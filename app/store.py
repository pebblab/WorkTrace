"""Portable, manual-first records. Standard library only; SQLite is disposable."""
import hashlib, json, os, re, shutil, sqlite3, threading, uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('America/New_York')
LOCK = threading.RLock()
HASH_CACHE = {}

def sha(b): return hashlib.sha256(b).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def atomic(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)+'\n'
    tmp = p.with_name(p.name+'.'+uuid.uuid4().hex+'.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,p)

def valid_id(s):
    if not re.fullmatch(r'[a-z]+-[a-f0-9]{32}',s): raise ValueError('Invalid record ID')
    return s

class Store:
    def __init__(self, root):
        self.root=Path(root).resolve(); self.data=self.root/'data'
        self.data.mkdir(parents=True,exist_ok=True)
        if not (self.data/'config.json').exists():atomic(self.data/'config.json',dict(version=1,readonly=False,timezone='America/New_York'))
        if not (self.data/'projects.json').exists():atomic(self.data/'projects.json',dict(projects=[]))
        if not (self.data/'preferences.json').exists():atomic(self.data/'preferences.json',{})
        self.config=read(self.data/'config.json'); self.db=self.data/'search.sqlite'
        if not self.db.exists(): self.rebuild()
    def writable(self):
        if self.config.get('readonly'): raise ValueError('Archived period is read-only. Open the active journal to begin a new period.')
    def projects(self): return read(self.data/'projects.json')['projects']
    def create_project(self,name,category=''):
        with LOCK:
            self.writable()
            name=str(name).strip()
            if not name or len(name)>200:raise ValueError('Enter a project name (up to200 characters)')
            key='project-'+uuid.uuid4().hex
            project=dict(id=key,key=key,label=name,category=str(category)[:200],active_period='period-'+uuid.uuid4().hex,archived_periods=[])
            atomic(self.data/'overviews'/(key+'.md'),'# '+name+'\n\nAdd a purpose, important decisions, reported/verified results, limitations, artifacts and future directions.\n\nOpen the project in the journal to see its history.\n')
            projects=self.projects();projects.append(project);atomic(self.data/'projects.json',dict(projects=projects));return project
    def project(self,key):
        for p in self.projects():
            if p['key']==key:return p
        raise ValueError('Unknown project')
    def overview_path(self,key):
        self.project(key); return self.data/'overviews'/(key+'.md')
    def overview(self,key):
        p=self.overview_path(key); text=p.read_text(encoding='utf-8');return dict(text=text,revision=sha(text.encode()))
    def save_overview(self,key,text,revision):
        with LOCK:
            self.writable();p=self.overview_path(key)
            if self.overview(key)['revision']!=revision:raise ValueError('Overview changed; reload before saving')
            atomic(self.data/'backups'/('overview-'+uuid.uuid4().hex+'.md'),p.read_text())
            atomic(p,text);return self.overview(key)
    def records(self):
        for p in sorted((self.data/'entries').glob('*/record.json')):yield read(p)
    def get(self,id):
        valid_id(id);p=self.data/'entries'/id/'record.json'
        if not p.exists():raise ValueError('Entry not found')
        r=read(p);body=(p.parent/r['body']).read_text(encoding='utf-8')
        r['text']=body;r['revision']=sha(p.read_bytes()+body.encode());return r
    def write(self,r,text):
        folder=self.data/'entries'/valid_id(r['id']);body='text/'+sha(text.encode())+'.md'
        p=folder/body
        # A human may have edited a Markdown version directly. Never overwrite or
        # reuse its old content-addressed name for different bytes.
        if p.exists() and p.read_text(encoding='utf-8')!=text:
            body='text/'+sha(text.encode())+'-'+uuid.uuid4().hex+'.md';p=folder/body
        if not p.exists():atomic(p,text)
        r={k:v for k,v in r.items() if k not in ['text','revision']};r['body']=body
        atomic(folder/'record.json',r)
    def save(self,payload):
        with LOCK:
            self.writable()
            if payload.get('id'):
                r=self.get(payload['id'])
                if r.get('frozen'):raise ValueError('This approved archived entry is frozen; begin a new period')
                if payload.get('revision')!=r['revision']:raise ValueError('Entry changed; reload to avoid overwriting edits')
                atomic(self.data/'backups'/(r['id']+'-'+uuid.uuid4().hex+'.json'),r)
            else:
                r=dict(id='manual-'+uuid.uuid4().hex,origin='manual',files=[],sources=[],topics=[],excluded=False,status='approved',timestamp_original=None,time_basis='human-local',timezone='America/New_York',pairing_flags=[])
            project=payload.get('project',r.get('project'))
            self.project(project)
            r['project']=project;r['period']=self.project(project)['active_period']
            for key in ['headline','summary','excluded']:
                if key in payload:r[key]=payload[key]
            r['headline']=str(r.get('headline','')).strip()[:200] or ' '.join(payload.get('text',r.get('text','Journal note')).split())[:100] or 'Journal note'
            r['summary']=str(r.get('summary',''))
            r['excluded']=bool(r.get('excluded'))
            if payload.get('approve'):r['status']='approved'
            date=payload.get('date',r.get('date'))
            if date:
                parsed=datetime.fromisoformat(date)
                if parsed.tzinfo is not None:date=parsed.astimezone(TZ).isoformat()
            else:date=datetime.now(TZ).isoformat(timespec='seconds') if r['origin']=='manual' else None
            if date!=r.get('date'):
                r['date_basis']='human-edited' if r['origin']!='manual' else 'human-local'
            r['date']=date
            if 'files' in payload:
                choices={f['id']:f.get('choice') for f in payload['files']}
                for f in r['files']:
                    if f['id'] in choices:
                        if choices[f['id']] not in ['keep','reference','ignore']:raise ValueError('Invalid file choice')
                        f['choice']=choices[f['id']]
            text=payload.get('text',r.get('text',''))
            if not isinstance(text,str) or not text.strip():raise ValueError('Write some entry text')
            self.write(r,text);self.index_one(r['id']);return self.get(r['id'])
    def connection(self):
        c=sqlite3.connect(self.db,timeout=30);c.row_factory=sqlite3.Row;return c
    def index_row(self,r):
        full=self.get(r['id']);name=self.project(r['project'])['label']
        return (r['id'],r.get('date') or '',r['project'],int(r.get('excluded',False)),r.get('status','imported'),r.get('headline',''),r.get('summary',''),full['text'],name,json.dumps([r.get('topics',[]),r.get('files',[]),r.get('sources',[]),r.get('pairing_flags',[])],ensure_ascii=False))
    def rebuild(self):
        with LOCK:
            self.data.mkdir(parents=True,exist_ok=True)
            tmp=self.db.with_suffix('.rebuild-'+uuid.uuid4().hex)
            c=sqlite3.connect(tmp)
            try:
                c.execute('CREATE VIRTUAL TABLE journal USING fts5(id UNINDEXED,date UNINDEXED,project UNINDEXED,excluded UNINDEXED,status UNINDEXED,headline,summary,text,project_name,metadata)')
                for r in self.records():c.execute('INSERT INTO journal VALUES (?,?,?,?,?,?,?,?,?,?)',self.index_row(r))
                c.commit();count=c.execute('SELECT count(*) FROM journal').fetchone()[0]
            finally:c.close()
            os.replace(tmp,self.db)
            if not self.config.get('readonly'):self.monthly_views()
            return count
    def monthly_views(self):
        groups={}
        for r in self.records():
            if r.get('excluded'):continue
            key=r['date'][:7] if r.get('date') else 'UNDATED'
            groups.setdefault(key,[]).append(r)
        folder=self.data/'monthly'
        # Retain empty derived months instead of deleting files when entries are excluded.
        for p in folder.glob('*.md'):groups.setdefault(p.stem,[])
        links=['# Primary exchange journal','', 'Derived monthly navigation. Edit entries in the application, not these views. Original imported sources remain available from each entry.','']
        for key,rs in sorted(groups.items()):
            lines=['# '+key+' — conversation exchanges','','Derived navigation, not duplicated conversation text.','']
            for r in sorted(rs,key=lambda r:(r.get('date') or '',r['id'])):
                title=r['headline'].replace('[','').replace(']','').replace('\n',' ')
                lines.append('- '+(r.get('date') or 'Undated')+' — ['+title+'](../entries/'+r['id']+'/'+r['body']+') — '+r['project'])
                if r.get('summary'):lines.append('  '+r['summary'].replace('\n',' '))
            atomic(folder/(key+'.md'),'\n'.join(lines)+'\n');links.append('- ['+key+'](monthly/'+key+'.md) — '+str(len(rs))+' entries')
        atomic(self.data/'JOURNAL.md','\n'.join(links)+'\n')
    def index_one(self,id):
        with self.connection() as c:
            c.execute('DELETE FROM journal WHERE id=?',(id,));c.execute('INSERT INTO journal VALUES (?,?,?,?,?,?,?,?,?,?)',self.index_row(self.get(id)))
        if not self.config.get('readonly'):self.monthly_views()
    def search(self,q='',project='',start='',end='',excluded=False,offset=0,limit=40):
        clauses=['excluded=?'];params=[int(excluded)]
        from search_query import terms, exact_pattern
        patterns=[re.compile(exact_pattern(value) if quoted else re.escape(value),re.I) for value,quoted in terms(q)]
        if patterns:clauses.append('query_match(headline,summary,text,project_name,metadata)=1')
        if project:clauses.append('project=?');params.append(project)
        if start:clauses.append('date>=?');params.append(start)
        if end:clauses.append('date<?');params.append(end+'T99')
        where=' AND '.join(clauses)
        with self.connection() as c:
            if patterns:
                c.create_function('query_match',5,lambda *fields:int(all(any(pattern.search(field or '') for field in fields) for pattern in patterns)))
            total=c.execute('SELECT count(*) FROM journal WHERE '+where,params).fetchone()[0]
            columns='id,headline,summary,text,project_name,metadata' if patterns else 'id'
            rows=c.execute('SELECT '+columns+' FROM journal WHERE '+where+" ORDER BY date DESC,id LIMIT ? OFFSET ?",params+[min(int(limit),100),max(int(offset),0)]).fetchall()
        results=[]
        for row in rows:
            from ui import contextual_snippet, display_headline
            r=self.get(row['id']);text=r.pop('text')
            r['display_headline']=display_headline(self.root,r)
            r['snippet']=contextual_snippet(r,text,q,[row[key] for key in ['headline','summary','text','project_name','metadata']] if patterns else None)
            for f in r['files']:f['present']=self.file_found(r,f)
            results.append(r)
        return dict(total=total,entries=results)
    def drafts(self):return [read(p) for p in sorted((self.data/'drafts').glob('*.json'))]
    def import_draft(self,p):
        with LOCK:
            self.writable()
            if p.get('status','draft')!='draft':raise ValueError('Imported agent content must be draft')
            self.project(p['project'])
            if not isinstance(p.get('text'),str) or not p['text'].strip():raise ValueError('Draft text required')
            if p.get('date'):datetime.fromisoformat(p['date'])
            key=str(p.get('id') or sha(json.dumps(p,sort_keys=True).encode()))
            id='draft-'+uuid.uuid5(uuid.NAMESPACE_URL,key).hex
            path=self.data/'drafts'/(id+'.json')
            if path.exists():return read(path)
            files=[]
            for n,f in enumerate(p.get('files',[])):
                if not isinstance(f,dict) or f.get('direction') not in ['provided','generated','reference']:raise ValueError('Draft files need name and direction provided/generated/reference')
                files.append(dict(id='file-'+uuid.uuid5(uuid.NAMESPACE_URL,id+str(n)).hex,name=str(f['name']),direction=f['direction'],choice='reference',basis='agent-proposed association; not verified',matched_path=None,candidates=[],sha256=None))
            r=dict(id=id,external_id=key,status='draft',project=p['project'],date=p.get('date'),headline=str(p.get('headline','Agent draft'))[:200],text=p['text'],summary=p.get('summary',''),sources=p.get('sources',[]),files=files)
            atomic(path,r);return r
    def review_draft(self,id,action,changes):
        with LOCK:
            self.writable();p=self.data/'drafts'/(valid_id(id)+'.json');r=read(p)
            if r['status']!='draft':return r
            if action not in ['approve','reject']:raise ValueError('Unknown review action')
            if action=='approve':
                # Deterministic approval ID also recovers interruption before draft status commit.
                eid='agent-'+id.split('-',1)[1];entrypath=self.data/'entries'/eid/'record.json'
                if not entrypath.exists():
                    project=changes.get('project',r['project']);self.project(project)
                    text=changes.get('text',r['text']);date=changes.get('date',r.get('date'))
                    if date:datetime.fromisoformat(date)
                    if not text.strip():raise ValueError('Draft text required')
                    entry=dict(id=eid,origin='agent-approved',headline=changes.get('headline',r['headline']),summary=changes.get('summary',r['summary']),project=project,date=date,period=self.project(project)['active_period'],status='approved',excluded=False,sources=r['sources'],files=r['files'],topics=[],timezone='America/New_York',time_basis='agent-proposed-human-approved',timestamp_original=None,pairing_flags=[])
                    self.write(entry,text)
                self.index_one(eid);r['entry_id']=eid
            r['status']='approved' if action=='approve' else 'rejected';atomic(p,r);return r
    def file_found(self,r,f):
        path=f.get('matched_path')
        if not path:return False
        original=self.root/path
        try:
            if original.is_symlink():return False
            p=original.resolve()
            if not p.is_file():return False
            expected=f.get('sha256')
            if expected:
                stat=p.stat();key=(str(p),stat.st_mtime_ns,stat.st_size)
                if key not in HASH_CACHE:HASH_CACHE[key]=sha(p.read_bytes())
                return HASH_CACHE[key]==expected
            return True
        except OSError:return False
    def archive(self,key,overview_revision,confirm):
        with LOCK:
            self.writable();project=self.project(key)
            if confirm is not True:raise ValueError('Review overview and explicitly confirm archive')
            if self.overview(key)['revision']!=overview_revision:raise ValueError('Overview changed; review again')
            period=project['active_period'];aid='archive-'+uuid.uuid4().hex
            dest=self.data/'archives'/aid;tmp=dest.with_name(aid+'.pending');tmp.mkdir(parents=True)
            records=[self.get(r['id']) for r in self.records() if r['project']==key and r.get('period')==period and r.get('status')=='approved' and not r.get('excluded') and not r.get('frozen')]
            if not records:
                shutil.rmtree(tmp)
                raise ValueError('No approved records in the active period; approve entries first')
            try:
                shutil.copytree(self.root/'app',tmp/'app',ignore=shutil.ignore_patterns('__pycache__'))
                shutil.copyfile(self.root/'launch.sh',tmp/'launch.sh')
                for rel in ['LivingJournal.desktop','VERSION','LICENSE']:
                    if (self.root/rel).exists():shutil.copyfile(self.root/rel,tmp/rel)
                data=tmp/'data';data.mkdir()
                atomic(data/'config.json',dict(version=1,readonly=True,timezone='America/New_York',archive_id=aid,opening_project=key))
                archived=dict(project);archived['active_period']=period
                atomic(data/'projects.json',dict(projects=[archived]))
                atomic(data/'preferences.json',{})
                atomic(data/'overviews'/(key+'.md'),self.overview(key)['text'])
                selected=[]
                for r in records:
                    folder=data/'entries'/r['id'];text=r.pop('text');r.pop('revision');r['frozen']=aid
                    body='text/'+sha(text.encode())+'.md';r['body']=body
                    atomic(folder/body,text);atomic(folder/'record.json',r)
                    for src in r.get('sources',[]):
                        rel=src.get('local_path')
                        if rel:
                            origin=(self.root/rel).resolve()
                            if not origin.is_relative_to(self.data/'sources'):raise ValueError('Source outside journal evidence')
                            target=tmp/rel;target.parent.mkdir(parents=True,exist_ok=True)
                            if not target.exists():shutil.copyfile(origin,target)
                    for f in r.get('files',[]):selected.append(dict(entry_id=r['id'],**f,available_now=self.file_found(r,f)))
                atomic(data/'files.json',selected)
                atomic(tmp/'README.md','# Archived project period\n\nRun `bash launch.sh`. The launcher selects an available local port and opens your browser. Overview opens first. Journal/source evidence is self-contained. External project files are not included; Keep marks future preservation only. This period is read-only.\n')
                manifest={str(p.relative_to(tmp)):sha(p.read_bytes()) for p in tmp.rglob('*') if p.is_file()}
                atomic(tmp/'ARCHIVE.json',dict(id=aid,project=key,period=period,entry_count=len(records),files=manifest,external_files_included=False))
                os.replace(tmp,dest)
                for r in records:
                    original=self.get(r['id']);original['frozen']=aid;self.write(original,original['text']);self.index_one(r['id'])
                projects=self.projects()
                for p in projects:
                    if p['key']==key:
                        p.setdefault('archived_periods',[]).append(dict(id=aid,period=period,path=dest.relative_to(self.root).as_posix()))
                        p['active_period']='period-'+uuid.uuid4().hex
                atomic(self.data/'projects.json',dict(projects=projects))
                self.monthly_views()
                return dict(id=aid,entries=len(records),path=dest.relative_to(self.root).as_posix(),new_period=self.project(key)['active_period'])
            except Exception:
                if tmp.exists():shutil.rmtree(tmp)
                raise
    def archives(self):
        return [read(p) for p in (self.data/'archives').glob('*/ARCHIVE.json')]
