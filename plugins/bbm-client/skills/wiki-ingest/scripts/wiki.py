#!/usr/bin/env python3
"""Read-only path, source queue and structural audit helpers for BBM Client."""
import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path


def load_paths():
    selected = os.environ.get('BBM_CLIENT_CONFIG')
    if selected:
        config = Path(selected).expanduser().absolute()
    else:
        config = next((d/'bbm-client.json' for d in [Path.cwd(), *Path.cwd().parents]
                       if (d/'bbm-client.json').exists()), None)
    if config is None:
        raise ValueError('No bbm-client.json found. Select the workspace and run workspace-setup.')
    if config.is_symlink():
        raise ValueError('Symlink config refused')
    cfg = json.loads(config.read_text(encoding='utf-8'))
    root = config.parent.resolve()
    result = {'config': config, 'root': root}
    for key in ('WORKSPACE_ROOT', 'WORKSPACE_MAP', 'VAULT_PATH', 'RAW_SOURCES_PATH', 'WIKI_PATH', 'STATE_PATH', 'PROPOSED_PATH', 'BOUNDARIES_FILE'):
        value = cfg.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError('Missing config key: ' + key)
        rel = Path(value)
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError('Config paths must remain relative to this workspace: ' + key)
        path = root/rel
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError('Symlink path refused: ' + key)
        path.resolve().relative_to(root)
        if not path.exists():
            raise ValueError('Configured path does not exist: ' + key)
        result[key] = path
    if result['WORKSPACE_ROOT'].resolve() != root:
        raise ValueError('WORKSPACE_ROOT must be the configuration directory')
    for key in ('RAW_SOURCES_PATH','WIKI_PATH','STATE_PATH','PROPOSED_PATH','WORKSPACE_MAP','BOUNDARIES_FILE'):
        result[key].resolve().relative_to(result['VAULT_PATH'].resolve())
    return result


def documents(root):
    for p in root.rglob('*.md'):
        if p.is_symlink() or any(x.is_symlink() for x in p.parents):
            continue
        if any(x.startswith('.') for x in p.relative_to(root).parts):
            continue
        yield p


def meta(text, key):
    if not text.startswith('---\n'):
        return ''
    header = text.split('\n---', 1)[0]
    match = re.search(r'^' + re.escape(key) + r':\s*(.*?)\s*$', header, re.M)
    return match.group(1).strip('"\'') if match else ''


def links(text):
    text = re.sub(r'```.*?```|`[^`\n]*`', '', text, flags=re.S)
    return re.findall(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]', text)


def resolve_link(vault, target):
    target = target.strip()
    path = Path(target)
    if path.is_absolute() or '..' in path.parts:
        return None
    if path.suffix != '.md':
        path = Path(str(path) + '.md')
    full = vault/path
    if full.is_symlink() or any(p.is_symlink() for p in full.parents):
        return None
    return full if full.is_file() else None


def audit(paths, stale_days=7):
    vault = paths['VAULT_PATH']
    docs = {p: p.read_text(encoding='utf-8') for p in documents(vault)}
    result = {'dead_links': [], 'orphans': [], 'stale_sources': []}
    inbound = set()
    for p, text in docs.items():
        for target in links(text):
            resolved = resolve_link(vault, target)
            if resolved is None:
                result['dead_links'].append({'file': str(p.relative_to(vault)), 'target': target})
            elif resolved != p:
                inbound.add(resolved)
    for kind in ('entities','concepts','topics'):
        for p in documents(paths['WIKI_PATH']/kind):
            if p not in inbound:
                result['orphans'].append(str(p.relative_to(vault)))
    cutoff = dt.date.today() - dt.timedelta(days=stale_days)
    for p in documents(paths['RAW_SOURCES_PATH']):
        text = docs.get(p, '')
        if meta(text, 'status') != 'unprocessed':
            continue
        try:
            stale = dt.date.fromisoformat(meta(text, 'date_captured')[:10]) < cutoff
        except ValueError:
            stale = True
        if stale:
            result['stale_sources'].append(str(p.relative_to(vault)))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['paths','unprocessed','lint'])
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--stale-days', type=int, default=7)
    args = parser.parse_args()
    try:
        p = load_paths()
        if args.command == 'paths':
            result = {k: str(v) for k, v in p.items()}
        elif args.command == 'lint':
            result = audit(p, args.stale_days)
        else:
            result = [{'path': str(f), 'status': meta(f.read_text(encoding='utf-8'), 'status')}
                      for f in sorted(documents(p['RAW_SOURCES_PATH']))
                      if meta(f.read_text(encoding='utf-8'), 'status') in ('unprocessed','needs-review')]
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, OSError, KeyError) as e:
        parser.exit(2, str(e) + '\n')


if __name__ == '__main__':
    main()
