import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
def module(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT/rel)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod
b = module('bootstrap', 'skills/workspace-setup/scripts/bootstrap.py')
w = module('wiki', 'skills/wiki-ingest/scripts/wiki.py')

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name).resolve()/'space with spaces'
        self.old = os.environ.get('BBM_CLIENT_CONFIG')
    def tearDown(self):
        if self.old is None: os.environ.pop('BBM_CLIENT_CONFIG',None)
        else: os.environ['BBM_CLIENT_CONFIG']=self.old
        self.temp.cleanup()
    def setup_workspace(self):
        b.create(self.root,'Sam','sam','example',True)
        os.environ['BBM_CLIENT_CONFIG']=str(self.root/'bbm-client.json')
        return w.load_paths()
    def test_preview_no_write(self):
        self.assertTrue(b.create(self.root,'Sam','sam','example')['new_files'])
        self.assertFalse(self.root.exists())
    def test_repeat_setup_preserves_content(self):
        self.setup_workspace()
        self.assertEqual(b.create(self.root,'Sam','sam','example',True)['new_files'],[])
        self.assertEqual(w.audit(w.load_paths()), {'dead_links': [],'orphans': [],'stale_sources': []})
    def test_conflict_preflight(self):
        self.root.mkdir(); (self.root/'README.md').write_text('my notes')
        with self.assertRaises(ValueError): b.create(self.root,'Sam','sam','example',True)
        self.assertEqual(list(self.root.iterdir()), [self.root/'README.md'])
    def test_invalid_slug(self):
        with self.assertRaises(ValueError): b.create(self.root,'Sam','../other','example',True)
        self.assertFalse(self.root.exists())
    def test_symlink_destination(self):
        self.root.mkdir(); (self.root/'vault').symlink_to(Path(self.temp.name).resolve(), target_is_directory=True)
        with self.assertRaises(ValueError): b.create(self.root,'Sam','sam','example',True)
        self.assertFalse((self.root/'AGENTS.md').exists())
    def test_config_escape(self):
        self.setup_workspace(); f=self.root/'bbm-client.json'; c=json.loads(f.read_text()); c['WIKI_PATH']='../outside'; f.write_text(json.dumps(c))
        with self.assertRaises(ValueError): w.load_paths()
    def test_no_global_fallback(self):
        self.setup_workspace(); os.environ['BBM_CLIENT_CONFIG']=str(self.root/'missing.json')
        with self.assertRaises(OSError): w.load_paths()
    def test_moved_checkout(self):
        self.setup_workspace(); other=Path(self.temp.name).resolve()/'moved'; self.root.rename(other)
        os.environ['BBM_CLIENT_CONFIG']=str(other/'bbm-client.json')
        self.assertEqual(w.load_paths()['root'], other)
    def test_exact_link_and_orphan(self):
        p=self.setup_workspace(); page=p['WIKI_PATH']/'entities/Example.md'; page.write_text('A page')
        (p['WIKI_PATH']/'index.md').write_text('[[knowledge/wiki/entities/Example|Example]]\n[[wrong/Example]]')
        r=w.audit(p); self.assertEqual(r['orphans'],[]); self.assertEqual(len(r['dead_links']),1)
    def test_symlink_source_not_read(self):
        p=self.setup_workspace(); outside=Path(self.temp.name).resolve()/'secret.md'; outside.write_text('[[bad]]')
        (p['RAW_SOURCES_PATH']/'leak.md').symlink_to(outside)
        self.assertEqual(w.audit(p)['dead_links'],[])
    def test_source_age_and_read_only(self):
        p=self.setup_workspace(); src=p['RAW_SOURCES_PATH']/'meeting.md'; src.write_text('---\nstatus: unprocessed\ndate_captured: 2000-01-01\n---\nText')
        before={f:f.read_bytes() for f in self.root.rglob('*') if f.is_file()}
        self.assertEqual(len(w.audit(p)['stale_sources']),1)
        self.assertEqual(before,{f:f.read_bytes() for f in self.root.rglob('*') if f.is_file()})

if __name__ == '__main__': unittest.main()
