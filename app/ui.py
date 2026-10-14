"""Read-only presentation; independent of any particular project or export."""
import re
from search_query import highlight_pattern

def contextual_snippet(record,text,query,indexed_fields=None):
    pattern=highlight_pattern(query)
    if pattern is None:return ''
    clean=re.sub(r'^## (?:User prompt|Assistant response \d+)\s*$','',text,flags=re.M)
    clean=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',clean)
    clean=re.sub(r'^[>#*\-]+\s*','',clean,flags=re.M)
    clean=re.sub(r'[`*_]','',clean);clean=' '.join(clean.split());match=pattern.search(clean)
    if not match:
        clean=' · '.join([record.get('summary',''),record['headline'],record['project']]+[f['name'] for f in record.get('files',[])])
        match=pattern.search(clean)
    if not match and indexed_fields:
        for field in indexed_fields:
            clean=' '.join((field or '').split());match=pattern.search(clean)
            if match:break
    if not match:return 'Match in project/topic/source metadata.'
    start=max(0,match.start()-90);end=min(len(clean),match.end()+170)
    return ('…' if start else '')+clean[start:end]+('…' if end<len(clean) else '')

def display_headline(root,record):return record['headline']
