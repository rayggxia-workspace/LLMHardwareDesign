"""Resumable parallel HTTP byte ranges, strict range/size checks and final SHA."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import time
import requests


def download(url, dest, size, expected=None, workers=4):
    dest=Path(dest)
    parts=dest.parent/(dest.name+'.parts')
    parts.mkdir(parents=True,exist_ok=True)
    block=16<<20
    def fetch(i):
        start=i*block; end=min(size,start+block)-1
        path=parts/f'{i:05d}'
        if path.exists() and path.stat().st_size==end-start+1:
            return
        for attempt in range(8):
            try:
                # CDN signed resolve URLs may cache by request; unique query fixes range identity.
                sep='&' if '?' in url else '?'
                u=url+sep+f'range_start={start}'
                with requests.get(u,headers={'Range':f'bytes={start}-{end}'},stream=True,timeout=(30,90)) as r:
                    r.raise_for_status()
                    assert r.status_code==206,(r.status_code,r.headers)
                    assert r.headers.get('Content-Range')==f'bytes {start}-{end}/{size}',r.headers
                    temp=path.with_suffix('.partial')
                    with temp.open('wb') as f:
                        for b in r.iter_content(1<<20):
                            f.write(b)
                    assert temp.stat().st_size==end-start+1
                    temp.replace(path)
                print(f'range {i} done {end+1}/{size}',flush=True)
                return
            except Exception as e:
                print(f'range {i} attempt {attempt}: {e!r}',flush=True)
                if attempt==7: raise
                time.sleep(min(attempt+1,5))
    count=(size+block-1)//block
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(fetch,range(count)))
    temp=dest.with_suffix(dest.suffix+'.assembled')
    h=hashlib.sha256()
    with temp.open('wb') as out:
        for i in range(count):
            with (parts/f'{i:05d}').open('rb') as f:
                for b in iter(lambda:f.read(8<<20),b''):
                    out.write(b);h.update(b)
    assert temp.stat().st_size==size
    assert not expected or h.hexdigest()==expected,(h.hexdigest(),expected)
    temp.replace(dest)
    print('verified',dest,h.hexdigest(),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--url',required=True);p.add_argument('--dest',required=True)
    p.add_argument('--size',type=int,required=True);p.add_argument('--sha256')
    p.add_argument('--workers',type=int,default=4)
    a=p.parse_args();download(a.url,a.dest,a.size,a.sha256,a.workers)
