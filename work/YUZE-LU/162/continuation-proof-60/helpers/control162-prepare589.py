from pathlib import Path
home=Path(__file__).parent
old=(home/'control162-queue564-remote.py').read_text(encoding='utf-8')
old=old.replace('sready564-s-local-existing-bidirectional','sready589-zero-pattern-controlled')
old=old.replace("record.mkdir();", """gates={}
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py','resource_search.h']:
 p=b/'source-587/project/experiments/control_v1'/name;assert sha(p)==sha(b/'source-537/project/experiments/control_v1'/name);gates[name]=sha(p)
reg=b/'r256-zero-pattern-regression-589'
spec=dict(script='system_upper.py',source_root=str(b/'source-587'),forecast_gib=16,requires=[],args=['--manifest',str(b/'r256-composition-359/selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--directional-regression-only','--route-regression-baseline',str(b/'source-537/project/experiments/control_v1/tree_router.cpp'),'--out',str(reg)])
p=b/'dynamic-07/node7/pending/00-f-sready589-zero-pattern-regression.json';assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
record.mkdir();""")
# Use the immutable current S scene/full chain as the comparison, not the older placement.
old=old.replace("sready500-bidirectional-signal-search/tasks.json", "sready564-s-local-existing-bidirectional/tasks.json")
old=old.replace("'-5010'", "'-5640'").replace("acceptance-5010.json", "acceptance-5640.json")
old=old.replace("acceptance-5640.json';assert not config", "acceptance-5890.json';assert not config")
old=old.replace("'/upper-candidates/5010/'", "'/upper-candidates/5640/'")
old=old.replace("'/upper-candidates/5640/'))", "'/upper-candidates/5890/'))")
old=old.replace(".replace('/upper-candidates/5640/','/upper-candidates/5640/')", ".replace('/upper-candidates/5640/','/upper-candidates/5890/')")
old=old.replace(".replace('acceptance-5640.json','acceptance-5640.json')", ".replace('acceptance-5640.json','acceptance-5890.json')")
old=old.replace("assert spec['source_root']==str(b/'source-474')", "assert spec['source_root']==str(b/'source-474');spec['source_root']=str(b/'source-587')")
old=old.replace("if spec['script']=='system_upper.py':", "if spec['script']=='system_upper.py':")
old=old.replace("a=spec['args'];assert", "a=spec['args'];a+=['--route-ordinary-zero-pattern'];spec['requires']+=[str(b/'r256-zero-pattern-regression-589/receipt.json')];assert")
old=old.replace(".replace('sready501','sready564').replace('5010','5640')", ".replace('sready564','sready589').replace('5640','5890')")
old=old.replace("candidate=5640", "candidate=5890")
start=old.index("scope='Reuse exactly")
end=old.index("'),indent=2)",start)
old=old[:start]+"scope='Controlled5890 differs actual5640 only source587 bounded zero-occupancy ordinary prepass; same current453 graph, reconstructed S5380 scene, all native fixed masks, finite constrained search, RNG4661/cost2/scale1/h256/bidirectional/critical8m64attempts16active. Original search remains fallback. Requires actual full independent589 regression before route. Full original geometry/nativeXOR/PG/three distributedRC300MHz/current453 real function/joint gates unchanged. This is an unqualified search hypothesis, no speed/convergence/system claim. Preserve all prior raw evidence and independent CUGR3751 comparator. Exact own older359 source400 fixed4050 slot may be reassigned after identity guard; parents/foreign/R/current453 searches untouched."+old[end:]
(home/'control162-queue589-remote.py').write_bytes(old.encode())
print(old)
