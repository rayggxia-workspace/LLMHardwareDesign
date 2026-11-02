from pathlib import Path
import json,re,sys
from collections import defaultdict
def load_graph(root):
    cells=[];names={};drivers={};loads=defaultdict(list);netnames={};ids={};ports={}
    with (root/'mapped.json').open(encoding='utf-8')as f:
        for line in f:
            if line.startswith('    "block_v1_r": {'):break
        else:raise AssertionError('top not found')
        section=None
        for line in f:
            m=re.match(r'      "(ports|cells|netnames)": \{',line)
            if m:section=m[1];continue
            if line.startswith('    }'):break
            if section not in ('ports','cells','netnames'):continue
            if not line.startswith('        "'):continue
            # Each record is indented eight spaces and ends with eight-space }.
            keypart=line.split(': {',1)[0].strip();key=json.loads(keypart)
            record=[line]
            for line in f:
                record.append(line)
                if line.startswith('        }'):break
            obj=json.loads('{'+''.join(record).strip().rstrip(',')+'}')[key]
            if section=='cells':
                i=len(cells);typ=sys.intern(obj['type']);pins={}
                for pin,bits in obj['connections'].items():
                    assert len(bits)==1,(key,pin,bits)
                    n=bits[0];pins[sys.intern(pin)]=n
                    if obj['port_directions'][pin]=='output':assert n not in drivers;drivers[n]=(i,pin)
                    else:loads[n].append((i,pin))
                cells.append((typ,key,pins));names[key]=i
            else:
                for j,n in enumerate(obj['bits']):
                    off=obj.get('offset',0);label=key+(f' [{j+off}]'if len(obj['bits'])>1 else'')
                    priority=2 if key.startswith('$')else 0
                    if n not in netnames or priority<netnames[n][0]:netnames[n]=(priority,label)
                ids[key]=obj['bits'][0]if len(obj['bits'])==1 else obj['bits']
                if section=='ports':ports[key]=obj
    for cell in cells:
        for n in cell[2].values():
            if n not in netnames:netnames[n]=(9,str(n))
    return cells,names,drivers,loads,{n:s for n,(p,s)in netnames.items()},ids,ports
if __name__=='__main__':
    g=load_graph(Path(__file__).resolve().parent)
    print(len(g[0]),len(g[4]),g[5]['bank_role']);print(g[0][0])
