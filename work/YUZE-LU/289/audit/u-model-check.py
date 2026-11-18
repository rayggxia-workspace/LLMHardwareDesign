from pathlib import Path
import json,re,hashlib
p=Path('.').resolve();name='u_n32_controlled_dma_64';lib=p/(name+'.lib');lef=p/(name+'.lef');data=json.loads((p/'imported-model.json').read_text())['modules'][name]
ports={}
for n,port in data['ports'].items():
 width=len(port['bits']);off=port.get('offset',0)
 names=[n] if width==1 else [n+'['+str(off+i)+']' for i in range(width)]
 for x in names:assert x not in ports;ports[x]=port['direction'].upper()
physical={};supply={}
for line in (p/'imported-pins.tsv').read_text().splitlines():
 a=line.split('\t')
 if a[0]=='TERM':
  if a[3] in ('POWER','GROUND'):supply[a[1]]={'lef_direction':a[2],'signal_type':a[3]}
  else:physical[a[1]]=a[2]
for n,v in supply.items():
 assert n in ports and ports[n]=='INPUT' and v['lef_direction']=='INOUT',(n,v,ports.get(n))
 v['liberty_direction']=ports.pop(n)
assert ports==physical,('Liberty/LEF signal interface mismatch',set(ports)^set(physical))
text=lib.read_text();time=re.search(r'\btime_unit\s*:\s*"([^"]+)"',text)[1];cap=re.search(r'\bcapacitive_load_unit\s*\(\s*([^,]+),\s*([^)]+)\)',text).groups();voltage=re.search(r'\bvoltage_unit\s*:\s*"([^"]+)"',text)[1]
assert time.lower()=='1ns' and float(cap[0])==1 and cap[1].strip().lower()=='ff' and voltage.lower()=='1v',(time,cap,voltage)
assert name in (p/'imported-timing-cell.txt').read_text()
r=dict(passed=True,independent_importers=['Fresh OpenROAD Liberty+LEF','Yosys Liberty blackbox'],signal_pin_count=len(ports),directions_exact=True,supply_ports=supply,supply_convention='Liberty input supply pins correspond to LEF INOUT POWER/GROUND',time_unit=time,capacitance_unit=list(cap),voltage_unit=voltage,nominal_voltage=float(re.search(r'nom_voltage\s*:\s*([\d.]+)',text)[1]),nominal_temperature=float(re.search(r'nom_temperature\s*:\s*([\d.]+)',text)[1]),source_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (lib,lef,p/'imported-pins.tsv',p/'imported-model.json')})
(p/'model-import-receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
