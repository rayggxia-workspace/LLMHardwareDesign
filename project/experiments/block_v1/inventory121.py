"""Independently traverse generic/mapped hierarchy and price every physical cell."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def number(value):return int(value,2) if isinstance(value,str) else int(value)
def need(ok,message):
    if not ok:raise ValueError(message)


def audit(generic,mapped,library,out):
    gm=json.loads(generic.read_text())['modules']
    mm=json.loads(mapped.read_text())['modules']
    areas={}
    cell=None
    for line in library.read_text().splitlines():
        match=re.match(r'\s*cell\s*\(\s*"?([^"\s)]+)"?\s*\)',line)
        if match:cell=match.group(1)
        match=re.match(r'\s*area\s*:\s*([^;]+);',line)
        if match and cell:areas[cell]=Decimal(match.group(1))
    need(len(areas)>100,'actual complete Liberty parsed')
    memories=[];multipliers=[];types=Counter();annotations=0;register_bits=0
    def generic_walk(name,path,stack):
        nonlocal register_bits
        need(name not in stack,'recursive generic hierarchy')
        for instance,c in gm[name]['cells'].items():
            t=c['type'];p=c['parameters'];where=path+'/'+instance
            if t in gm:
                need(not number(gm[t].get('attributes',{}).get('blackbox',0)),'no generic black boxes')
                generic_walk(t,where,stack+[name]);continue
            types[t]+=1
            need(t not in ('$div','$mod','$divfloor','$modfloor','$pow'),'no hidden combinational divider')
            if 'dff' in t.lower():register_bits+=number(p['WIDTH'])
            if t=='$mem_v2':
                memories.append(dict(instance=where,**{k:number(p[k])for k in ('WIDTH','SIZE','RD_PORTS','WR_PORTS')}))
            if t=='$mul':
                dynamic=all(any(isinstance(bit,int)for bit in c['connections'][port])for port in ('A','B'))
                multipliers.append(dict(instance=where,dynamic=dynamic,**{k:number(p[k])for k in ('A_WIDTH','B_WIDTH','Y_WIDTH','A_SIGNED','B_SIGNED')}))
    generic_walk('shared121','shared121',[])
    need(Counter((m['WIDTH'],m['SIZE'],m['RD_PORTS'],m['WR_PORTS'])for m in memories)==Counter({(128,1024,1,1):1,(128,384,1,1):1}),'one true S16K plus one true T6K')
    dynamic=Counter((m['A_WIDTH'],m['B_WIDTH'])for m in multipliers if m['dynamic'])
    need(dynamic==Counter({(8,8):8,(32,32):1}),'exact 8 S8 lanes and one shared S32 multiplier')
    def mapped_walk(name,stack):
        nonlocal annotations
        need(name not in stack,'recursive mapped hierarchy')
        cells=Counter()
        for c in mm[name]['cells'].values():
            t=c['type']
            if t=='$scopeinfo':annotations+=1;continue
            if t in areas:
                cells[t]+=1
            elif t in mm:
                need(not number(mm[t].get('attributes',{}).get('blackbox',0)),'unpriced mapped blackbox '+t)
                cells.update(mapped_walk(t,stack+[name]))
            else:raise ValueError('unmapped or unknown hardware '+t)
        return cells
    physical=mapped_walk('shared121',[])
    cost=sum((areas[t]*count for t,count in physical.items()),Decimal(0))
    subcost={name:str(sum((areas[t]*n for t,n in mapped_walk(name,[]).items()),Decimal(0)))
             for name in mm if name not in areas and not number(mm[name].get('attributes',{}).get('blackbox',0))}
    report=dict(schema='block-v1-inventory/1',generic_sha256=sha(generic),mapped_sha256=sha(mapped),library_sha256=sha(library),
                top='shared121',memories=memories,memory_bits=sum(m['WIDTH']*m['SIZE']for m in memories),
                generic_register_bits_excluding_memories=register_bits,generic_types=dict(types),multipliers=multipliers,
                physical_cells=dict(physical),physical_cell_count=sum(physical.values()),area_um2=str(cost),
                module_instance_area_um2=subcost,ignored_scope_annotations=annotations,
                qualification='Full stdcell mapped cost including both real stores; no PPA/STA qualification')
    out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(area_um2=str(cost),physical_cell_count=sum(physical.values()),memories=memories,dynamic_multipliers=dict((str(k),v)for k,v in dynamic.items()))))


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__)
    for key in ['generic','mapped','library','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();audit(a.generic,a.mapped,a.library,a.out)
