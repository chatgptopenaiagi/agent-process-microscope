"""Validate the repository capability contract with a bounded schema subset.

Supports exactly the keywords used by our published JSON Schema; unknown
keywords fail closed. This is not a general JSON Schema implementation and
performs no network resolution. Source/test references are repository-relative.
"""
import argparse
import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
KEYWORDS = {'$schema', 'title', 'description', 'type', 'properties', 'required',
            'additionalProperties', 'items', 'minItems', 'maxItems', 'minLength',
            'maxLength', 'enum', 'const', 'pattern'}


def validate(value, schema, path='$', depth=0):
    if depth > 12 or set(schema) - KEYWORDS: raise ValueError('Unsupported schema at ' + path)
    kind = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool}
    if kind not in types or type(value) is not types[kind]: raise ValueError('Wrong type at ' + path)
    if 'const' in schema and value != schema['const']: raise ValueError('Wrong constant at ' + path)
    if 'enum' in schema and value not in schema['enum']: raise ValueError('Unknown enumeration at ' + path)
    if kind == 'object':
        if set(schema.get('required', [])) - set(value): raise ValueError('Missing fields at ' + path)
        properties = schema.get('properties', {})
        if schema.get('additionalProperties') is not False: raise ValueError('Schema must be closed')
        if set(value) - set(properties): raise ValueError('Unknown fields at ' + path)
        for k, v in value.items(): validate(v, properties[k], path + '.' + k, depth + 1)
    elif kind == 'array':
        if not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', 100): raise ValueError('Array limit at ' + path)
        for n, v in enumerate(value): validate(v, schema['items'], path + '[' + str(n) + ']', depth + 1)
    elif kind == 'string':
        if not schema.get('minLength', 0) <= len(value) <= schema.get('maxLength', 2000): raise ValueError('String limit at ' + path)
        if 'pattern' in schema and re.search(schema['pattern'], value) is None: raise ValueError('Pattern mismatch at ' + path)


def reference(root, value):
    filename, _, symbol = value.partition(':')
    p = Path(filename)
    if p.is_absolute() or '..' in p.parts or '\\' in filename or ':' in filename:
        raise ValueError('Nonlocal reference')
    target = (root / p).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file(): raise ValueError('Missing repository reference: ' + filename)
    if symbol:
        tree = ast.parse(target.read_text(encoding='utf-8'))
        if symbol not in {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}:
            raise ValueError('Missing symbol: ' + value)


def verify(manifest, schema, root=ROOT):
    validate(manifest, schema)
    ids = [c['id'] for c in manifest['capabilities']]
    if len(ids) != len(set(ids)): raise ValueError('Duplicate capability identifier')
    from apm import __version__
    if manifest['application_version'] != __version__: raise ValueError('Version mismatch')
    for c in manifest['capabilities']:
        for r in c['implementation'] + c['tests'] + c['evidence_sources']: reference(root, r)
        if c['verification_status'] == 'TESTED' and not c['tests']: raise ValueError('Test evidence required')
    return dict(status='PASS', capabilities=len(ids),
                tested=sum(c['verification_status'] == 'TESTED' for c in manifest['capabilities']),
                limits='Contract and local references validated; test outcomes must be recorded separately. No API stability or universal correctness certification.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'capabilities/apm-capabilities-v1.json')
    args = parser.parse_args()
    if args.manifest.stat().st_size > 256 * 1024: raise ValueError('Manifest too large')
    manifest = json.loads(args.manifest.read_text())
    schema = json.loads((ROOT / 'capabilities/apm-capabilities-v1.schema.json').read_text())
    print(json.dumps(verify(manifest, schema), indent=2))


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT))
    main()
