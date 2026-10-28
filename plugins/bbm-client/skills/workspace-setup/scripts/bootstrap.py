#!/usr/bin/env python3
"""Preview or create a client workspace. Existing differing files are never overwritten."""
import argparse
import json
import re
from pathlib import Path


def safe_path(root, relative):
    path = root / relative
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('Symlink destination refused: ' + str(path))
    path.resolve().relative_to(root.resolve())
    return path


def plan(destination, owner, person, business):
    for slug in (person, business):
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug):
            raise ValueError('Person and business must be lowercase slugs')
    if not owner.strip() or any(c in owner for c in '\n\r"{}'):
        raise ValueError('Owner must be a nonempty single-line name without quotes or braces')
    destination = Path(destination).absolute()
    destination = destination.parent.resolve() / destination.name
    safe_path(destination, '.')
    replacements = {'{{OWNER}}': owner, '{{PERSON}}': person, '{{BUSINESS}}': business}
    def render(text):
        for a, b in replacements.items():
            text = text.replace(a, b)
        return text
    template = Path(__file__).resolve().parent.parent / 'assets/starter'
    files = {render(p.relative_to(template).as_posix()): render(p.read_text(encoding='utf-8'))
             for p in template.rglob('*') if p.is_file()}
    cfg = {'OWNER_NAME': owner, 'WORKSPACE_ROOT': '.', 'WORKSPACE_MAP': 'vault/workspace/MAP.md',
           'VAULT_PATH': 'vault', 'RAW_SOURCES_PATH': 'vault/knowledge/raw',
           'WIKI_PATH': 'vault/knowledge/wiki', 'STATE_PATH': f'vault/businesses/{business}/state',
           'PROPOSED_PATH': f'vault/businesses/{business}/proposed',
           'BOUNDARIES_FILE': 'vault/workspace/BOUNDARIES.md'}
    files['bbm-client.json'] = json.dumps(cfg, indent=2) + '\n'
    conflicts = []
    for rel, content in files.items():
        path = safe_path(destination, rel)
        if path.exists() and (not path.is_file() or path.read_text(encoding='utf-8') != content):
            conflicts.append(rel)
    if conflicts:
        raise ValueError('Existing files differ; no writes made: ' + ', '.join(conflicts))
    return destination, files


def create(destination, owner, person, business, apply=False):
    root, files = plan(destination, owner, person, business)
    added = []
    for rel, content in files.items():
        p = safe_path(root, rel)
        if p.exists():
            continue
        added.append(rel)
        if apply:
            p.parent.mkdir(parents=True, exist_ok=True)
            safe_path(root, rel)
            with p.open('x', encoding='utf-8') as out:
                out.write(content)
    return {'mode': 'applied' if apply else 'preview', 'new_files': added, 'existing_identical': len(files)-len(added)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('destination', 'owner', 'person', 'business'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--apply', action='store_true')
    try:
        print(json.dumps(create(**vars(p.parse_args())), indent=2))
    except (ValueError, OSError) as e:
        p.exit(2, str(e) + '\n')
