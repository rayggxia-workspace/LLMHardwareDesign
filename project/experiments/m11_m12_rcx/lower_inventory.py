"""Index frozen native net names, actual metal probes and original SPEF values.

Reads existing snapshot geometry and original extraction; no P&R or field solve.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import re

KINDS = ('C0','F0','J0','P0','T0','U0')
SNAP = Path('/public/home/yuzelu/PingyangHuang/issue-222-native-W8lGG4Iy')
JOBS = dict(C0=100095,F0=100098,J0=100099,P0=100100,T0=100101,U0=100096)


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def clean(name): return re.sub(r'\\(.)',r'\1',name)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kind',default=KINDS[int(os.environ.get('LOWER_INDEX','0'))])
    p.add_argument('--snapshot',type=Path)
    p.add_argument('--out',type=Path,default=Path(os.environ.get('LOWER_OUT','.')))
    a=p.parse_args();a.out.mkdir()
    folder=a.snapshot if a.snapshot else SNAP/('job-'+str(JOBS[a.kind]))/'result'
    receipt=json.loads((folder/'snapshot.json').read_text())
    assert receipt['kind']==a.kind
    geom=folder/'conductors.tsv.gz';assert geom.stat().st_size==receipt['outputs'][geom.name]['bytes']
    names={};data={};current=None;header=False;gh=hashlib.sha256()
    with gzip.open(geom,'rb') as stream:
        for raw in stream:
            gh.update(raw);line=raw.decode().rstrip('\n')
            if line.startswith('# block-v1-odb-geometry/1 '):
                dbu=int(line.split('dbu_per_um=')[1]);header=True;continue
            if line.startswith('# NET '):
                _,_,token,encoded=line.split();name=bytes.fromhex(encoded).decode()
                assert token not in names and name not in data
                names[token]=name;current=dict(name=name,rectangles=0,highest_metal=0,probe=None)
                data[name]=current;continue
            if line.startswith('#') or not line:continue
            token,layer,role,*xy=line.split('\t');assert names[token]==current['name']
            current['rectangles']+=1
            if layer.startswith('metal'):
                level=int(layer[5:]);assert 1<=level<=10
                x0,y0,x1,y1=map(int,xy)
                if level>current['highest_metal']:
                    current['highest_metal']=level
                    current['probe']=[(x0+x1)/(2*dbu),(y0+y1)/(2*dbu)]
                    current['probe_layer']=layer
    assert header and gh.hexdigest()==receipt['geometry_uncompressed_sha256']
    # OpenDB stores escaped brackets in some internal names. SPEF also adds
    # its own escape layer. Compare decoded identifiers, retaining raw names;
    # refuse ambiguous canonicalization instead of silently joining nets.
    normalized={clean(name):name for name in data}
    assert len(normalized)==len(data),'Ambiguous decoded OpenDB net names'
    ports={}
    for line in (folder/'ports.tsv').read_text().splitlines():
        ph,nh,io,signal=line.split('\t');pin=bytes.fromhex(ph).decode();net=bytes.fromhex(nh).decode()
        ports[pin]=dict(net=net,io=io,signal=signal)
        assert net in data;data[net].setdefault('ports',[]).append(pin)
    spef=Path(receipt['source_hashes']['spef']['path'])
    assert spef.stat().st_size==receipt['source_hashes']['spef']['bytes']
    mapped={};mode=None;active=None;sh=hashlib.sha256();cap_unit=None;net_count=0
    missing=[];matched=set();runit=None
    with spef.open('rb') as stream:
        for raw in stream:
            sh.update(raw);s=raw.decode().strip()
            if s.startswith('*C_UNIT '):
                _,v,u=s.split();cap_unit=float(v)*{'PF':1000.,'FF':1.}[u]
            elif s.startswith('*R_UNIT '):
                _,v,u=s.split();runit=float(v)*{'OHM':1.,'KOHM':1000.}[u]
            elif s=='*NAME_MAP':mode='names'
            elif s.startswith('*D_NET '):
                _,token,value=s.split();name=mapped.get(token,clean(token));net_count+=1
                active=dict(original_declared_cap_ff=float(value)*cap_unit,original_ground_cap_ff=0.,original_cc_entries_ff=0.,original_resistance_sum_ohm=0.,original_resistance_edges=0)
                assert name not in matched;matched.add(name)
                candidates={r for r in [normalized.get(name),normalized.get(clean(name))] if r is not None}
                assert len(candidates)<=1,('Ambiguous SPEF escape decoding',name,candidates)
                resolved=next(iter(candidates)) if candidates else None
                if resolved is not None:
                    assert 'original' not in data[resolved],('Multiple SPEF nets map to one ODB net',name,resolved)
                    data[resolved].update(original_spef=True,original_spef_net=name);data[resolved]['original']=active
                else:missing.append(name)
                mode=None
            elif s=='*CAP':mode='cap'
            elif s=='*RES':mode='res'
            elif s.startswith('*') and mode=='names' and re.match(r'^\*\d+\s',s):
                token,name=s.split(maxsplit=1);mapped[token]=clean(name)
            elif s.startswith('*'):mode=None
            elif s and mode=='cap':
                v=s.split()
                assert len(v) in (3,4),s
                active['original_ground_cap_ff' if len(v)==3 else 'original_cc_entries_ff']+=float(v[-1])*cap_unit
            elif s and mode=='res':
                v=s.split();assert len(v)==4
                active['original_resistance_sum_ohm']+=float(v[-1])*runit;active['original_resistance_edges']+=1
    assert sh.hexdigest()==receipt['source_hashes']['spef']['sha256']
    totals=Counter(str(v['highest_metal']) for v in data.values())
    target=a.out/'net-inventory.jsonl.gz'
    with gzip.open(target,'wt',encoding='utf-8') as f:
        for v in data.values():f.write(json.dumps(v,separators=(',',':'))+'\n')
    (a.out/'ports.json').write_text(json.dumps(ports,indent=2)+'\n')
    result=dict(kind=a.kind,source_snapshot=str(folder/'snapshot.json'),source_snapshot_sha256=sha(folder/'snapshot.json'),
        source_geometry=str(geom),source_geometry_uncompressed_sha256=gh.hexdigest(),source_spef=str(spef),source_spef_sha256=sh.hexdigest(),
        native_net_count=len(data),original_spef_nets=net_count,geometry_nets_with_spef=sum('original' in v for v in data.values()),
        missing_spef_geometry_names=missing[:25],missing_spef_geometry_count=len(missing),highest_metal_counts=dict(totals),
        ports=len(ports),inventory_sha256=sha(target),inventory_bytes=target.stat().st_size,
        capacitance_unit_ff=cap_unit,resistance_unit_ohm=runit,
        scope='Original ODB-routed net inventory; nested macro internal nets remain in their accepted child databases. Not a field extraction or proof that low-layer nets are unaffected.')
    (a.out/'inventory.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
