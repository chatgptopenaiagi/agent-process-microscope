"""APM Evidence Capsule v1: bounded, unsigned JSON, never an executable archive."""
from collections import Counter
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from uuid import UUID

from apm.core.events import ACTIONS, CATEGORIES, STATUSES, utc_now
from apm.security.redaction import sanitize
from apm.storage.memory import canonical
from apm.storage.review import QualificationReview

MAX_BYTES = 4 * 1024 * 1024
MAX_RECORDS = 1000
MAX_REFS = 100
ORIGINS = ('host', 'reporter', 'local-human', 'local-investigator')
CLASSES = ('OBSERVED', 'AGENT_REPORTED', 'HUMAN_RECORDED', 'INFERRED', 'SYNTHETIC', 'UNKNOWN', 'UNAVAILABLE')
SOURCES = ('codex', 'process', 'filesystem', 'git', 'system', 'local-investigator', 'human-decision', 'fixture', 'other')
ATTRIBUTES = {'exit_code', 'item_id', 'codex_event', 'comparison_key', 'through_arrival', 'checkpoint',
              'decision', 'algorithm', 'inspected', 'total', 'truncated'}
OMITTED_FIELDS = ['agent_id', 'principal', 'process_identifiers', 'structured_path_metadata', 'unlisted_metadata', 'raw_reference', 'confidence']
LIMITATIONS = ['UNSIGNED', 'SOURCE_AUTHENTICITY_UNKNOWN', 'COLLECTION_COMPLETENESS_UNKNOWN',
              'SOURCE_CHAIN_NOT_REVERIFIED', 'NO_CAUSATION_OR_LEGAL_CUSTODY_PROOF',
              'NO_EXTERNAL_ARTIFACT_PAYLOADS', 'NO_EXECUTION_AUTHORITY']
RECORD_FIELDS = {'arrival', 'event_id', 'stream', 'sequence', 'missing_before', 'origin', 'source',
    'evidence_class', 'category', 'action', 'status', 'event_timestamp', 'received_at', 'timestamp_basis',
    'source_time', 'clock_uncertainty_ms', 'source_fingerprint', 'target', 'attributes', 'references'}
MANIFEST_FIELDS = {'format', 'version', 'case_id', 'session_id', 'created_at', 'canonicalization',
    'algorithm', 'records_sha256', 'record_count', 'source', 'disclosure', 'missing_references', 'limitations'}


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def require(condition, code):
    if not condition:
        raise ValueError('capsule_' + code)


def fields(value, keys):
    require(isinstance(value, dict) and set(value) == set(keys), 'fields')


def integer(value, minimum=0, maximum=2**53-1):
    require(type(value) is int and minimum <= value <= maximum, 'integer_bounds')


def identifier(value):
    require(isinstance(value, str) and len(value) == 36 and str(UUID(value)) == value, 'uuid')


def fingerprint(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None, 'sha256')


def timestamp(value):
    require(isinstance(value, str) and len(value) <= 40, 'timestamp')
    require(re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value) is not None, 'timestamp_format')
    require(datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None, 'timestamp_zone')


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def _reject_number(_):
    raise ValueError('capsule_noninteger_number')


def _depth(raw):
    depth, quoted, escaped = 0, False, False
    for byte in raw:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            require(depth <= 12, 'nesting_limit')
        elif byte in (93, 125):
            depth -= 1


def validate(document):
    """Closed structural contract plus cross-record invariants. No schema fetching."""
    fields(document, ('manifest', 'manifest_sha256', 'records'))
    m, records = document['manifest'], document['records']
    fields(m, MANIFEST_FIELDS)
    require(m['format'] == 'apm-evidence-capsule' and type(m['version']) is int and m['version'] == 1, 'version')
    require(m['canonicalization'] == 'apm-json-v1' and m['algorithm'] == 'sha256', 'algorithm')
    identifier(m['case_id']); identifier(m['session_id']); timestamp(m['created_at'])
    fingerprint(m['records_sha256']); fingerprint(document['manifest_sha256'])
    require(isinstance(records, list) and len(records) <= MAX_RECORDS, 'record_limit')
    integer(m['record_count'], maximum=MAX_RECORDS)
    require(m['record_count'] == len(records), 'record_count')
    require(digest(records) == m['records_sha256'] and digest(m) == document['manifest_sha256'], 'integrity')
    require(m['limitations'] == LIMITATIONS, 'limitations')
    source, disclosure = m['source'], m['disclosure']
    fields(source, ('kind', 'database_tip', 'database_records', 'session_records', 'verification'))
    require(source['kind'] == 'apm-sqlite-v1' and source['verification'] == 'exporter-checked-unkeyed-chain', 'source')
    fingerprint(source['database_tip']); integer(source['database_records'], maximum=1000000)
    integer(source['session_records'], maximum=MAX_RECORDS)
    fields(disclosure, ('policy', 'human_records', 'omitted_records', 'omitted_fields'))
    require(disclosure['policy'] in ('minimal-v1', 'text-v1'), 'disclosure_policy')
    require(disclosure['human_records'] in ('included', 'omitted'), 'human_disclosure')
    require(disclosure['omitted_fields'] == OMITTED_FIELDS, 'omitted_fields')
    integer(disclosure['omitted_records'], maximum=MAX_RECORDS)
    require(source['session_records'] == len(records) + disclosure['omitted_records'] <= source['database_records'], 'source_count')
    if disclosure['human_records'] == 'included':
        require(disclosure['omitted_records'] == 0, 'omitted_count')
    ids, references, streams = set(), set(), {}
    last_arrival = 0
    for r in records:
        fields(r, RECORD_FIELDS)
        identifier(r['event_id']); identifier(r['stream'])
        require(r['event_id'] not in ids, 'duplicate_event'); ids.add(r['event_id'])
        integer(r['arrival'], 1); require(r['arrival'] > last_arrival, 'receipt_order'); last_arrival = r['arrival']
        integer(r['sequence'], 1); integer(r['missing_before'])
        require(r['origin'] in ORIGINS and r['source'] in SOURCES, 'provenance')
        require(r['category'] in CATEGORIES and r['action'] in ACTIONS and r['status'] in STATUSES, 'event_vocabulary')
        expected_class = r['status'].upper() if r['status'] != 'observed' else (
            'OBSERVED' if r['origin'] == 'host' else 'HUMAN_RECORDED' if r['origin'] == 'local-human' else 'AGENT_REPORTED')
        require(r['evidence_class'] == expected_class, 'classification')
        require(disclosure['human_records'] == 'included' or r['origin'] != 'local-human', 'human_record_not_authorized')
        previous, origin = streams.get(r['stream'], (0, r['origin']))
        require(r['sequence'] > previous and r['missing_before'] == r['sequence'] - previous - 1 and origin == r['origin'], 'stream_order')
        streams[r['stream']] = (r['sequence'], origin)
        timestamp(r['event_timestamp']); timestamp(r['received_at']); fingerprint(r['source_fingerprint'])
        require(r['source_time'] is None and r['clock_uncertainty_ms'] is None, 'unknown_clock')
        require(r['timestamp_basis'] in ('client_receipt_time', 'import_time', 'unknown'), 'time_basis')
        require(isinstance(r['target'], str) and len(r['target']) <= 8192 and sanitize(r['target']) == r['target'], 'unsafe_text')
        r['target'].encode('utf8')  # Reject unpaired surrogates before any UI display.
        if disclosure['policy'] == 'minimal-v1':
            require(r['target'] == r['category'] + ' ' + r['action'], 'minimal_text')
        attrs = r['attributes']
        require(isinstance(attrs, dict) and set(attrs) <= ATTRIBUTES, 'attributes')
        for key, value in attrs.items():
            if key == 'exit_code':
                integer(value, -(2**31), 2**32-1)
            elif key in ('through_arrival', 'inspected', 'total'):
                integer(value)
            elif key == 'truncated':
                require(type(value) is bool, 'truncated_flag')
            elif key == 'checkpoint':
                fingerprint(value)
            else:
                require(isinstance(value, str) and re.fullmatch('[A-Za-z0-9_.-]{1,80}', value) is not None
                        and sanitize(value) == value, 'attribute_text')
        require(isinstance(r['references'], list) and len(r['references']) <= MAX_REFS, 'reference_limit')
        require(len(set(r['references'])) == len(r['references']), 'duplicate_reference')
        for ref in r['references']:
            identifier(ref); references.add(ref)
    require(m['missing_references'] == sorted(references - ids), 'missing_reference_declaration')


class Capsule:
    """Isolated read-only investigation context; accessors return independent copies.

    Declared OBSERVED is an exporter claim, never a new local host observation.
    """
    def __init__(self, raw, *, expected_sha256=None):
        require(isinstance(raw, bytes) and len(raw) <= MAX_BYTES, 'byte_limit')
        require(raw.startswith(b'{'), 'json_only_archives_unsupported')
        _depth(raw)
        try:
            document = json.loads(raw.decode('utf8'), object_pairs_hook=_unique,
                                  parse_constant=_reject_number, parse_float=_reject_number)
            validate(document)
        except (KeyError, TypeError, AttributeError, OverflowError, RecursionError, UnicodeError) as exc:
            raise ValueError('capsule_malformed') from None
        self.sha256 = hashlib.sha256(raw).hexdigest()
        if expected_sha256 is not None:
            fingerprint(expected_sha256)
            require(self.sha256 == expected_sha256, 'external_digest_mismatch')
        self._document = document
        self._by_id = {r['event_id']: r for r in document['records']}

    @classmethod
    def open(cls, path, *, expected_sha256=None):
        path = Path(path)
        require(path.suffix == '.apmcapsule', 'filename_extension')
        require(stat.S_ISREG(path.stat().st_mode), 'regular_file_required')
        with path.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        return cls(raw, expected_sha256=expected_sha256)

    @property
    def manifest(self):
        return deepcopy(self._document['manifest'])

    def page(self, *, after=0, limit=100):
        integer(after); integer(limit, 1, 100)
        return deepcopy([r for r in self._document['records'] if r['arrival'] > after][:limit])

    def resolve(self, evidence_id):
        identifier(evidence_id)
        return deepcopy(self._by_id.get(evidence_id))

    def summary(self):
        m = self.manifest
        return dict(status='VERIFIED', check='capsule structure and internal SHA-256 checksums',
            sha256=self.sha256, case_id=m['case_id'], session_id=m['session_id'], records=m['record_count'],
            declared_classes=dict(Counter(r['evidence_class'] for r in self._document['records'])),
            disclosure=m['disclosure'], missing_references=m['missing_references'],
            provenance='UNVERIFIED exporter declarations; original source chain not reverified',
            limitations=m['limitations'])


def export_session(database, session, case_id, destination, *, include_human=False, include_text=False, expected_tip=None):
    """Explicit selected-session disclosure. Exclusive destination; no source writes."""
    identifier(session); identifier(case_id)
    destination = Path(destination)
    require(destination.suffix == '.apmcapsule', 'filename_extension')
    require(not destination.exists(), 'destination_exists')
    records, omitted, count, after = [], 0, 0, 0
    with QualificationReview(database, expected_tip=expected_tip) as review:
        review._require()
        while rows := review.page(session, after=after):
            for row in rows:
                count += 1
                require(count <= MAX_RECORDS, 'session_exceeds_record_limit')
                if row['origin'] == 'local-human' and not include_human:
                    omitted += 1
                    continue
                event, meta = row['event'], row['event']['metadata']
                refs = meta.get('evidence_ids', [])
                require(isinstance(refs, list), 'references')
                # Duplicate citations carry no extra knowledge; malformed UUIDs fail validation.
                attrs = {k: meta[k] for k in ATTRIBUTES if k in meta and meta[k] is not None}
                require(all(isinstance(ref, str) for ref in refs), 'references')
                records.append(dict(arrival=row['arrival'], event_id=event['event_id'], stream=row['stream'],
                    sequence=row['sequence'], missing_before=row['missing_before'], origin=row['origin'],
                    source=event['source'] if event['source'] in SOURCES else 'other',
                    evidence_class=row['evidence_class'], category=event['category'], action=event['action'], status=event['status'],
                    event_timestamp=event['timestamp'], received_at=row['received_at'],
                    timestamp_basis=meta.get('timestamp_basis') if meta.get('timestamp_basis') in ('client_receipt_time', 'import_time') else 'unknown',
                    source_time=None, clock_uncertainty_ms=None, source_fingerprint=row['fingerprint'],
                    target=sanitize(event['target']) if include_text else event['category'] + ' ' + event['action'],
                    attributes=attrs, references=list(dict.fromkeys(refs))))
            after = rows[-1]['arrival']
        require(count > 0, 'session_not_found')
        ids = {r['event_id'] for r in records}
        manifest = dict(format='apm-evidence-capsule', version=1, case_id=case_id, session_id=session,
            created_at=utc_now(), canonicalization='apm-json-v1', algorithm='sha256', records_sha256=digest(records), record_count=len(records),
            source=dict(kind='apm-sqlite-v1', database_tip=review.integrity['tip'], database_records=review.integrity['records'],
                        session_records=count, verification='exporter-checked-unkeyed-chain'),
            disclosure=dict(policy='text-v1' if include_text else 'minimal-v1', human_records='included' if include_human else 'omitted',
                            omitted_records=omitted, omitted_fields=OMITTED_FIELDS),
            missing_references=sorted({ref for r in records for ref in r['references']} - ids), limitations=LIMITATIONS)
    raw = canonical(dict(manifest=manifest, manifest_sha256=digest(manifest), records=records))
    capsule = Capsule(raw)
    with destination.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return capsule.summary()
