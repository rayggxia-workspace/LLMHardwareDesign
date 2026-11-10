"""Task-owned, Slurm-only public W8 artifact acquisition and closure experiments."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import urllib.request

MODEL='Qwen/Qwen2.5-3B-Instruct-GPTQ-Int8'
REVISION='1fed15cb34975bc0bd699e62b95a539bb06eed42'
FILES=('config.json','generation_config.json','tokenizer.json','tokenizer_config.json',
       'merges.txt','vocab.json','model.safetensors','LICENSE')


def download(url,target):
    h=hashlib.sha256();n=0
    with urllib.request.urlopen(url,timeout=120) as response,target.open('xb') as out:
        while True:
            b=response.read(4<<20)
            if not b:break
            out.write(b);h.update(b);n+=len(b)
    return dict(bytes=n,sha256=h.hexdigest(),url=url)


def fetch(root):
    out=root/'quality';out.mkdir(exist_ok=False)
    model=root/'official-model';model.mkdir(exist_ok=False)
    report=dict(passed=False,source_commit=(root/'source-commit.txt').read_text().strip(),
                job=os.environ.get('SLURM_JOB_ID'),acquisition_only=True,
                model=MODEL,revision=REVISION,files={})
    def save():(out/'closure-fetch.json').write_text(json.dumps(report,indent=2)+'\n')
    try:
        for name in FILES:
            report['files'][name]=download(f'https://huggingface.co/{MODEL}/resolve/{REVISION}/{name}',model/name)
            print('FETCHED '+name+' '+str(report['files'][name]['bytes']),flush=True);save()
        config=json.loads((model/'config.json').read_text())
        assert config['quantization_config']['bits']==8 and config['quantization_config']['group_size']==128
        report['config']=config
        with (model/'model.safetensors').open('rb') as f:
            size=struct.unpack('<Q',f.read(8))[0];header=json.loads(f.read(size))
        report['tensor_header']=header
        data_url='https://datasets-server.huggingface.co/rows?dataset=Salesforce%2Fwikitext&config=wikitext-2-raw-v1&split=test&offset=0&length=100'
        report['dataset_rows']=download(data_url,root/'wikitext-test-rows.json')
        report['passed']=True
    finally:save()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--fetch-local',action='store_true')
    a=p.parse_args()
    if not a.fetch_local:assert os.environ.get('SLURM_JOB_ID')
    fetch(a.root) # Only network/file I/O, no model execution or EDA.
