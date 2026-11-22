import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from lxml import html
for f in ['code_lab.html','list_lab.html','news.html','python_blurb.html','iana_example_domains.html']:
    p = Path('samples')/f
    if not p.exists(): print(f, 'ABSENT'); continue
    raw = html.tostring(html.document_fromstring(p.read_bytes(), parser=html.HTMLParser(no_network=True)), encoding='unicode')
    print(f, 'raw_chars=', len(raw), 'untruncated@20k=', len(raw)<=20000)
for d in ['drift_lab']:
    for p in sorted((Path('samples')/d).glob('*.html')):
        raw = html.tostring(html.document_fromstring(p.read_bytes(), parser=html.HTMLParser(no_network=True)), encoding='unicode')
        print(d+'/'+p.name, 'raw_chars=', len(raw), 'untruncated@20k=', len(raw)<=20000)
