"""Fixed official Qwen ModelScope commit; all local files verified with publisher SHA256."""
import argparse
import json
from pathlib import Path
import requests
from prepare import sha
from ranged import download


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--model',required=True);p.add_argument('--revision',required=True)
    a=p.parse_args();a.root.mkdir(parents=True,exist_ok=True)
    meta_path=a.root/'official-metadata.json'
    if not meta_path.exists():
        r=requests.get(f'https://modelscope.cn/api/v1/models/{a.model}/repo/files',
            params={'Recursive':'true','Revision':a.revision},timeout=30)
        r.raise_for_status();meta=r.json();assert meta['Code']==200
        meta_path.write_text(json.dumps(meta,indent=2),encoding='utf-8')
    meta=json.loads(meta_path.read_text())
    files={}
    names={'config.json','generation_config.json','tokenizer.json','tokenizer_config.json',
           'merges.txt','vocab.json','LICENSE','README.md','model.safetensors.index.json'}
    for item in meta['Data']['Files']:
        name=item['Name']
        if item['Type']!='blob' or (name not in names and not name.endswith('.safetensors')): continue
        dest=a.root/name
        url=f'https://modelscope.cn/models/{a.model}/resolve/{a.revision}/{name}'
        if not dest.exists():
            if item['Size']>64<<20:
                download(url,dest,item['Size'],item['Sha256'],4)
            else:
                r=requests.get(url,timeout=90);r.raise_for_status()
                part=dest.with_suffix(dest.suffix+'.partial');part.write_bytes(r.content)
                assert part.stat().st_size==item['Size'] and sha(part)==item['Sha256'],name
                part.rename(dest)
        assert dest.stat().st_size==item['Size'] and sha(dest)==item['Sha256'],name
        files[name]={'bytes':item['Size'],'sha256':item['Sha256'],'publisher_file_commit':item['Revision']}
        print(name,files[name],flush=True)
        (a.root/'model-manifest.json').write_text(json.dumps({'model':a.model,'revision':a.revision,
            'publisher':'https://modelscope.cn/'+a.model,'root':str(a.root.resolve()),'files':files,'complete':False},indent=2))
    assert any(n.endswith('.safetensors') for n in files)
    (a.root/'model-manifest.json').write_text(json.dumps({'model':a.model,'revision':a.revision,
        'publisher':'https://modelscope.cn/'+a.model,'root':str(a.root.resolve()),'files':files,'complete':True},indent=2))


if __name__=='__main__': main()
