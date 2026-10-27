"""Create a private distribution ZIP from an existing metadata archive; never contacts the platform."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from urllib.parse import urlsplit, parse_qsl
from catalog import Catalog, digest, member_path, write_new

SENSITIVE_TEXT = re.compile(r'(?i)(?:password|passwd|authorization|access[_-]?token|secret[_-]?key)\s*[=:]\s*["\x27]?[^\s"\x27]{6,}|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----')
SENSITIVE_KEYS = {'cookie', 'set-cookie', 'authorization', 'password', 'passwd', 'access_token', 'refresh_token', 'client_secret'}


def check_text(text: str) -> None:
    if SENSITIVE_TEXT.search(text):
        raise ValueError('SENSITIVE_TEXT_REQUIRES_REVIEW')
    for url in re.findall(r'https?://[^\s<>"\x27`]+', text):
        parsed = urlsplit(url)
        if parsed.username or any(('signature' in k.lower() or k.lower() in SENSITIVE_KEYS | {'token'})
                                 and v not in ('<redacted>', '[REDACTED]') for k, v in parse_qsl(parsed.query)):
            raise ValueError('SENSITIVE_URL_REQUIRES_REVIEW')


def check_payload(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() in SENSITIVE_KEYS and item not in (None, '', '<redacted>', '[REDACTED]'):
                raise ValueError('SENSITIVE_KEY_REQUIRES_REVIEW')
            check_payload(item)
    elif isinstance(value, list):
        for item in value:
            check_payload(item)
    elif isinstance(value, str):
        check_text(value)


def package(source: Path, output: Path, manifest_path: Path) -> dict:
    if output.exists() or manifest_path.exists() or output.with_suffix(output.suffix+'.sha256').exists():
        raise ValueError('OUTPUT_EXISTS_PRESERVE_PREVIOUS_VERSION')
    with Catalog(source) as catalog:
        validation = catalog.validate()
        selected = {'snapshot/snapshot.json', 'provenance/index.json'}
        for name in ('README.md', 'delivery_summary.json', 'coverage.csv', 'database_coverage.csv', 'remaining_gaps.csv',
                     'version_review.csv', 'permission_candidates.csv', 'observed_edges.json', 'external_references.json', 'task_name_change_review.json'):
            member = member_path(name)
            if member in catalog.zip.namelist():
                selected.add(member)
        for entry in catalog.index.values():
            selected.add(member_path(entry['record']))
            for item in [*entry.get('sources', []), *entry.get('related_task_sources', []),
                         *([entry['description']] if entry.get('description') else [])]:
                selected.add(member_path(item['path']))
            if not entry.get('description') and entry.get('reused_description_evidence'):
                selected.add(member_path(entry['reused_description_evidence']))
            for key in ('link_record', 'task_record'):
                if entry.get('task_source', {}).get(key):
                    selected.add(member_path(entry['task_source'][key]))
        output.parent.mkdir(parents=True, exist_ok=True)
        hashes = {}
        with ZipFile(output, 'x', compression=ZIP_DEFLATED, compresslevel=6) as target:
            for name in sorted(selected):
                content = catalog.zip.read(name)
                text = content.decode('utf-8-sig')
                if name.endswith('.json'):
                    check_payload(json.loads(text))
                else:
                    check_text(text)
                target.writestr(name, content)
                hashes[name] = hashlib.sha256(content).hexdigest()
            receipt = {'format': 'bigdata-platform-catalog-v1', 'source_archive_sha256': catalog.sha256,
                       'included_members_sha256': hashes,
                       'excluded': ['browser profile', 'credentials', 'runtime audit logs', 'business rows', 'executable collectors'],
                       'note': 'Original audit archive stays local. Some evidence paths are historical references; indexed source/description artifacts are included.'}
            target.writestr('distribution-manifest.json', json.dumps(receipt, ensure_ascii=False, indent=2).encode('utf-8'))
        with Catalog(output) as copy:
            copy.validate()
            for name, expected in hashes.items():
                if hashlib.sha256(copy.zip.read(name)).hexdigest() != expected:
                    raise ValueError('DISTRIBUTION_MEMBER_CHANGED')
        result = {'format_version': 1, 'asset_name': output.name, 'sha256': digest(output),
                  'source_archive_sha256': catalog.sha256, 'created_at': datetime.now(timezone.utc).isoformat(),
                  'metadata_collected_as_of': 'SEE_COMPONENT_TIMESTAMPS', 'tables': validation['tables'],
                  'coverage': {k: catalog.provenance_summary.get(k) for k in ('tables_with_sql_evidence',
                               'tables_with_description_evidence', 'tables_with_nonempty_lineage')},
                  'members': len(hashes)+1, 'bytes': output.stat().st_size,
                  'distribution_validation': 'PASS', 'visibility_required': 'private'}
    write_new(manifest_path, result)
    with output.with_suffix(output.suffix+'.sha256').open('x', encoding='ascii') as stream:
        stream.write(result['sha256']+'  '+output.name+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(package(args.source, args.output, args.manifest), ensure_ascii=False, indent=2))
