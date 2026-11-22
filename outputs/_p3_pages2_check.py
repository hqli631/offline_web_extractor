import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from lxml import html
for f in ['whatwg-html.candidate.html','rfc.candidate.html','gnu.candidate.html','python_appetite_zh.html','mdn.candidate.html','github-copilot-blog.candidate.html','w3c-link-text.candidate.html']:
    p = Path('samples')/f
    if not p.exists(): print(f,'ABSENT'); continue
    raw = html.tostring(html.document_fromstring(p.read_bytes(), parser=html.HTMLParser(no_network=True)), encoding='unicode')
    print(f, len(raw), '<=20k' if len(raw)<=20000 else ('<=40k' if len(raw)<=40000 else '>40k'))
