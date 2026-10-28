#!/usr/bin/env python3
"""Export exactly the portable client skills; never the messaging agent bundle."""
import sys
import zipfile
from pathlib import Path
root = Path(__file__).resolve().parent.parent / 'plugins/bbm-client'
with zipfile.ZipFile(sys.argv[1], 'x', zipfile.ZIP_DEFLATED) as archive:
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if p.is_file() and not p.is_symlink() and '__pycache__' not in rel.parts and ('tests' not in rel.parts) and (rel.parts[0] == 'skills' or str(rel) in ('README.md', 'LICENSE')):
            archive.write(p, rel.as_posix())
print(sys.argv[1])
