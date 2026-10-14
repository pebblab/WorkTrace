'use strict';
// Small DOM-based Markdown renderer: raw HTML never enters innerHTML.
function inlineMarkdown(parent,text,depth=0){
 if(depth>6){parent.append(document.createTextNode(text));return}
 const tokens=/(`+)([^\n]*?)\1|\[([^\]]+)\]\(([^\s)]+)(?:\s+"[^"]*")?\)|\*\*([^\n]+?)\*\*|__([^\n]+?)__|\*([^*\n]+?)\*|_([^_\n]+?)_|~~([^\n]+?)~~/g;
 let at=0,m;while((m=tokens.exec(text))){parent.append(document.createTextNode(text.slice(at,m.index)));let el;
 if(m[1]){el=document.createElement('code');el.textContent=m[2]}
 else if(m[3]){el=document.createElement('a');inlineMarkdown(el,m[3],depth+1);try{const raw=m[4];const url=new URL(raw,location.href);if(['http:','https:','mailto:'].includes(url.protocol)){el.href=url.href;el.rel='noopener noreferrer';el.target='_blank'}else el.title='Link protocol is not supported safely'}catch{el.title='Invalid link'}}
 else{el=document.createElement(m[5]||m[6]?'strong':m[9]?'del':'em');inlineMarkdown(el,m[5]||m[6]||m[7]||m[8]||m[9],depth+1)}
 parent.append(el);at=tokens.lastIndex}parent.append(document.createTextNode(text.slice(at)));
}
function markdown(text){
 const root=document.createElement('div');root.className='markdown';const lines=text.replace(/\r\n/g,'\n').split('\n');let i=0;
 const special=l=>/^\s*(?:```|~~~|#{1,6} |>|[-*+] |\d+[.)] |---+$|\*\*\*+$)/.test(l);
 while(i<lines.length){const line=lines[i];if(!line.trim()){i++;continue}
 const fence=line.match(/^\s*(`{3,}|~{3,})(.*)$/);if(fence){const code=[];i++;while(i<lines.length&&!lines[i].trim().startsWith(fence[1]))code.push(lines[i++]);if(i<lines.length)i++;const pre=document.createElement('pre'),node=document.createElement('code');node.textContent=code.join('\n');pre.append(node);root.append(pre);continue}
 const heading=line.match(/^\s*(#{1,6})\s+(.+?)\s*#*$/);if(heading){const h=document.createElement('h'+heading[1].length);inlineMarkdown(h,heading[2]);root.append(h);i++;continue}
 if(/^\s*(?:---+|\*\*\*+)\s*$/.test(line)){root.append(document.createElement('hr'));i++;continue}
 if(/^\s*>/.test(line)){const quoted=[];while(i<lines.length&&/^\s*>/.test(lines[i]))quoted.push(lines[i++].replace(/^\s*> ?/,''));const q=document.createElement('blockquote');q.append(markdown(quoted.join('\n')));root.append(q);continue}
 const list=line.match(/^\s*([-*+]|\d+[.)])\s+(.+)$/);if(list){const ordered=/\d/.test(list[1]);const ul=document.createElement(ordered?'ol':'ul');if(ordered)ul.start=parseInt(list[1],10);while(i<lines.length){const item=lines[i].match(/^\s*([-*+]|\d+[.)])\s+(.+)$/);if(!item||/\d/.test(item[1])!==ordered)break;const li=document.createElement('li');inlineMarkdown(li,item[2]);ul.append(li);i++}root.append(ul);continue}
 if(line.includes('|')&&i+1<lines.length&&/^\s*\|?\s*:?-{3,}/.test(lines[i+1])){const table=document.createElement('table');const cells=s=>s.trim().replace(/^\||\|$/g,'').split('|');const add=(s,tag)=>{const row=document.createElement('tr');for(const c of cells(s)){const cell=document.createElement(tag);inlineMarkdown(cell,c.trim());row.append(cell)}table.append(row)};add(line,'th');i+=2;while(i<lines.length&&lines[i].includes('|'))add(lines[i++],'td');root.append(table);continue}
 const p=document.createElement('p'),paragraph=[line];i++;while(i<lines.length&&lines[i].trim()&&!special(lines[i]))paragraph.push(lines[i++]);inlineMarkdown(p,paragraph.join('\n'));root.append(p);
 }return root;
}
function searchTerms(query){
 const terms=[];let at=0;while(at<query.length){if(query[at]==='"'){const end=query.indexOf('"',at+1);if(end>=0){const text=query.slice(at+1,end).trim().replace(/\s+/g,' ');if(text)terms.push({text,quoted:true});at=end+1;continue}}
 let end=query.indexOf('"',query[at]==='"'?at+1:at);if(end<0)end=query.length;for(const text of query.slice(at,end).match(/[\p{L}\p{N}_]+/gu)||[])terms.push({text,quoted:false});at=end}return terms;
}
function highlightTerms(root,query){
 const terms=searchTerms(query);if(!terms.length)return;const escape=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');const word=/[\p{L}\p{N}_]/u;
 const patterns=terms.map(t=>t.quoted? (word.test(t.text[0])?'(?<![\\p{L}\\p{N}_])':'')+t.text.split(/\s+/).map(escape).join('\\s+')+(word.test(t.text.at(-1))?'(?![\\p{L}\\p{N}_])':''):escape(t.text)).sort((a,b)=>b.length-a.length);
 const pattern=new RegExp(patterns.join('|'),'giu');const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);const nodes=[];let text='',previousBlock=null;
 while(walker.nextNode()){const node=walker.currentNode;if(node.parentElement?.closest('mark'))continue;const block=node.parentElement?.closest('p,li,h1,h2,h3,h4,h5,h6,pre,td,th,section')||root;if(previousBlock&&block!==previousBlock)text+='\n';const start=text.length;text+=node.nodeValue;nodes.push({node,start,end:text.length});previousBlock=block}
 const ranges=[];let match;while((match=pattern.exec(text)))ranges.push([match.index,pattern.lastIndex]);
 for(const {node,start,end} of nodes){const hits=ranges.filter(([a,b])=>a<end&&b>start).map(([a,b])=>[Math.max(a,start)-start,Math.min(b,end)-start]);if(!hits.length)continue;const fragment=document.createDocumentFragment();let at=0;for(const [a,b] of hits){fragment.append(document.createTextNode(node.nodeValue.slice(at,a)));const mark=document.createElement('mark');mark.textContent=node.nodeValue.slice(a,b);fragment.append(mark);at=b}fragment.append(document.createTextNode(node.nodeValue.slice(at)));node.replaceWith(fragment)}
}
function exchangeMarkdown(text,query){
 const root=document.createElement('div');root.className='fulltext exchange';
 const sections=text.split(/^## (User prompt|Assistant response \d+)\s*$/m);
 if(sections.length===1)root.append(markdown(text));
 else{if(sections[0].trim())root.append(markdown(sections[0]));for(let i=1;i<sections.length;i+=2){const section=document.createElement('section');const prompt=sections[i]==='User prompt';section.className=prompt?'prompt-text':'response-text';section.setAttribute('aria-label',prompt?'User prompt':'Assistant response');section.append(markdown(sections[i+1]||''));root.append(section)}}
 highlightTerms(root,query);return root;
}
function journalDate(value){
 if(!value)return ['Undated',''];if(/^\d{4}-\d{2}-\d{2}$/.test(value))return [value,''];
 const d=new Date(value);if(Number.isNaN(d.getTime()))return [value,''];
 return [new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',month:'short',day:'numeric',year:'numeric'}).format(d),new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',hour:'numeric',minute:'2-digit',hour12:true}).format(d)];
}
