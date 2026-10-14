"""Quoted search additions. Unquoted terms retain the existing FTS prefix path."""
import re

def terms(query):
    result=[];at=0
    while at<len(query):
        if query[at]=='"':
            end=query.find('"',at+1)
            if end>=0:
                value=' '.join(query[at+1:end].split())
                if value:result.append((value,True))
                at=end+1;continue
        end=query.find('"',at+1) if query[at]=='"' else query.find('"',at)
        if end<0:end=len(query)
        result.extend((word,False) for word in re.findall(r'\w+',query[at:end]))
        at=end
    return result

def exact_pattern(value):
    parts=value.split()
    escaped=r'\s+'.join(re.escape(part) for part in parts)
    return (r'(?<!\w)' if re.match(r'\w',value[0]) else '')+escaped+(r'(?!\w)' if re.match(r'\w',value[-1]) else '')

def quoted_patterns(query):
    return [re.compile(exact_pattern(value),re.I) for value,quoted in terms(query) if quoted]

def highlight_pattern(query):
    items=terms(query)
    if not items:return None
    if not any(quoted for _,quoted in items):return re.compile('|'.join(re.escape(w) for w in re.findall(r'\w+',query)),re.I)
    patterns=[exact_pattern(value) if quoted else re.escape(value) for value,quoted in items]
    return re.compile('|'.join(sorted(patterns,key=len,reverse=True)),re.I)

def fts_expression(query):
    # No quoted clauses: byte-for-byte same token/prefix expression as before.
    clauses=[]
    for value,quoted in terms(query):
        for word in re.findall(r'\w+',value):clauses.append('"'+word+'"'+('' if quoted else '*'))
    return ' AND '.join(clauses)
