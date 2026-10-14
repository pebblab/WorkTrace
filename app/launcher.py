"""Linux single-instance launcher. No service installation, signals to unknown PIDs, or downloads."""
import argparse,fcntl,json,os,socket,subprocess,sys,time,urllib.request,uuid,webbrowser
from pathlib import Path
from urllib.parse import urlparse

def preflight():
    if sys.version_info<(3,10):raise RuntimeError('Python3.10+ required. On Debian/Mint: install python3 using your software manager.')
    try:
        import sqlite3
        from zoneinfo import ZoneInfo
        ZoneInfo('America/New_York')
        with sqlite3.connect(':memory:') as db:db.execute('CREATE VIRTUAL TABLE probe USING fts5(text)')
    except Exception as e:raise RuntimeError('Python SQLite FTS5 and system tzdata required. Debian/Mint packages: python3, libsqlite3-0, tzdata. Nothing installed automatically. '+str(e))

def request(url,path,payload=None,token=None):
    parsed=urlparse(url)
    if parsed.scheme!='http' or parsed.hostname!='127.0.0.1' or not parsed.port or parsed.path!='/':raise ValueError('Invalid runtime URL')
    headers={};data=None
    if payload is not None:data=json.dumps(payload).encode();headers={'Content-Type':'application/json','X-Journal-Token':token or ''}
    with urllib.request.urlopen(urllib.request.Request(url+path,data=data,headers=headers),timeout=2) as res:return json.load(res)

def running(path):
    try:
        state=json.loads(path.read_text());actual=request(state['url'],'api/instance')
        return state if actual.get('application')=='LivingJournal' and actual.get('instance')==state.get('instance') else None
    except (OSError,ValueError,KeyError):return None

def open_browser(url,disabled):
    if disabled:return
    try:
        if not webbrowser.open(url):print('Browser could not be opened. Open this URL manually: '+url)
    except Exception:print('Open this URL manually: '+url)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stop',action='store_true');parser.add_argument('--no-browser',action='store_true');parser.add_argument('--port',type=int,default=8780);parser.add_argument('--rebuild-index',action='store_true');parser.add_argument('--import-draft',type=Path)
    args=parser.parse_args();preflight();root=Path(__file__).resolve().parents[1];data=root/'data';data.mkdir(exist_ok=True)
    with (data/'.launcher.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        runtime=data/'.runtime.json';state=running(runtime)
        if args.stop:
            if not state:print('No responding Living Journal instance for this folder. No unrelated process was terminated.');return
            token=request(state['url'],'api/state')['token'];request(state['url'],'api/shutdown',{},token)
            for _ in range(50):
                if not runtime.exists():print('Living Journal stopped.');return
                time.sleep(.1)
            raise RuntimeError('Server has not stopped yet; inspect data/server.log. No force-kill performed.')
        if args.rebuild_index or args.import_draft:
            if state:
                token=request(state['url'],'api/state')['token']
                result=request(state['url'],'api/rebuild' if args.rebuild_index else 'api/draft-import',{} if args.rebuild_index else json.loads(args.import_draft.read_text()),token)
                print(json.dumps(result));return
            command=[sys.executable,str(root/'app/server.py'),'--root',str(root)]
            command+=['--rebuild-index'] if args.rebuild_index else ['--import-draft',str(args.import_draft.resolve())]
            subprocess.run(command,check=True);return
        if state:print('Reopening '+state['url']);open_browser(state['url'],args.no_browser);return
        # An unresponsive suspended instance still holds the server lock. Never
        # launch another writer or kill it based on stale PID information.
        with (data/'.server.lock').open('a') as guard:
            try:fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise RuntimeError('This folder has an unresponsive running instance. Resume it in its terminal or stop it there; no duplicate server started.')
        port=args.port
        if not 0<=port<=65535:raise ValueError('Port must be between0 and65535')
        if port:
            try:
                with socket.socket() as probe:probe.bind(('127.0.0.1',port))
            except OSError:port=0
        instance=uuid.uuid4().hex
        with (data/'server.log').open('ab') as log:
            process=subprocess.Popen([sys.executable,str(root/'app/server.py'),'--root',str(root),'--port',str(port),'--instance',instance],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1'))
        for _ in range(100):
            state=running(runtime)
            if state and state['instance']==instance:print('Living Journal: '+state['url']);open_browser(state['url'],args.no_browser);return
            if process.poll() is not None:raise RuntimeError('Startup failed. See data/server.log. No packages installed or other server stopped.')
            time.sleep(.1)
        raise RuntimeError('Startup timed out. Check data/server.log; no force-kill performed.')

if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError,ValueError,subprocess.CalledProcessError) as e:
        print('Living Journal: '+str(e),file=sys.stderr)
        if '--no-browser' not in sys.argv and sys.stdin.isatty():
            try:input('Press Enter to close this launcher.')
            except EOFError:pass
        sys.exit(1)
