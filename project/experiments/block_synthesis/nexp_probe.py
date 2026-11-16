"""Turn the compiler's actual NExp loop into a native-RTL command transcript."""
import argparse
import hashlib
import json
from pathlib import Path
import random
from unittest.mock import patch

from streaming_ir import templates,primitive_body


def main():
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    with patch('streaming_ir.duration',return_value=1):library=templates({})
    node={'id':'probe','op':'NExp','inputs':['x'],'shape':[1],'attributes':{}}
    body,_=primitive_body(node)
    calls=[part['call'] for part in body['body']['sequence']]
    rng=random.Random(219)
    values=sorted(set([-32768,-16385,-16384,-16383,-1024,-1,0,1,32766,32767]+
        list(range(-32768,32768,127))+[rng.randrange(-32768,32768) for _ in range(128)]))
    def transcript(names):
        lines=[]
        for value in values:
            lines.append(f'{value} {len(names)}')
            for name in names:
                leaf=library[name];p=leaf['parameters'];source=leaf.get('operand_source')
                # Poison all upper lanes. Only the canonical low S32 and the
                # count=1 low S16 are available; implicit [x,0] is invalid.
                if source=='primitive_input_0.low_s16':raw=(0xa55a5aa5<<32)|(value&0xffffffff)
                elif source=='native_constant:0.low_s16':raw=0
                elif source is None:raw=0
                else:raise ValueError('unknown native operand '+source)
                lines.append(f"{p['op']} {p['count']} {raw}")
        return '\n'.join(lines)+'\n'
    files={'commands.txt':transcript(calls),
        'old-count-one.txt':transcript([name for name in calls if name!='n_soft_zero_stats'])}
    for name,data in files.items():(args.output/name).write_text(data,encoding='utf-8',newline='\n')
    manifest={'cases':len(values),'negative_values':sum(x<0 for x in values),'calls':calls,
        'semantics':'native exp(x-max(x,0)); explicit scalar Stats(x), Stats(0)',
        'qualification':'transcript derived from compiler; synthetic durations not used as timing evidence',
        'sha256':{name:hashlib.sha256((args.output/name).read_bytes()).hexdigest() for name in files}}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest))


if __name__=='__main__':main()
