"""Allowlisted clean packaging. Refuses user data, caches and unapproved files."""
import hashlib,json,re,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ALLOW=[
 'LivingJournal.desktop','launch.sh','VERSION','LICENSE','README.md','.gitignore','RELEASE_NOTES.md','THIRD_PARTY.md',
 'data/README.md','docs/QUICK_START.md','docs/IMPORT_CHATS.md','docs/AGENT_WORKFLOW.md','docs/PORTABILITY.md',
 'app/server.py','app/store.py','app/launcher.py','app/importer.py','app/ui.py','app/search_query.py',
 'app/static/index.html','app/static/style.css','app/static/main.js','app/static/markdown.js',
 'tests/test_store.py','tests/smoke.py','tests/browser.cjs','tools/build_release.py'
]
def main():
    (ROOT.parent/'reports').mkdir(exist_ok=True)
    actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts}
    allowed=set(ALLOW)|{'MANIFEST.json'}
    unknown=sorted(actual-allowed)
    missing=sorted(set(ALLOW)-actual)
    if unknown or missing:raise SystemExit('Package allowlist failed: unexpected='+str(unknown)+' missing='+str(missing))
    if any(p.is_symlink() for p in ROOT.rglob('*') if '.git' not in p.relative_to(ROOT).parts):raise SystemExit('Symlinks are not allowed in a public package')
    license_text=(ROOT/'LICENSE').read_text()
    if 'Copyright (c) 2026 Pebblab' not in license_text or 'OWNER MUST COMPLETE' in license_text:
        raise SystemExit('Complete the owner-approved MIT license before publication')
    patterns={
      'home directory':r'/home/[A-Za-z0-9_.-]+/',
      'personal desktop path':r'/Users/[A-Za-z0-9_.-]+/',
      'conversation URL':r'https?://(?:chatgpt\.com|chat\.openai\.com)/[^\s]*\b(?:c|share)/',
      'private key':r'-----BEGIN (?:OPENSSH|RSA|EC|DSA|PRIVATE).*?KEY-----',
      'credential URL':r'https?://[^\s/:]+:[^\s/@]+@',
      'provider secret':r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b',
      'assigned secret':r'(?i)\b(?:password|api_key|access_token)\s*=\s*[\"\'][^\"\']{8,}[\"\']'
    }
    findings=[]
    for rel in ALLOW:
        text=(ROOT/rel).read_text(encoding='utf-8')
        for label,pattern in patterns.items():
            if re.search(pattern,text):findings.append(dict(file=rel,rule=label))
    if findings:raise SystemExit('Privacy audit blocked: '+str(findings))
    source={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in ALLOW}
    (ROOT/'MANIFEST.json').write_text(json.dumps(dict(version='1.0.0',files=source,self_hash='External release manifest hashes this file too.'),indent=2)+'\n')
    final={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in sorted(allowed)}
    output=ROOT.parent/'LivingJournal-1.0.0.tar.gz'
    with tarfile.open(output,'w:gz',format=tarfile.PAX_FORMAT) as archive:
        for rel in sorted(final):
            path=ROOT/rel;info=archive.gettarinfo(str(path),arcname='LivingJournal/'+rel)
            info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
            info.mode=0o755 if rel in ['launch.sh','LivingJournal.desktop'] else 0o644
            with path.open('rb') as f:archive.addfile(info,f)
    result=dict(version='1.0.0',files=final,archive_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),archive_bytes=output.stat().st_size)
    (ROOT.parent/'LivingJournal-1.0.0.manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    audit=dict(allowlisted_files=len(final),unexpected_files=[],privacy_findings=findings,user_data_files=0,symlinks=0,git_history=False,license_blocker=None,copyright_holder='Pebblab')
    (ROOT.parent/'reports/privacy-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(dict(package=str(output),bytes=result['archive_bytes'],files=len(final),privacy=audit),indent=2))
if __name__=='__main__':main()
