"""Offline metadata/provenance lookup and version binding. Never executes SQL or ZIP code."""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZipFile

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BINDING = SKILL_ROOT / '.local/catalog.json'


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def write_new(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(json_bytes(value))


def member_path(relative: str) -> str:
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or '\\' in relative:
        raise ValueError('UNSAFE_ARCHIVE_REFERENCE')
    return 'provenance/' + path.as_posix()


class Catalog:
    def __init__(self, path: Path, expected_sha: str | None = None) -> None:
        self.path = path.resolve()
        self.sha256 = digest(self.path)
        if expected_sha is not None and self.sha256 != expected_sha.lower():
            raise ValueError('ARCHIVE_HASH_CHANGED')
        self.zip = ZipFile(self.path)
        try:
            names = self.zip.namelist()
            if len(names) != len(set(names)):
                raise ValueError('DUPLICATE_ARCHIVE_MEMBER')
            snapshot = self.read_json('snapshot/snapshot.json')
            provenance = self.read_json('provenance/index.json')
            self.tables = {row['fqn']: row for row in snapshot['tables']}
            self.index = {row['fqn']: row for row in provenance['tables']}
            if (len(self.tables) != len(snapshot['tables']) or len(self.index) != len(provenance['tables'])
                    or set(self.tables) != set(self.index)
                    or len({r['native_id'] for r in self.tables.values()}) != len(self.tables)):
                raise ValueError('TABLE_SCOPE_NOT_UNIQUE_OR_EQUAL')
            for name, row in self.tables.items():
                if row['native_id'] != self.index[name]['native_id']:
                    raise ValueError('TABLE_IDENTITY_MISMATCH')
            self.provenance_summary = provenance['summary']
        except Exception:
            self.zip.close()
            raise

    def __enter__(self) -> Catalog:
        return self

    def __exit__(self, *args: Any) -> None:
        self.zip.close()

    def read_json(self, name: str) -> dict:
        return json.loads(self.zip.read(name).decode('utf-8-sig'))

    def entry(self, fqn: str) -> dict:
        if fqn not in self.tables:
            raise ValueError('EXACT_DATABASE_TABLE_NOT_FOUND')
        return self.index[fqn]

    def record(self, fqn: str) -> dict:
        entry = self.entry(fqn)
        record = self.read_json(member_path(entry['record']))
        if (record.get('fqn'), record.get('native_id')) != (fqn, entry['native_id']):
            raise ValueError('PROVENANCE_RECORD_IDENTITY_MISMATCH')
        return record

    def validate(self) -> dict:
        if self.zip.testzip() is not None:
            raise ValueError('ZIP_CRC_FAILED')
        verified: set[str] = set()
        for fqn, entry in self.index.items():
            self.record(fqn)
            artifacts = [*entry.get('sources', []), *entry.get('related_task_sources', [])]
            if entry.get('description'):
                artifacts.append(entry['description'])
            for item in artifacts:
                member = member_path(item['path'])
                if hashlib.sha256(self.zip.read(member)).hexdigest() != item['sha256']:
                    raise ValueError('SOURCE_CONTENT_HASH_MISMATCH')
                verified.add(member)
            task = entry.get('task_source', {})
            if task.get('link_record'):
                link = self.read_json(member_path(task['link_record']))
                if (link.get('fqn'), link.get('native_id')) != (fqn, entry['native_id']):
                    raise ValueError('TASK_LINK_IDENTITY_MISMATCH')
            if task.get('task_record'):
                record = self.read_json(member_path(task['task_record']))
                if record.get('task_id') != task.get('task_id'):
                    raise ValueError('TASK_RECORD_IDENTITY_MISMATCH')
                source = record.get('source', {})
                if source.get('taskCode'):
                    actual = hashlib.sha256(source['taskCode'].encode('utf-8')).hexdigest()
                    expected = source.get('taskCode_stored_sha256') or source.get('taskCode_source_sha256')
                    if not expected or actual != expected:
                        raise ValueError('TASK_SOURCE_CONTENT_HASH_MISMATCH')
            if not entry.get('description') and entry.get('reused_description_evidence'):
                self.zip.getinfo(member_path(entry['reused_description_evidence']))
        return {'tables': len(self.tables), 'verified_text_files': len(verified), 'sha256': self.sha256,
                'identity_and_content_validation': 'PASS'}

    def summary(self) -> dict:
        return {'archive_sha256': self.sha256, 'tables': len(self.tables),
                'databases': len({x.split('.', 1)[0] for x in self.tables}),
                'provenance': self.provenance_summary, 'current_platform_state': 'NOT_LIVE_VERIFIED'}

    def search(self, keyword: str, fields: bool = False, limit: int = 30) -> dict:
        if not keyword.strip() or not 1 <= limit <= 200:
            raise ValueError('SEARCH_REQUIRES_KEYWORD_AND_LIMIT_1_TO_200')
        matches = []
        word = keyword.casefold()
        for name, row in self.tables.items():
            description = (row.get('detail') or {}).get('tableDesc') or row.get('inventory_description') or ''
            columns = [c for c in (row.get('schema') or {}).get('fieldsInfos', [])
                       if fields and word in (str(c.get('name') or '') + str(c.get('comment') or '')).casefold()]
            if columns or word in (name + description).casefold():
                matches.append({'fqn': name, 'native_id': row['native_id'], 'description': description,
                                'heat': row.get('heat'), 'matched_fields': columns,
                                'sql_source_status': self.index[name].get('sql_source_status')})
        matches.sort(key=lambda r: -((r.get('heat') or {}).get('hotValue') or 0))
        return {'matches_total': len(matches), 'returned': min(limit, len(matches)), 'tables': matches[:limit],
                'archive_sha256': self.sha256, 'authorization': 'NOT_VERIFIED_BY_METADATA'}

    def table(self, fqn: str) -> dict:
        entry = self.entry(fqn)
        row = self.tables[fqn]
        return {**{k: row.get(k) for k in ('fqn', 'native_id', 'detail', 'schema', 'heat', 'heat_time_window',
                 'schema_status', 'observed_at_by_component', 'source_failure')},
                'provenance': entry, 'archive_sha256': self.sha256, 'authorization': 'NOT_VERIFIED_BY_METADATA'}

    def text(self, fqn: str, kind: str, index: int = 0) -> dict:
        entry = self.entry(fqn)
        result = {'fqn': fqn, 'kind': kind, 'archive_sha256': self.sha256,
                  'production_version_verified': False}
        if kind == 'task':
            reference = entry.get('task_source', {})
            if not reference.get('task_record'):
                return {**result, 'status': 'NOT_CAPTURED', 'task_source': reference}
            task = self.read_json(member_path(reference['task_record']))
            return {**result, 'status': reference['status'], 'task_source': reference, 'task': task}
        if kind == 'sql':
            artifacts = entry.get('sources', [])
            if not artifacts:
                return {**result, 'status': 'NOT_CAPTURED', 'task_source': entry.get('task_source')}
            if not 0 <= index < len(artifacts):
                raise ValueError('SOURCE_INDEX_OUT_OF_RANGE')
            item = artifacts[index]
        else:
            item = entry.get('description')
            if not item:
                reference = entry.get('reused_description_evidence')
                return ({**result, 'status': entry.get('description_status'), 'evidence': reference,
                         'text': self.zip.read(member_path(reference)).decode('utf-8-sig')}
                        if reference else {**result, 'status': 'NOT_CAPTURED'})
        content = self.zip.read(member_path(item['path']))
        if hashlib.sha256(content).hexdigest() != item['sha256']:
            raise ValueError('SOURCE_CONTENT_HASH_MISMATCH')
        status = (entry.get('task_source', {}).get('status') if item.get('origin') == 'TASK_DEVELOPMENT_PAGE_SOURCE'
                  else entry.get('sql_source_status')) if kind == 'sql' else entry.get('description_status')
        return {**result, 'status': status,
                'evidence': item, 'text': content.decode('utf-8-sig')}


def difference(old: Catalog, new: Catalog) -> dict:
    before, after = set(old.tables), set(new.tables)
    changed, identities = [], []
    for name in sorted(before & after):
        if old.tables[name]['native_id'] != new.tables[name]['native_id']:
            identities.append({'fqn': name, 'old': old.tables[name]['native_id'], 'new': new.tables[name]['native_id']})
        components = [k for k in ('schema', 'detail', 'heat') if old.tables[name].get(k) != new.tables[name].get(k)]
        a, b = old.record(name), new.record(name)
        components += [k for k in ('lineage', 'assets', 'description', 'task_source') if a.get(k) != b.get(k)]
        if components:
            changed.append({'fqn': name, 'components': components})
    return {'old_sha256': old.sha256, 'new_sha256': new.sha256, 'added': sorted(after-before),
            'absent_from_new_scope': sorted(before-after), 'native_id_changes': identities, 'changed': changed,
            'note': 'Scope/observation differences do not prove physical creation/deletion; component changes may include timestamps.'}


def bind(path: Path, expected_sha: str, binding: Path) -> dict:
    with Catalog(path, expected_sha) as new:
        validation = new.validate()
        previous = json.loads(binding.read_text(encoding='utf-8')) if binding.exists() else None
        diff = None
        if previous and previous['sha256'] != new.sha256:
            with Catalog(Path(previous['archive']), previous['sha256']) as old:
                diff = difference(old, new)
            if diff['native_id_changes']:
                raise ValueError('IDENTITY_CHANGED_REVIEW_REQUIRED')
            history = binding.parent/'history'/f"{previous['sha256']}.json"
            if not history.exists():
                write_new(history, previous)
            diff_path = binding.parent/'history'/f"{previous['sha256']}-{new.sha256}.diff.json"
            if not diff_path.exists():
                write_new(diff_path, diff)
        current = {'format_version': 1, 'archive': str(new.path), 'sha256': new.sha256,
                   'bound_at': datetime.now(timezone.utc).isoformat(), 'validation': validation}
        binding.parent.mkdir(parents=True, exist_ok=True)
        temp = binding.with_suffix('.tmp')
        temp.write_bytes(json_bytes(current))
        temp.replace(binding)
        return {'binding': str(binding), **current, 'changes': diff}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding', type=Path, default=DEFAULT_BINDING)
    parser.add_argument('--archive', type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('summary', 'validate'):
        commands.add_parser(name)
    search = commands.add_parser('search')
    search.add_argument('keyword'); search.add_argument('--fields', action='store_true'); search.add_argument('--limit', type=int, default=30)
    for name in ('table', 'lineage', 'sources', 'text'):
        p = commands.add_parser(name); p.add_argument('fqn')
        if name == 'text':
            p.add_argument('--kind', choices=['sql', 'description', 'task'], required=True); p.add_argument('--index', type=int, default=0)
    p = commands.add_parser('bind'); p.add_argument('--archive', type=Path, required=True); p.add_argument('--sha256', required=True)
    p = commands.add_parser('diff'); p.add_argument('--old', type=Path, required=True); p.add_argument('--new', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'bind':
        result = bind(args.archive, args.sha256, args.binding)
    elif args.command == 'diff':
        with Catalog(args.old) as old, Catalog(args.new) as new:
            old.validate(); new.validate(); result = difference(old, new)
        write_new(args.output, result)
    else:
        expected = None
        if not args.archive:
            if not args.binding.exists():
                raise ValueError('NO_CATALOG_BOUND_USE_BIND')
            binding = json.loads(args.binding.read_text(encoding='utf-8'))
            args.archive, expected = Path(binding['archive']), binding['sha256']
        with Catalog(args.archive, expected) as catalog:
            if args.command in ('summary', 'validate'):
                result = getattr(catalog, args.command)()
            elif args.command == 'search':
                result = catalog.search(args.keyword, args.fields, args.limit)
            elif args.command == 'table':
                result = catalog.table(args.fqn)
            elif args.command == 'lineage':
                record = catalog.record(args.fqn)
                result = {'fqn': args.fqn, 'archive_sha256': catalog.sha256, 'lineage': record['lineage']}
            elif args.command == 'sources':
                result = {'archive_sha256': catalog.sha256, **catalog.entry(args.fqn)}
            else:
                result = catalog.text(args.fqn, args.kind, args.index)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
