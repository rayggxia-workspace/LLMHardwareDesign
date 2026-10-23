"""Resumable, fixed-revision public Phi files. No tokens/remote code execution."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
import urllib.error


def hashes(path):
    size=Path(path).stat().st_size;h=hashlib.sha256();g=hashlib.sha1(('blob '+str(size)+'\0').encode())
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b);g.update(b)
    return {'bytes':size,'sha256':h.hexdigest(),'git_blob':g.hexdigest()}


def main():
    p=argparse.ArgumentParser();p.add_argument('--metadata',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--config-only',action='store_true');a=p.parse_args()
    meta=json.loads(a.metadata.read_text());revision='cfbefacb99257ffa30c83adab238a50856ac3083'
    if meta['id']!='microsoft/Phi-4-mini-instruct' or meta['sha']!=revision or meta.get('gated'):raise ValueError('not frozen public Phi')
    allowed=['LICENSE','NOTICE.md','README.md','config.json','generation_config.json','tokenizer.json','tokenizer_config.json',
             'special_tokens_map.json','added_tokens.json','vocab.json','merges.txt','model.safetensors.index.json',
             'configuration_phi3.py','modeling_phi3.py']
    if not a.config_only:allowed+=['model-00001-of-00002.safetensors','model-00002-of-00002.safetensors']
    known={r['rfilename']:r for r in meta['siblings']};a.out.mkdir(parents=True,exist_ok=True)
    def one(name):
        record=known[name];dest=a.out/name;expected=record.get('lfs',{}).get('sha256')
        def verify():
            got=hashes(dest)
            if got['bytes']!=record['size'] or (got['sha256']!=expected if expected else got['git_blob']!=record['blobId']):raise ValueError('download hash '+name)
            return got
        if dest.exists():return name,{**verify(),'reused':True}
        partial=dest.with_suffix(dest.suffix+'.part');failures=[];start=time.time()
        for attempt in range(3):
            offset=partial.stat().st_size if partial.exists() else 0
            url='https://huggingface.co/microsoft/Phi-4-mini-instruct/resolve/'+revision+'/'+name+'?download=true'
            headers={'User-Agent':'LLMHardwareDesign-issue61-public-fixed-revision'}
            if offset:headers['Range']='bytes='+str(offset)+'-'
            try:
                with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=45) as response:
                    if offset and response.status!=206:offset=0
                    with partial.open('ab' if offset else 'wb') as f:
                        while True:
                            block=response.read(8<<20)
                            if not block:break
                            f.write(block)
                if partial.stat().st_size!=record['size']:raise ValueError('truncated '+name)
                # Validate before publishing the final filename.
                got=hashes(partial)
                if (got['sha256']!=expected if expected else got['git_blob']!=record['blobId']):raise ValueError('SHA '+name)
                partial.rename(dest)
                return name,{**verify(),'seconds':time.time()-start,'failures':failures,'source_url':url}
            except Exception as exc:
                failures.append({'attempt':attempt+1,'type':type(exc).__name__,'error':str(exc)})
                print(json.dumps({'file':name,'attempt_failed':failures[-1]}),flush=True)
        raise RuntimeError(json.dumps({'file':name,'failures':failures}))
    small=[n for n in allowed if not n.endswith('.safetensors')];weights=[n for n in allowed if n.endswith('.safetensors')]
    receipts={}
    for name in small:
        key,value=one(name);receipts[key]=value
        print(json.dumps({'file':key,'bytes':value['bytes'],'verified':True}),flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        for key,value in pool.map(one,weights):
            receipts[key]=value;print(json.dumps({'file':key,'bytes':value['bytes'],'verified':True}),flush=True)
    result={'model':meta['id'],'revision':revision,'metadata_sha256':hashlib.sha256(a.metadata.read_bytes()).hexdigest(),
            'files':receipts,'status':'PASS','scope':'download/source hashes only, no inference or integer verification'}
    (a.out/'download-receipt.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')


if __name__=='__main__':main()
