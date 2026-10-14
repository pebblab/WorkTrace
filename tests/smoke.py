"""Independent synthetic HTTP/launcher/relocation smoke. No original journal access."""
import json,os,shutil,subprocess,sys,tempfile,time,urllib.request,urllib.error,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run():
    checks=[]
    with tempfile.TemporaryDirectory() as tmp:
        work=Path(tmp)/'Synthetic Public Journal';shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns('__pycache__','.git','MANIFEST.json'))
        # Public source data contains only README; never copy arbitrary local data.
        assert sorted(p.name for p in (work/'data').iterdir())==['README.md']
        def launch(*args,root=work):return subprocess.check_output(['bash',str(root/'launch.sh'),'--no-browser',*args],text=True,stderr=subprocess.STDOUT)
        def runtime(root=work):return json.loads((root/'data/.runtime.json').read_text())
        def req(endpoint,payload=None,status=200,root=work,token=True):
            url=runtime(root)['url'];headers={};body=None
            if payload is not None:
                csrf=req('api/state',root=root)['token'] if token else ''
                headers={'Content-Type':'application/json','X-Journal-Token':csrf};body=json.dumps(payload).encode()
            try:
                with urllib.request.urlopen(urllib.request.Request(url+endpoint,data=body,headers=headers),timeout=15) as response:code=response.status;data=response.read();kind=response.headers['Content-Type']
            except urllib.error.HTTPError as e:code=e.code;data=e.read();kind=e.headers['Content-Type']
            assert code==status,(endpoint,code,data[:300]);return json.loads(data) if 'json' in kind else data.decode()
        try:
            launch('--port','0');state=req('api/state');assert not state['projects'];assert req('api/entries')['total']==0;checks.append('Fresh empty first launch and200 HTTP')
            before=runtime();launch();assert runtime()['pid']==before['pid'];checks.append('Repeated launch reopens one instance')
            for resource in ['','style.css','main.js','markdown.js']:req(resource)
            checks.append('HTML/CSS/JavaScript served')
            p=req('api/project-create',dict(name='Garden research',category='Synthetic examples'))
            note=req('api/save',dict(project=p['key'],text='A cat and a stress pattern.',headline='Experiment note'))
            edited=req('api/save',dict(note,headline='Edited note',text='A cat and a stress pattern.'))
            req('api/save',dict(note,text='Stale'),status=400);checks.append('Arbitrary project, manual entry/edit and conflict protection')
            for text in ['catch category cats','concatenate'] :req('api/save',dict(project=p['key'],text=text))
            assert req('api/entries?q=cat')['total']==3;assert req('api/entries?q=%22cat%22')['total']==1
            assert req('api/entries?q=%22stress%20pattern%22')['total']==1;assert req('api/entries?q=%22cat%22')['entries'][0]['snippet'];checks.append('Substring, quoted whole word/phrase and contextual snippets')
            edited=req('api/save',dict(edited,excluded=True));assert req('api/entries?q=%22cat%22')['total']==0
            edited=req('api/save',dict(edited,excluded=False));assert req('api/entries?q=%22cat%22')['total']==1;checks.append('Exclude and restore')
            transcript='User: Prepare a garden report.\nAssistant: [Report](sandbox:/mnt/data/report.md)\nUser: Compare @input.csv\nAssistant: Here is an analysis.\n'
            imported=req('api/transcript-import',dict(project=p['key'],text=transcript));assert len(imported['entries'])==2
            assert req('api/transcript-import',dict(project=p['key'],text=transcript))['duplicate'];checks.append('Supported transcript import and duplicate prevention')
            historic=req('api/entry?id='+imported['entries'][0]);assert not historic['files'][0]['present'];assert 'Original' in req('api/source?path='+historic['sources'][0]['local_path']);checks.append('Missing file presence and offline source evidence')
            historic=req('api/save',dict(historic,approve=True,files=[dict(id=historic['files'][0]['id'],choice='keep')]))
            assert req('api/keep?project='+p['key']);checks.append('Explicit approval and editable file Keep choice')
            draft=req('api/draft-import',dict(id='public-synthetic',project=p['key'],text='Agent draft neutrontrail'))
            assert req('api/entries?q=neutrontrail')['total']==0
            req('api/draft-review',dict(id=draft['id'],action='approve',changes=dict(text='Human edited neutrontrail')))
            assert req('api/entries?q=neutrontrail')['total']==1;checks.append('Agent draft isolation/edit and human approval')
            rebuild=req('api/rebuild',{});assert rebuild['indexed']==6;checks.append('Rebuildable derived index')
            overview=req('api/overview?project='+p['key']);overview=req('api/overview',dict(project=p['key'],text='# Garden research\nSynthetic overview reviewed.',revision=overview['revision']))
            archive=req('api/archive',dict(project=p['key'],revision=overview['revision'],confirm=True));assert archive['entries']==5
            prefix='archives/'+archive['id']+'/'
            assert req(prefix+'api/state')['readonly'];assert req(prefix+'api/entries')['total']==5
            req(prefix+'api/save',dict(project=p['key'],text='Frozen'),status=400);checks.append('Approved-only archive, overview, readonly reopen')
            nextnote=req('api/save',dict(project=p['key'],text='New work'));assert nextnote['period']!=note['period'];checks.append('Project reopen starts a new work period')
            req('api/preferences',dict(q='new work',project=p['key']))
            launch('--stop');assert not (work/'data/.runtime.json').exists();launch('--port','0')
            assert req('api/state')['preferences']['q']=='new work';assert req('api/entry?id='+edited['id'])['headline']=='Edited note';checks.append('Clean stop/restart, preferences and data persistence')
            req('api/save',dict(project=p['key'],text='Denied'),status=400,token=False)
            req('api/source?path=../../etc/passwd',status=400);checks.append('Edit token and source path traversal protection')
            launch('--stop');moved=Path(tmp)/'Different directory'/ 'Journal moved';moved.parent.mkdir();shutil.move(str(work),moved)
            launch('--port','0',root=moved);assert req('api/entries',root=moved)['total']==7;checks.append('Full journal relocation without original workspace')
            launch('--stop',root=moved)
            portable=Path(tmp)/'Standalone archive';shutil.copytree(moved/archive['path'],portable)
            launch('--port','0',root=portable);assert req('api/state',root=portable)['opening_project']==p['key'];assert req('api/entries',root=portable)['total']==5
            req('api/source?path='+historic['sources'][0]['local_path'],root=portable);checks.append('Standalone archive relocation and source evidence')
            launch('--stop',root=portable)
            # Occupied preferred port is preserved; an unrelated socket is never terminated.
            with socket.socket() as unrelated:
                unrelated.bind(('127.0.0.1',0));unrelated.listen();port=unrelated.getsockname()[1]
                launch('--port',str(port),root=moved);assert int(runtime(moved)['url'].split(':')[-1].strip('/'))!=port
                assert unrelated.fileno()>=0;launch('--stop',root=moved)
            checks.append('Occupied unrelated port safely selects a different port')
            (moved/'data/.runtime.json').write_text(json.dumps({'pid':99999999,'url':'http://127.0.0.1:1/','instance':'stale'}))
            launch('--port','0',root=moved);launch('--stop',root=moved);checks.append('Stale runtime safely replaced')
        finally:
            for candidate in [work,locals().get('moved'),locals().get('portable')]:
                if candidate and (candidate/'data/.runtime.json').exists():
                    try:launch('--stop',root=candidate)
                    except Exception:pass
    return dict(passed=len(checks),failed=0,checks=checks,data='synthetic only')
if __name__=='__main__':print(json.dumps(run(),indent=2))
