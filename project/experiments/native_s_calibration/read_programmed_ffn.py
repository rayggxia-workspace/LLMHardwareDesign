"""Import programmed three-P whole-FFN phases with actual MC/DMA receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile

from read_three_p_ffn import digest, fields


JOBS=((102604,0),(102603,1))
SOURCE='ab7611d43e4c007cc966ab5e61903118d33fcb4a'


def read(index, cache):
    profiles=[]
    for job,early in JOBS:
        run,=(r for r in index['runs'] if r['job']==job)
        assert run['state']=='COMPLETED' and run['accounting'].split('|')[1:3]==['COMPLETED','0:0']
        assert run['source_commit']==SOURCE
        archive=cache/f'{job}-receipts.tar.gz'
        assert digest(archive)==run['receipts_sha256']
        trials={}
        with tarfile.open(archive,mode='r:gz') as stream:
            manifest=json.load(stream.extractfile('receipts-manifest.json'))
            for member in stream:
                match=re.fullmatch(r'seed-(\d+)/mode-([01])-initial-([012])\.log',member.name)
                if not match:
                    continue
                key=tuple(map(int,match.groups()))
                raw=stream.extractfile(member).read()
                assert hashlib.sha256(raw).hexdigest()==manifest[member.name]
                log=raw.decode()
                assert '%Fatal' not in log and '%Error' not in log
                values=[]
                for label in ('FFN_PROFILE','DOWN_PROFILE','DMA_PROFILE','PROGRAM_PROFILE','PASS ffn_three_p_native'):
                    line,=re.findall(r'^'+label+r' (.*)$',log,re.M)
                    values.append(fields(line))
                gate,down,dma,program,check=values
                assert gate['W64']==748544 and gate['S_copy']==44544 and gate['S_scatter']==5504
                assert down['W64']==374272 and down['S_copy_words']==24768 and down['Mid_replays']==516 and down['result_words']==512
                assert check==dict(columns=11008,stripes=58,real_P_M=3,real_S_banks=16,Mid=86,mode=key[1],
                                  down=1,four_w=1,shared_dma=1,program=1,split_up=0,early_exec=early)
                assert program==dict(calls=192,confirmed_reads=71_884_800,confirmed_writes=96_256)
                assert dma==dict(backend_requests=1_123_200,backend_returns=1_123_200,purges=1)
                assert program['confirmed_reads']==dma['backend_requests']*64
                assert key not in trials
                trials[key]=dict(seed=key[0],mode=key[1],initial=key[2],gate=gate['cycles'],down=down['cycles'])
        assert set(trials)=={(seed,mode,init) for seed in range(25001,25007) for mode in (0,1) for init in (0,1,2)}
        rows=[trials[k] for k in sorted(trials)]
        profiles.append(dict(job=job,early_exec=bool(early),receipt_sha256=run['receipts_sha256'],
                            source_sha256=run['source_sha256'],source_commit=SOURCE,program=program,dma=dma,trials=rows))
    for profile,first in zip(profiles,((590628,269574),(586103,263811)),strict=True):
        assert (profile['trials'][0]['gate'],profile['trials'][0]['down'])==first
    assert all(b['gate']+b['down']<a['gate']+a['down'] for a,b in zip(*(p['trials'] for p in profiles),strict=True))
    return dict(schema='programmed-three-P-native-FFN/1',profiles=profiles,
        boundary='Synthetic inputs and weights, exact Qwen FFN dimensions. Actual MC/LC and dual-channel DMA to finite RTL DDR peer. Weights and descriptor reads confirmed. Confirmed output bytes are local terminal counters, not backend DDR writes. Source X already committed in U.S. No unrelated descriptors or DMA, post-phase diagnostic readback, architectural output export or whole-program terminal costs.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--index',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.write_text(json.dumps(read(json.loads(args.index.read_text()),args.cache),indent=2)+'\n',encoding='utf-8',newline='\n')
