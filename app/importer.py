"""Explicit local transcript import; no login, scraping, provider API or AI."""
import re,uuid
from datetime import datetime
from store import LOCK,TZ,atomic,read,sha

def parse(text):
    lines=text.splitlines(keepends=True);starts=[];offset=0;fence=None
    for number,line in enumerate(lines):
        marker=re.match(r'^\s*(`{3,}|~{3,})',line)
        if marker:
            token=marker[1][0]
            if fence is None:fence=token
            elif fence==token:fence=None
            offset+=len(line.encode());continue
        if fence is None:
            clean=line.strip();role={'# you asked':'user','# chatgpt response':'assistant'}.get(clean.lower());inline=''
            if not role:
                match=re.match(r'^(?:#{1,6}\s+)?(User|Assistant):\s*(.*)$',clean,re.I)
                if match:role=match[1].lower();inline=match[2]
            if role:starts.append((number,offset,role,inline))
        offset+=len(line.encode())
    if not starts:raise ValueError('No supported role markers. Use User: and Assistant: lines, or # you asked / # chatgpt response.')
    messages=[]
    for i,(line,byte,role,inline) in enumerate(starts):
        last,end=starts[i+1][:2] if i+1<len(starts) else (len(lines),len(text.encode()))
        body=(inline+'\n' if inline else '')+''.join(lines[line+1:last]);timestamp=None
        match=re.search(r'^message time: (.+)$',body,re.M)
        if match:timestamp=match[1].strip();body=body[:match.start()]+body[match.end():]
        body=re.sub(r'\n---\s*$','',body).strip()
        messages.append(dict(ordinal=i,role=role,text=body,start_byte=byte,end_byte=end,start_line=line+1,end_line=last,timestamp=timestamp))
    return messages

def groups(messages):
    current=[]
    for m in messages:
        if m['role']=='user':
            if current:yield current
            current=[m]
        elif current:current.append(m)
        else:yield [m]
    if current:yield current

def date_value(raw):
    if not raw:return None,'missing'
    try:
        value=datetime.fromisoformat(raw.replace('Z','+00:00'))
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw):return raw,'source-date-only'
        if value.tzinfo:return value.astimezone(TZ).isoformat(),'explicit-offset'
        return value.replace(tzinfo=TZ).isoformat(),'assumed-display-zone; source offset absent'
    except ValueError:return None,'unparsed source timestamp; original preserved'

def files(group):
    result=[]
    for m in group:
        matches=[]
        for match in re.finditer(r'\[([^]]+)\]\(([^)]+)\)|@([\w./-]+\.(?:md|txt|csv|tsv|pdf|json|html|zip))',m['text'],re.I):
            name=match[2] or match[3]
            if not re.search(r'\.(?:md|txt|csv|tsv|pdf|json|html|zip|wav|png|jpg)(?:$|[?#])',name,re.I):continue
            direction='provided' if m['role']=='user' else ('generated' if name.startswith('sandbox:') else 'reference')
            if (name,direction) in matches:continue
            matches.append((name,direction))
            result.append(dict(id='file-'+uuid.uuid5(uuid.NAMESPACE_URL,str(m['ordinal'])+name+direction).hex,name=name,direction=direction,choice='reference',basis='explicit input reference' if direction=='provided' else 'reported output link' if direction=='generated' else 'ordinary reference',matched_path=None,candidates=[],sha256=None))
    return result

def import_transcript(store,project,text,name='conversation.md'):
    with LOCK:
        store.writable();store.project(project)
        if not isinstance(text,str) or not text.strip():raise ValueError('Paste a transcript first')
        messages=parse(text);fingerprint=sha(text.encode());manifest=store.data/'imports'/(fingerprint+'.json')
        if manifest.exists():return dict(read(manifest),duplicate=True)
        # Persist exact source once; stable entry IDs make interrupted retries safe.
        local='data/sources/source-'+fingerprint+'.md';source=store.root/local
        if not source.exists():atomic(source,text)
        ids=[]
        for group in groups(messages):
            first=group[0];id='exchange-'+uuid.uuid5(uuid.NAMESPACE_URL,fingerprint+':'+str(first['ordinal'])).hex
            prompt=first['text'] if first['role']=='user' else '';date,basis=date_value(first['timestamp'])
            headline=' '.join(re.sub(r'[`#*_]','',prompt).split())[:110] or 'Unpaired assistant response'
            body='## User prompt\n\n'+(prompt or '[No preceding user prompt in supplied transcript]')
            for number,m in enumerate(group[1:] if first['role']=='user' else group,1):body+='\n\n## Assistant response '+str(number)+'\n\n'+m['text']
            refs=[dict(local_path=local,source_name=str(name)[:200],source_sha256=fingerprint,ordinal=m['ordinal'],role=m['role'],start_byte=m['start_byte'],end_byte=m['end_byte'],start_line=m['start_line'],end_line=m['end_line'],timestamp_original=m['timestamp']) for m in group]
            flags=[]
            if not prompt:flags.append('No preceding user prompt; original sequence retained')
            if len(group)==1 and first['role']=='user':flags.append('No associated response supplied')
            r=dict(id=id,origin='imported-conversation',headline=headline,summary='',project=project,period=store.project(project)['active_period'],status='imported',excluded=False,topics=[],date=date,timestamp_original=first['timestamp'],time_basis=basis,timezone='America/New_York',sources=refs,files=files(group),pairing_flags=flags)
            if not (store.data/'entries'/id/'record.json').exists():store.write(r,body)
            ids.append(id)
        result=dict(sha256=fingerprint,entries=ids,messages=len(messages),duplicate=False)
        atomic(manifest,result);store.rebuild();return result
