"""Recover actual boundary drivers and original Liberty load limits."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def body(text,start):
    depth=1;i=start;quoted=False
    while depth:
        c=text[i]
        if c=='\\':i+=2;continue
        if c=='"':quoted=not quoted
        if not quoted:
            depth+=(c=='{')-(c=='}')
        i+=1
    return text[start:i-1]


def limits(path):
    text=path.read_text()
    unit=re.search(r'capacitive_load_unit\s*\(\s*([\d.eE+-]+)\s*,\s*([a-zA-Z]+)\s*\)',text)
    assert unit, str(path)
    factor=float(unit[1])*{'ff':1.,'pf':1000.}[unit[2].lower()]
    default=re.search(r'default_max_capacitance\s*:\s*([\d.eE+-]+)',text)
    result={}
    for cell in re.finditer(r'\bcell\s*\(\s*"?([^"\s)]+)"?\s*\)\s*\{',text):
        contents=body(text,cell.end())
        pins={}
        for pin in re.finditer(r'\bpin\s*\(\s*"?([^"\s)]+)"?\s*\)\s*\{',contents):
            value=body(contents,pin.end())
            direction=re.search(r'\bdirection\s*:\s*(\w+)',value)
            if not direction or direction[1]!='output':continue
            cap=re.search(r'\bmax_capacitance\s*:\s*([\d.eE+-]+)',value)
            pins[pin[1]]=float(cap[1])*factor if cap else (float(default[1])*factor if default else None)
        result[cell[1]]=pins
    return result


def main():
    root=Path('/public/home/yuzelu/PingyangHuang')
    receipt=json.loads((root/'issue-215-top-pex-zOz2uxIr/route-206.json').read_text())
    binding=json.loads(Path(receipt['artifacts']['case-binding.json']['path']).read_text())['endpoints']
    out=Path(os.environ['COUPLING_OUT'])/'result';out.mkdir()
    kinds=['C0','F0','J0','P0','T0','U0']
    libraries={Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')}
    tables={};sources={}
    for kind in kinds:
        gds=Path(receipt['native_masks'][kind]['path']);db=gds.with_suffix('.odb')
        config=gds.parents[5]/'config.mk'
        if '/flow/results/' in str(gds) and config.exists():
            for line in config.read_text().splitlines():
                if line.startswith('export ADDITIONAL_LIBS ='):libraries.update(map(Path,line.split('=',1)[1].split()))
        libraries.update(gds.parent.glob('*.lib'))
        destination=out/(kind+'.tsv')
        env=dict(os.environ,COUPLING_DRIVER_ODB=str(db),COUPLING_DRIVER_TSV=str(destination))
        with (out/(kind+'.log')).open('xb') as log:
            subprocess.run(['openroad','-no_init','-exit',str(Path(__file__).with_suffix('.tcl'))],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        ports={}
        for line in destination.read_text().splitlines():
            encoded,master,pin,typ,inst=line.split('\t')
            name=bytes.fromhex(encoded).decode()
            ports.setdefault(name,[]).append(dict(master=master,pin=bytes.fromhex(pin).decode(),master_type=typ,instance=bytes.fromhex(inst).decode()))
        tables[kind[0]]=ports
    lookup={}
    for path in sorted(libraries):
        assert path.is_file(),str(path)
        parsed=limits(path)
        for name,pins in parsed.items():
            if name in lookup:assert lookup[name]==pins,('Conflicting original cell limits',name)
            lookup[name]=pins
        sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    result=[]
    for word,ends in binding.items():
        instance,pin=ends[0]
        candidates=tables[instance[0]].get(pin,[])
        assert len(candidates)==1,(word,instance,pin,candidates)
        driver=candidates[0]
        driver.update(net=word,macro_instance=instance,macro_output=pin,
                      max_capacitance_ff=lookup.get(driver['master'],{}).get(driver['pin']))
        result.append(dict(driver))
    (out/'drivers.json').write_text(json.dumps(result,indent=2)+'\n')
    report=dict(nets=len(result),with_explicit_or_default_load_limit=sum(r['max_capacitance_ff'] is not None for r in result),
                original_liberty_sha256=sources,scope='Actual final-ODB driver and original library limits; no P&R, model edits, or relaxed limits.')
    (out/'driver-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
