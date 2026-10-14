"""Synthetic-only public regressions; never open an existing user's journal."""
import sys,tempfile,unittest,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from store import Store,read,sha
from importer import parse,import_transcript,date_value
from search_query import highlight_pattern

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        shutil.copytree(ROOT/'app',self.root/'app',ignore=shutil.ignore_patterns('__pycache__'))
        for name in ['launch.sh','LivingJournal.desktop','VERSION','LICENSE']:shutil.copyfile(ROOT/name,self.root/name)
        self.s=Store(self.root);self.p=self.s.create_project('Sample research','Learning')
    def tearDown(self):self.tmp.cleanup()
    def add(self,text):return self.s.save(dict(project=self.p['key'],text=text))
    def test_empty_first_launch(self):
        self.assertEqual(self.s.search()['total'],0);self.assertEqual(self.p['label'],'Sample research')
        self.assertEqual(self.p['category'],'Learning')
    def test_note_edit_conflict_and_restart(self):
        r=self.add('A manual note');changed=self.s.save(dict(r,text='Edited note',headline='New heading',summary='Summary'))
        self.assertEqual(Store(self.root).get(r['id'])['text'],'Edited note')
        with self.assertRaises(ValueError):self.s.save(dict(r,text='stale'))
        self.assertEqual(changed['headline'],'New heading')
    def test_exclusion_restore_rebuild(self):
        r=self.add('A searchable note');r=self.s.save(dict(r,excluded=True));self.assertEqual(self.s.search()['total'],0)
        self.assertEqual(self.s.search(excluded=True)['total'],1);self.s.save(dict(r,excluded=False));self.s.rebuild();self.assertEqual(self.s.search('searchable')['total'],1)
    def test_substring_whole_words_phrases_filters(self):
        for text in ['cat','CAT!','catch category cats','concatenate','stress pattern','STRESS  pattern','stress-pattern','stress patterns']:self.add(text)
        self.assertEqual(self.s.search('cat')['total'],4)
        self.assertEqual(self.s.search('"cat"')['total'],2)
        self.assertEqual(self.s.search('"stress pattern"')['total'],2)
        self.assertEqual(self.s.search('""')['total'],8);self.assertEqual(self.s.search('"cat')['total'],4)
        self.assertEqual(self.s.search('cat',start='2099-01-01')['total'],0)
        self.assertEqual(self.s.search('cat',project=self.p['key'])['total'],4)
        self.assertEqual(highlight_pattern('"cat"').findall('cat CAT! cats catch'),['cat','CAT'])
        self.assertIn('cat',self.s.search('"cat"')['entries'][0]['snippet'].lower())
    def test_exports_pairing_and_fences(self):
        text='# you asked\nmessage time: 2026-01-02 10:05:00\nDescribe a cat.\n---\n# chatgpt response\nA cat.\n```\nUser: not a role\n```\n---\n# chatgpt response\nAnother response.\n---\n# you asked\nA second question.\n'
        result=import_transcript(self.s,self.p['key'],text);self.assertEqual(len(result['entries']),2);self.assertEqual(result['messages'],4)
        first=self.s.get(result['entries'][0]);self.assertEqual(len(first['sources']),3);self.assertIn('Assistant response 2',first['text']);self.assertEqual(first['timestamp_original'],'2026-01-02 10:05:00')
        self.assertIsNone(self.s.get(result['entries'][1])['date']);self.assertTrue(self.s.get(result['entries'][1])['pairing_flags'])
        self.assertTrue(import_transcript(self.s,self.p['key'],text)['duplicate']);self.assertEqual(self.s.search()['total'],2)
    def test_plain_transcript_and_unsupported(self):
        r=import_transcript(self.s,self.p['key'],'User: A prompt\nAssistant: A response\n');self.assertEqual(len(r['entries']),1)
        with self.assertRaises(ValueError):import_transcript(self.s,self.p['key'],'Unstructured text with no role markers')
        self.assertEqual(len(parse('Assistant: Orphan\nUser: New request\n')),2)
    def test_timezone_missing_explicit_and_date_only(self):
        self.assertEqual(date_value('2026-07-01T16:00:00Z')[0],'2026-07-01T12:00:00-04:00')
        self.assertIsNone(date_value(None)[0]);self.assertEqual(date_value('2026-07-01')[0],'2026-07-01')
    def test_draft_isolation_approval_rejection_and_duplicates(self):
        d=self.s.import_draft(dict(id='synthetic-draft',project=self.p['key'],text='Draft only'))
        self.assertEqual(self.s.search()['total'],0);self.assertEqual(self.s.import_draft(dict(id='synthetic-draft',project=self.p['key'],text='Different')),d)
        self.s.review_draft(d['id'],'approve',dict(text='Human approved'));self.s.review_draft(d['id'],'approve',{});self.assertEqual(self.s.search()['total'],1)
        rejected=self.s.import_draft(dict(id='second',project=self.p['key'],text='Discard'));self.s.review_draft(rejected['id'],'reject',{});self.assertEqual(self.s.search()['total'],1)
    def test_missing_files_choices_and_untrusted_draft_presence(self):
        d=self.s.import_draft(dict(project=self.p['key'],text='File report',files=[dict(name='missing.csv',direction='provided',matched_path='/etc/passwd')]))
        approved=self.s.review_draft(d['id'],'approve',{});r=self.s.get(approved['entry_id']);self.assertFalse(self.s.file_found(r,r['files'][0]));self.assertIsNone(r['files'][0]['matched_path'])
        r=self.s.save(dict(r,files=[dict(id=r['files'][0]['id'],choice='keep')]));self.assertEqual(r['files'][0]['choice'],'keep')
    def test_archive_move_sources_and_new_period(self):
        result=import_transcript(self.s,self.p['key'],'User: A task\nAssistant: A reply\n');r=self.s.get(result['entries'][0]);self.s.save(dict(r,approve=True))
        overview=self.s.overview(self.p['key']);archive=self.s.archive(self.p['key'],overview['revision'],True)
        path=self.root/archive['path'];s=Store(path);self.assertEqual(s.search()['total'],1)
        for rel,checksum in read(path/'ARCHIVE.json')['files'].items():self.assertEqual(sha((path/rel).read_bytes()),checksum)
        self.assertTrue((path/s.get(r['id'])['sources'][0]['local_path']).exists())
        with self.assertRaises(ValueError):s.save(dict(project=self.p['key'],text='Read only'))
        with self.assertRaises(ValueError):self.s.save(dict(self.s.get(r['id']),text='Frozen'))
        nextnote=self.add('New period');self.assertNotEqual(nextnote['period'],r['period'])
        moved=self.root/'Moved archive';shutil.copytree(path,moved);self.assertEqual(Store(moved).search()['total'],1)
    def test_direct_markdown_edit_preserved(self):
        r=self.add('Original');p=self.s.data/'entries'/r['id']/r['body'];p.write_text('Manual edit')
        self.s.save(dict(self.s.get(r['id']),text='Original'));self.assertEqual(p.read_text(),'Manual edit')

if __name__=='__main__':unittest.main()
