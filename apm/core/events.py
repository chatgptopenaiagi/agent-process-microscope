from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
from uuid import UUID, uuid4

from apm.security.redaction import sanitize

CATEGORIES = frozenset('agent process command filesystem file git test browser network system tool verification error session'.split())
ACTIONS = frozenset('START STOP OPEN READ WRITE CREATE DELETE RENAME EXECUTE CLICK TYPE NAVIGATE REQUEST RESPONSE PASS FAIL VERIFY WAIT UNKNOWN SNAPSHOT SAMPLE UPDATE'.split())
STATUSES = frozenset(('observed', 'inferred', 'unknown', 'unavailable', 'synthetic'))


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


@dataclass(frozen=True)
class Event:
    session_id: str
    agent_id: str
    source: str
    category: str
    action: str
    target: str = ''
    status: str = 'observed'
    confidence: float = 1.0
    interpretation_level: str = 'observation'
    raw_reference: str | None = None
    metadata: dict = field(default_factory=dict)
    schema_version: str = '1.0'
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=utc_now)

    def __post_init__(self):
        if not all(isinstance(value, str) for value in (self.session_id, self.event_id, self.timestamp,
                                                       self.agent_id, self.source, self.target,
                                                       self.category, self.action, self.status)):
            raise ValueError('Invalid textual event fields')
        if self.raw_reference is not None and not isinstance(self.raw_reference, str):
            raise ValueError('Invalid evidence reference')
        if self.schema_version != '1.0':
            raise ValueError('Unsupported event schema')
        UUID(self.event_id)
        UUID(self.session_id)
        if datetime.fromisoformat(self.timestamp.replace('Z', '+00:00')).tzinfo is None:
            raise ValueError('Timestamp must have timezone')
        if self.category not in CATEGORIES or self.action not in ACTIONS or self.status not in STATUSES:
            raise ValueError('Invalid canonical event vocabulary')
        if type(self.confidence) not in (float, int) or not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError('Invalid confidence')
        if self.interpretation_level not in ('observation', 'inference', 'synthetic'):
            raise ValueError('Invalid interpretation level')
        if self.status == 'synthetic' and self.interpretation_level != 'synthetic':
            raise ValueError('Synthetic evidence must remain synthetic')
        if self.status == 'inferred' and self.interpretation_level != 'inference':
            raise ValueError('Inference must be identified')
        if not isinstance(self.metadata, dict):
            raise ValueError('Metadata must be object')

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**sanitize(data))


class Normalizer:
    def __init__(self, session_id, agent_id):
        self.session_id, self.agent_id = session_id, agent_id

    def normalize(self, payload: dict) -> Event:
        clean = sanitize(payload)
        clean['session_id'] = self.session_id
        clean['agent_id'] = self.agent_id
        # Hash only sanitized evidence. Raw sensitive text is never recorded.
        metadata = clean.setdefault('metadata', {})
        metadata.setdefault('observation_source', clean.get('source', 'unknown'))
        if not clean.get('raw_reference'):
            encoded = json.dumps(metadata, sort_keys=True, ensure_ascii=False).encode('utf-8')
            clean['raw_reference'] = 'sha256:' + hashlib.sha256(encoded).hexdigest()
        return Event(**clean)
