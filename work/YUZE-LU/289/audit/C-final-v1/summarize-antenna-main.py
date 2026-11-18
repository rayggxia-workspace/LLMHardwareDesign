from pathlib import Path
import json,collections,re,hashlib
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');out=r/'audit/C-final-v1/antenna-C-v20-native-clock4-119976';m=json.loads((out/'antenna-net-map.json').read_text());assert m['mapping_complete']
ports=collections.defaultdict(set)
for line in (out/'bpins.tsv').read_text().splitlines():
 p,n,*_=line.split('\t');ports[n].add(p)
definition=(r/'cu/runs/C-v20-native-clock4/flow/results/nangate45/c-overlay-current/base/6_final.def').read_text()
pins=re.search(r'\nPINS\s+\d+\s*;(.*?)\nEND PINS',definition,re.S)[1];directions={}
for e in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',pins,re.M|re.S):
 directions[e[1].replace('\\','')]=re.search(r'\+\s+DIRECTION\s+(\S+)',e[2])[1]
selected=set((r/'cu/C-outputs.txt').read_text().splitlines());category=collections.Counter(x['category'] for x in m['markers']);marker_by_id={x['report_id']:x for x in m['markers']}
rows=[]
for n in m['networks']:
 row=dict(net=n['net'],report_count=len(n['report_ids']),layers=sorted({marker_by_id[i]['layer'] for i in n['report_ids']}),top_ports=sorted(ports[n['net']]),top_port_directions={p:directions[p.replace('\\','')] for p in sorted(ports[n['net']])},selected_output_ports=sorted(ports[n['net']]&selected),existing_parent_diodes=[x['instance'] for x in n['existing_parent_diodes']],standard_driver_pins=[dict(instance=x['instance'],master=x['master'],pin=x['pin']) for x in n['standard_endpoints'] if x['direction']=='OUTPUT'],standard_input_pins=sum(x['direction']=='INPUT' for x in n['standard_endpoints']))
 rows.append(row)
summary=dict(mapping_complete=True,accepted=False,source_scope='C-v20-native-clock4 diagnostic physical layout; native DRC1 so not an accepted C implementation. No diode ECO emitted.',antenna_report_items=len(m['markers']),unique_mapped_nets=len(rows),nonparent=0,ambiguous=0,unmapped=0,checked_endpoint_nets=m['checked_endpoint_nets'],scanned_route_segments=m['scanned_segments'],report_categories=dict(category),nets_touching_top_ports=sum(bool(x['top_ports']) for x in rows),all_mapped_top_ports_are_inputs=all(set(x['top_port_directions'].values())=={'INPUT'} for x in rows),nets_touching_selected_outputs=sum(bool(x['selected_output_ports']) for x in rows),nets_with_existing_parent_antennax1=sum(bool(x['existing_parent_diodes']) for x in rows),scope='Counts describe actual report/network attribution, not required diode count. Macro-internal diodes are not enumerated by parent ODB. Recheck reports on any changed physical candidate.',mapping_sha256=hashlib.sha256((out/'antenna-net-map.json').read_bytes()).hexdigest(),source_sha256=m['source_sha256'])
(out/'summary.json').write_text(json.dumps(summary,indent=2));(out/'mapped-net-inventory.json').write_text(json.dumps(rows,indent=2));(out/'mapped-nets.txt').write_text('\n'.join(sorted(x['net'] for x in rows))+'\n');print(json.dumps({k:v for k,v in summary.items() if k!='source_sha256'},indent=2))

