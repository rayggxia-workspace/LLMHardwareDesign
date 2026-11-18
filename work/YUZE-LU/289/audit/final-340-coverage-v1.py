from pathlib import Path
import json, hashlib, re
R=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
hashes={}
def read(p):
    p=Path(p) if str(p).startswith('/') else R/p
    b=p.read_bytes(); hashes[str(p)]=hashlib.sha256(b).hexdigest(); return b.decode()
def j(p): return json.loads(read(p))
def check(p,h):
    hashes[str(Path(p))]=hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert hashes[str(Path(p))]==h,(p,h)
E=j('audit/endpoints.json'); branches=E['branches']
read(__file__)
assert len(branches)==340 and len({b['driver'] for b in branches})==340
assert {v:sum(v in b['variants'] for b in branches) for v in ['A','B']}=={'A':306,'B':340}
C='audit/C-v43-independent-v1/C-v43-margin-plan0/'
cg=j(C+'geometry/receipt.json'); assert cg['signal_die_macro_pin_geometry_exact'] and cg['selected_outputs_all_BUF_X8'] and cg['selected_outputs']==153
u=j('audit/release-candidate-U-v19-preserved/accepted-parent.json'); assert u['passed'] and u['accepted_by_checks'] and u['signal_die_macro_geometry_exact'] and u['selected_x8_drivers']==153
froot='gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4/'
f=j(froot+'accepted-parent.json'); assert f['passed'] and f['signal_and_power_bpin_geometry_unchanged'] and f['macro_positions_unchanged']
assert f['selected_leaf_output']=='local_group.services.store.leaf/req_ready' and f['selected_leaf_driver']=='BUF_X8'
drivers={}
for role,p,receipt in [('C0',C+'geometry/drivers.tsv',cg),('U0','audit/candidate-U-v19-preserved-independent-v3/drivers.tsv',u)]:
    text=read(p); path=str(R/p)
    maps=[v for v in receipt.values() if isinstance(v,dict) and path in v]
    assert maps and any(m[path]==hashes[path] for m in maps),(role,'driver evidence hash absent')
    rows=[x.split() for x in text.splitlines() if x.strip()]
    assert len(rows)==153 and len({x[0] for x in rows})==153
    for port,net,inst,master,pin in rows:
        assert master=='BUF_X8' and pin=='Z'
        drivers[role+'.'+port]=dict(direction='OUTPUT',unique_driver_count=1,instance=inst,master=master,pin=pin,net=net,evidence=path)
for role,leaf,jsonname,portnames in [('C0.G','G-hold03-v3','gate-physical.json',['out_data','out_valid']),('F0.S','S-minimal-localv4','gate.json',['req_ready'])]:
    base='gs/candidate-'+leaf+'/'
    accepted=j(base+'accepted-leaf.json'); assert accepted['passed'] and accepted['selected_driver_count']==(33 if role=='C0.G' else 1)
    vp=str(R/(base+'candidate.v')); v=read(vp); assert hashes[vp]==accepted['sha256'][vp]
    formal=j(base+'formal/receipt.json'); assert formal['passed']
    modules=j(base+'formal/'+jsonname)['modules']
    candidates=[(n,m) for n,m in modules.items() if all(p in m.get('ports',{}) for p in portnames)]
    assert len(candidates)==1; top,m=candidates[0]
    bitdrivers={}
    for n,c in m['cells'].items():
        for p,di in c['port_directions'].items():
            if di=='output':
                for bit in c['connections'][p]: bitdrivers.setdefault(bit,[]).append((n,c['type'],p))
    for pn in portnames:
        port=m['ports'][pn]; assert port['direction']=='output'
        for i,bit in enumerate(port['bits']):
            name=pn if len(port['bits'])==1 else pn+'['+str(i+port.get('offset',0))+']'
            ds=bitdrivers.get(bit,[]); assert len(ds)==1 and ds[0][1:] == ('BUF_X8','Z'),(role,name,ds)
            inst,master,pin=ds[0]
            # Independently bind parsed direct output driver to the accepted actual Verilog.
            pattern=r'\bBUF_X8\s+'+re.escape(inst)+r'\s*\((.*?)\);'
            matches=re.findall(pattern,v,re.S); assert len(matches)==1,(role,inst)
            assert re.search(r'\.Z\s*\(\s*'+re.escape(name)+r'\s*\)',matches[0]),(role,name)
            drivers[role+'.'+name]=dict(direction='OUTPUT',unique_driver_count=1,instance=inst,master=master,pin=pin,net=name,evidence=str(R/(base+'formal/'+jsonname)),accepted_leaf=str(R/(base+'accepted-leaf.json')),actual_verilog=vp)
    if role=='F0.S':
        leafcopy=j(froot+'release/leaf.json'); assert leafcopy==accepted
        lp=str(R/(froot+'release/leaf.json')); assert hashes[lp]==f['hashes'][lp]
        configpath=str(R/(froot+'release/config.mk')); read(configpath); assert hashes[configpath]==f['hashes'][configpath]
g=j('audit/G-geometry-comparison.json'); assert g['physical_geometry_equal'] and g['selected_count']==34
# The historical literal-name comparison failed; independently prove its explicit alias below.
current=[r.split('\t') for r in read(C+'geometry/candidate-geometry.tsv').splitlines()]
def norm(s): return s.replace('\\','')
gboxes=[]
for pin,d in g['differences'].items():
    assert len(d['expected'])==len(d['actual'])==1
    a,b=d['expected'][0],d['actual'][0]
    assert a['instance']=='local_group.'+b['instance'] and a['direction']==b['direction'] and a['rect']==b['rect']
    matches=[r for r in current if r[0]=='MACROPIN' and norm(r[1])==norm(b['instance']) and norm(r[3])==pin and r[4]==b['direction'] and list(map(int,r[-4:]))==b['rect']]
    assert len(matches)==1,(pin,matches)
    gboxes.append(dict(port=pin,expected=a,current=b,layer=matches[0][5]))
assert len(gboxes)==34
gb=j(C+'G-leaf-integration-binding.json'); assert gb['passed'] and gb['selected_driver_count']==33
config=read(gb['actual_C_config']); assert hashes[gb['actual_C_config']]==gb['actual_C_config_sha256']
for var,item in gb['actual_model_bindings'].items():
    check(item['path'],item['sha256']); assert item['path'] in config and var in config
for p,h in gb['accepted_leaf_evidence'].items(): check(p,h)
assert set(drivers)=={b['driver'] for b in branches},(set(drivers)-{b['driver'] for b in branches},{b['driver'] for b in branches}-set(drivers))
rows=[]
for b in branches:
    row=dict(b); row.update(drivers[b['driver']]); rows.append(row)
export=j('audit/C43-plan0-final-proof/actual-export-binding.json'); assert export['export_verified'] and export['saved_final_verilog_exact']
final={p:h for p,h in export['hashes'].items() if '/base/6_final.' in p}
for p,h in final.items():
    # Large final physical files are bound by the independently frozen/exported receipt.
    if p.endswith('.v'): check(p,h)
out=dict(coverage_passed=True,C_backend_accepted=False,remaining_C_gate='Original full deck 120303 and root final disposition',counts=dict(total=340,A=306,B=340,C=153,U=153,G=33,S=1),rows=rows,G_fixed_34_boxes=gboxes,G_historical_literal_comparison_passed=g['passed'],G_explicit_hierarchy_alias_and_current_boxes_reverified=True,G_actual_three_view_binding=gb['actual_model_bindings'],C_final_artifacts=final,geometry_evidence=dict(C=str(R/(C+'geometry/receipt.json')),U=str(R/'audit/release-candidate-U-v19-preserved/accepted-parent.json'),F_S=str(R/(froot+'accepted-parent.json'))),scope='Independent exact endpoint union and accepted-view/version mapping; C signal geometry preserved, PG differences separately qualified. Block backend coverage only; no top-level interconnect timing claim.',input_sha256=hashes)
p=R/'audit/final-340-coverage-v1.json';p.write_text(json.dumps(out,indent=2)+'\n')
(R/'audit/final-340-coverage-v1.md').write_text('# Final 340 output coverage\n\n340/340 unique selected output drivers are BUF_X8: C153, U153, G33, S1. Scheme A306 and B340 exactly match the archived endpoint union. G all34 interface boxes match after the explicit local_group hierarchy alias, including the input out_ready. C43 actual Lib/LEF/GDS bind the accepted G leaf; F binds the accepted S leaf.\n\nC43 actual final Verilog 2b74fbc9 is functionally verified; C backend acceptance remains pending original full deck120303 and root disposition. This receipt does not claim top-level wire timing validation.\n\nMachine per-port mapping and exact input hashes: final-340-coverage-v1.json.\n')
print(p,hashlib.sha256(p.read_bytes()).hexdigest())
