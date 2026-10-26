"""Extract the requested report without printing embedded base64. Python 3.10+."""
from pathlib import Path
from html.parser import HTMLParser
import argparse, base64, hashlib, json, re
from urllib.parse import unquote_to_bytes

class Extractor(HTMLParser):
    def __init__(self, out):
        super().__init__(); self.out=out; self.text=[]; self.skip=0; self.images=[]
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if tag in ('script','style'): self.skip+=1
        if tag=='a' and d.get('href','').startswith('data:'):
            h,b=d['href'].split(',',1); name=Path(d.get('download','download')).name
            raw=base64.b64decode(b) if ';base64' in h else unquote_to_bytes(b)
            (self.out/name).write_bytes(raw)
        if tag=='img' and d.get('src','').startswith('data:image/png;base64,'):
            idx=len(self.images); alt=d.get('alt',''); self.images.append({'index':idx,'alt':alt})
            if idx in (0,1,6,7,9,10):
                (self.out/f'source_image_{idx}.png').write_bytes(base64.b64decode(d['src'].split(',',1)[1]))
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.skip-=1
    def handle_data(self, text):
        if not self.skip and text.strip(): self.text.append(text.strip())

def extract(source, out):
    source=Path(source); out=Path(out); out.mkdir(parents=True,exist_ok=True)
    raw=source.read_bytes(); s=raw.decode('utf-8'); p=Extractor(out); p.feed(s)
    (out/'source_text.txt').write_text('\n'.join(p.text),encoding='utf-8')
    body=re.search(r'<script\b[^>]*id="pin-data"[^>]*>(.*?)</script>',s,re.S).group(1)
    (out/'source_pin_data.json').write_text(json.dumps(json.loads(body),ensure_ascii=False,indent=2),encoding='utf-8')
    receipt={'source':str(source.resolve()),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'images':p.images}
    (out/'extraction_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    return receipt

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('source');a.add_argument('--out',default=str(Path(__file__).parent));args=a.parse_args()
    r=extract(args.source,args.out);print(json.dumps({k:r[k] for k in ('sha256','bytes')}))
