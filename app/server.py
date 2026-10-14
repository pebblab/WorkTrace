#!/usr/bin/env python3
"""Single-process localhost HTTP application. No network dependencies."""
import argparse, html, json, re, secrets, sqlite3, sys, os, fcntl, signal, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs,unquote
from store import Store, read, sha, atomic
from importer import import_transcript

TOKEN=secrets.token_urlsafe(32)

def renderer(text):
    # Deliberately small safe Markdown subset. Raw HTML, images and active URLs never execute.
    parts=[];code=False
    for line in text.splitlines():
        if line.startswith('```'):
            parts.append('</code></pre>' if code else '<pre><code>');code=not code;continue
        escaped=html.escape(line)
        if code:parts.append(escaped+'\n');continue
        m=re.match(r'^(#{1,6}) (.*)',line)
        if m:parts.append('<h'+str(len(m[1]))+'>'+html.escape(m[2])+'</h'+str(len(m[1]))+'>')
        else:parts.append('<div class="line">'+(escaped or '<br>')+'</div>')
    if code:parts.append('</code></pre>')
    return '\n'.join(parts)

class Handler(BaseHTTPRequestHandler):
    server_version='LivingJournal/1'
    def send(self,status,data,kind='application/json; charset=utf-8'):
        if not isinstance(data,bytes):data=(json.dumps(data,ensure_ascii=False) if kind.startswith('application/json') else data).encode()
        self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'")
        self.end_headers();self.wfile.write(data)
    def context(self):
        port=self.server.server_port
        if self.headers.get('Host') not in ['127.0.0.1:'+str(port),'localhost:'+str(port)]:raise ValueError('Invalid localhost Host')
        url=urlparse(self.path);path=unquote(url.path);store=self.server.store
        match=re.match(r'^/archives/(archive-[a-f0-9]{32})(/.*)?$',path)
        if match:
            root=store.data/'archives'/match[1]
            if not (root/'ARCHIVE.json').is_file():raise ValueError('Archive not found')
            store=Store(root);path=match[2] or '/'
        return store,path,{k:v[0] for k,v in parse_qs(url.query).items()}
    def do_GET(self):
        try:
            s,path,q=self.context()
            if path in ['/','/index.html']:
                return self.send(200,(self.server.store.root/'app/static/index.html').read_bytes(),'text/html; charset=utf-8')
            if path in ['/main.js','/markdown.js','/style.css']:
                return self.send(200,(self.server.store.root/'app/static'/path[1:]).read_bytes(),'text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8')
            if path=='/api/instance':return self.send(200,dict(instance=self.server.instance,application='LivingJournal',version='1.0.0'))
            if path=='/api/state':return self.send(200,dict(token=TOKEN,projects=s.projects(),readonly=s.config.get('readonly',False),opening_project=s.config.get('opening_project'),archives=s.archives(),preferences=read(s.data/'preferences.json')))
            if path=='/api/entries':return self.send(200,s.search(q.get('q',''),q.get('project',''),q.get('start',''),q.get('end',''),q.get('excluded')=='1',int(q.get('offset',0))))
            if path=='/api/entry':
                r=s.get(q['id'])
                for f in r['files']:f['present']=s.file_found(r,f)
                return self.send(200,r)
            if path=='/api/overview':return self.send(200,s.overview(q['project']))
            if path=='/api/archive-preview':
                key=q['project'];period=s.project(key)['active_period']
                return self.send(200,dict(entries=[dict(id=r['id'],headline=r['headline'],date=r.get('date')) for r in s.records() if r['project']==key and r.get('period')==period and r.get('status')=='approved' and not r.get('excluded') and not r.get('frozen')]))
            if path=='/api/drafts':return self.send(200,s.drafts())
            if path=='/api/keep':
                return self.send(200,[dict(entry_id=r['id'],headline=r['headline'],**f,available_now=s.file_found(r,f)) for r in s.records() if r['project']==q['project'] for f in r['files'] if f.get('choice')=='keep'])
            if path=='/api/source':
                # Only allow imported, professional source evidence. Never arbitrary file paths.
                p=(s.root/q['path']).resolve()
                if not p.is_relative_to(s.data/'sources') or p.suffix!='.md':raise ValueError('Invalid source path')
                if not p.is_file():return self.send(404,{'error':'Source not available'})
                content=p.read_text(encoding='utf-8')
                page='<!doctype html><meta charset="utf-8"><title>Original exported conversation</title><pre>'+html.escape(content)+'</pre>'
                return self.send(200,page,'text/html; charset=utf-8')
            return self.send(404,{'error':'Not found'})
        except (ValueError,KeyError,OSError) as e:self.send(400,{'error':str(e)})
        except Exception as e:
            print('Request failed:',repr(e),file=sys.stderr);self.send(500,{'error':'Internal error; see terminal. Your source evidence is unchanged.'})
    def do_POST(self):
        try:
            s,path,q=self.context()
            origin=self.headers.get('Origin')
            if origin and origin not in ['http://localhost:'+str(self.server.server_port),'http://127.0.0.1:'+str(self.server.server_port)]:raise ValueError('Foreign origin rejected')
            if self.headers.get('X-Journal-Token')!=TOKEN:raise ValueError('Missing or invalid local edit token')
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<=8*1024*1024:raise ValueError('Invalid request size (max8MiB)')
            p=json.loads(self.rfile.read(size))
            if not isinstance(p,dict):raise ValueError('Expected a JSON object')
            if path=='/api/shutdown':
                self.send(200,dict(stopping=True));threading.Thread(target=self.server.shutdown,daemon=True).start();return
            if path=='/api/project-create':return self.send(200,s.create_project(p['name'],p.get('category','')))
            if path=='/api/transcript-import':return self.send(200,import_transcript(s,p['project'],p['text'],p.get('name','conversation.md')))
            if path=='/api/preferences':
                s.writable();allowed={k:str(p.get(k,''))[:500] for k in ['q','project','start','end','excluded']};atomic(s.data/'preferences.json',allowed);return self.send(200,allowed)
            if path=='/api/save':return self.send(200,s.save(p))
            if path=='/api/rebuild':return self.send(200,dict(indexed=s.rebuild()))
            if path=='/api/overview':return self.send(200,s.save_overview(p['project'],p['text'],p['revision']))
            if path=='/api/draft-import':return self.send(200,s.import_draft(p))
            if path=='/api/draft-review':return self.send(200,s.review_draft(p['id'],p['action'],p.get('changes',{})))
            if path=='/api/archive':return self.send(200,s.archive(p['project'],p['revision'],p.get('confirm')))
            self.send(404,{'error':'Unknown action'})
        except (ValueError,KeyError,OSError,TypeError) as e:self.send(400,{'error':str(e)})
        except Exception as e:
            print('Save failed:',repr(e),file=sys.stderr);self.send(500,{'error':'Save failed; see terminal. Reload before retrying.'})

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--port',type=int,default=0);p.add_argument('--rebuild-index',action='store_true');p.add_argument('--import-draft',type=Path);p.add_argument('--instance',default=uuid.uuid4().hex)
    a=p.parse_args();a.root=a.root.resolve();data=a.root/'data';data.mkdir(parents=True,exist_ok=True)
    lock=(data/'.server.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:p.error('This journal already has a server/writer. Reopen with launch.sh; stop it before offline maintenance.')
    try:s=Store(a.root)
    except (OSError,ValueError,sqlite3.Error) as e:p.error('Unable to open journal: '+str(e))
    if a.rebuild_index:print('Indexed',s.rebuild(),'entries');return
    if a.import_draft:print(json.dumps(s.import_draft(read(a.import_draft)),indent=2));return
    try:server=ThreadingHTTPServer(('127.0.0.1',a.port),Handler)
    except OSError as e:p.error('Cannot bind localhost port; use another --port or --port 0: '+str(e))
    server.store=s;server.instance=a.instance
    url='http://127.0.0.1:'+str(server.server_port)+'/'
    runtime=data/'.runtime.json';atomic(runtime,dict(pid=os.getpid(),url=url,instance=a.instance))
    def stop(signum,frame):threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop)
    print('Living Journal: '+url,flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:print('\nStopped')
    finally:
        server.server_close()
        if runtime.exists() and read(runtime).get('instance')==a.instance:runtime.unlink()
        lock.close()
if __name__=='__main__':main()
