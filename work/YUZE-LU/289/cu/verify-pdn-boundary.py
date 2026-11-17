from pathlib import Path
import json
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/u-macro-pdn-v1')
def lines(name):return (p/name).read_text().splitlines()
a=lines('before-geometry.tsv');b=lines('after-geometry.tsv')
def signal_geometry(rows):return [r for r in rows if not (r.startswith('PIN\tVDD\t') or r.startswith('PIN\tVSS\t'))]
assert signal_geometry(a)==signal_geometry(b),'Signal/macro/die geometry changed'
assert lines('before-instances.tsv')==lines('after-instances.tsv'),'Placement changed'
x=lines('before-nets.tsv');y=lines('after-nets.tsv')
def sig(rows):return [r for r in rows if r.split('\t')[0] not in {'VDD','VSS'}]
assert sig(x)==sig(y),'Signal logic connections changed'
result={'signal_geometry_equal':True,'instances_equal':True,'signal_nets_equal':True,'power_geometry_removed':sorted(set(a)-set(b)),'power_geometry_added':sorted(set(b)-set(a)),'power_net_term_counts_before':{r.split('\t')[0]:len(r.split('\t'))-2 for r in x if r.split('\t')[0] in {'VDD','VSS'}},'power_net_term_counts_after':{r.split('\t')[0]:len(r.split('\t'))-2 for r in y if r.split('\t')[0] in {'VDD','VSS'}},'full_routing_and_gds_signoff':'pending; legacy PG_FIX_PASS banner routed claim is not applicable at CTS stage'}
(p/'boundary-proof.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if not k.startswith('power_geometry')}))
