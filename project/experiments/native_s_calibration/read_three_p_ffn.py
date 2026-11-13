"""Freeze timing and true traffic from the paired three-P native FFN logs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile


def digest(path):
    with path.open('rb') as data:
        return hashlib.file_digest(data,'sha256').hexdigest()


def fields(line):
    return {key:int(value) for key,value in (word.split('=',1) for word in line.split())}


def read(root,cache):
    index=json.loads((root/'index.json').read_text())
    profiles=[]
    for job,four in ((102563,0),(102564,1)):
        run,=(r for r in index['runs'] if r['job']==job)
        assert run['state']=='COMPLETED' and run['accounting'].split('|')[1:3]==['COMPLETED','0:0']
        assert run['source_commit']=='3a808380199605662307fe88d4330ba8c056728f'
        archive=cache/f'{job}-receipts.tar.gz'
        assert digest(archive)==run['receipts_sha256']
        received={}
        checked={}
        with tarfile.open(archive,mode='r|gz') as stream:
            for item in stream:
                if item.name=='receipts-manifest.json':
                    manifest=json.load(stream.extractfile(item))
                    continue
                match=re.fullmatch(r'seed-(\d+)/mode-([01])-initial-([012])\.log',item.name)
                if not match:
                    continue
                key=tuple(map(int,match.groups()))
                log=stream.extractfile(item).read()
                checked[item.name]=hashlib.sha256(log).hexdigest()
                text=log.decode()
                assert '%Fatal' not in text and '%Error' not in text
                profiles_by_label={}
                for label in ('FFN_PROFILE','DOWN_PROFILE','DMA_PROFILE','PASS ffn_three_p_native'):
                    line,=re.findall(r'^'+label+r' (.*)$',text,re.M)
                    profiles_by_label[label]=fields(line)
                gate,down,dma,check=profiles_by_label.values()
                assert gate['W64']==748544 and gate['S_copy']==44544 and gate['S_scatter']==5504
                assert down['W64']==374272 and down['S_copy_words']==24768 and down['Mid_replays']==516 and down['result_words']==512
                assert dma['backend_requests']==dma['backend_returns']==gate['W64']+down['W64'] and dma['purges']==1
                assert check==dict(columns=11008,stripes=58,real_P_M=3,real_S_banks=16,Mid=86,
                                  mode=key[1],down=1,four_w=four,shared_dma=1)
                assert key not in received
                received[key]=dict(seed=key[0],mode=key[1],initial=key[2],gate=gate['cycles'],down=down['cycles'])
        assert all(manifest[name]==sha for name,sha in checked.items())
        assert set(received)=={(s,m,i) for s in range(25001,25007) for m in range(2) for i in range(3)}
        rows=[received[k] for k in sorted(received)]
        profiles.append(dict(job=job,four_W=bool(four),receipt_sha256=run['receipts_sha256'],
                             source_sha256=run['source_sha256'],source_commit=run['source_commit'],trials=rows))
    assert profiles[0]['source_sha256']==profiles[1]['source_sha256']
    for profile,first in zip(profiles,[(1040034,503285),(590359,268319)],strict=True):
        assert (profile['trials'][0]['gate'],profile['trials'][0]['down'])==first
    return dict(schema='paired-three-P-native-FFN/1',workload=dict(K=2048,Mid=11008,Down=2048,columns_per_scope=192,
                gate_stripes=58,Down_stripes=6,gate_W64=748544,Down_W64=374272,Mid_tiles=86),profiles=profiles,
                boundary='True local Gate/Up→Mid→Down and actual typed dual-channel DMA with a finite DDR peer. Synthetic input/weights, source already committed in U.S, excludes diagnostic Mid/result rereads and architectural output export. No competing descriptor or unrelated workload. Each profile is a whole measured phase.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--ffn-index-dir',required=True,type=Path)
    p.add_argument('--receipt-cache',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(read(a.ffn_index_dir,a.receipt_cache),indent=2)+'\n',encoding='utf-8')
