import pathlib,json,csv,re,hashlib
P=pathlib.Path;root=P(__file__).resolve().parent;dest=root/'v4'
rows=[]
for p in sorted(dest.glob('*-[23]00/crossing.tsv')):
 data=list(csv.DictReader(p.open(),delimiter='\t'));assert len(data)==256
 assert all(r['startpoint'].startswith('C/') and r['endpoint'].startswith('U/') for r in data)
 log=(p.parent/'run.log').read_text();assert 'REPLAY_COMPLETE' in log
 warnings=[s for s in log.splitlines() if '[WARNING' in s and 'ORD-0011' not in s];assert not warnings,warnings[:10]
 mode={k:min((r for r in data if r['mode']==k),key=lambda r:float(r['slack'])) for k in ('max','min')}
 annotation=(p.parent/'annotation.rpt').read_text()
 portrows=list(csv.DictReader((root/'C-v2/ports.tsv').open(),delimiter='\t'))
 drivers={f"C/{r['cell']}/{r['pin']}" for r in portrows if r['port'].startswith('native_tx_data_o[') and r['pin_direction']=='OUTPUT'}
 assert len(drivers)==128
 assert not any(line.strip() in drivers for line in annotation.splitlines())
 item={'case':p.parent.name,'setup_ns':float(mode['max']['slack']),'hold_ns':float(mode['min']['slack']),'setup_bit':int(mode['max']['bit']),'hold_bit':int(mode['min']['bit']),'paths':256,'source_drivers_annotated':128}
 for filename in ('max_capacitance','max_slew'):
  parsed=[]
  for line in (p.parent/(filename+'.rpt')).read_text().splitlines():
   a=line.split()
   if len(a)==5 and a[0] in drivers:
    parsed.append({'pin':a[0],'limit':float(a[1]),'actual':float(a[2]),'slack':float(a[3])})
  item[filename]={'reported_boundary_pins':len(parsed),'violations':sum(x['slack']<0 for x in parsed),'worst':min(parsed,key=lambda x:x['slack']) if parsed else None}
 rows.append(item)
assert len(rows)==14
(root/'summary.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2))
