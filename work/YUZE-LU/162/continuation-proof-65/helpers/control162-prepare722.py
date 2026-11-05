from pathlib import Path
p=Path(__file__).parent
s=(p/'control162-queue691-remote.py').read_text(encoding='utf-8')
s=s.replace("source-690","source-717").replace('sready691-weighted-bidirectional-controls','sready718-phase-trace-controls').replace('r256-weighted-bidir-regression-691','r256-phase-trace-regression-718').replace('00-f-sready691-weighted-bidirectional-regression','00-f-sready718-phase-trace-regression').replace("'dynamic-03/node5'","'dynamic-07/node7'")
s=s.replace("'--route-regression-baseline',str(b/'source-668/project/experiments/control_v1/tree_router.cpp')","'--route-regression-baseline',str(b/'source-690/project/experiments/control_v1/tree_router.cpp')")
s=s.replace("[(6920,1,'dynamic-07/node7'),(6921,0,'dynamic-02/node3')]","[(7200,1,'dynamic-07/node7')]")
s=s.replace("a.append('--route-weighted-bidirectional');","a+=['--route-weighted-bidirectional','--route-trace-phases'];a[a.index('--seed')+1]='4662';")
s=s.replace("replace('sready589','sready691')","replace('sready589','sready718')")
s=s.replace("candidates=[6920,6921]","candidates=[7200]")
start=s.index("scope='Source690")
end=s.index("'),indent=2)",start)
s=s[:start]+"scope='Source717 adds only optional bounded phase timing trace; actual full regression718 uses source690 baseline, includes27 cases/3 phase-only byte replays/8 invalid rejects and unchanged older tests. Candidate7200 uses current453/S5380 weighted global1 with new independent RNG4662,16active64attempts. All seven final geometry/PG/3RC300MHz/current function and trace prerequisites retained. No physical qualification inherited. Reallocate only exact own old S4610 placement4760 after guarded read719; preserve source/spec/logs, CUGR3751/all other tasks.'"+s[end+1:]
compile(s,'queue718','exec');(p/'control162-queue718-remote.py').write_bytes(s.encode())
s=(p/'control162-refill695-remote.py').read_text(encoding='utf-8')
s=s.replace('sready695-weighted-bidirectional-refill-node5','sready723-phase-trace-refill-node7').replace('sready691-weighted-bidirectional-controls','sready718-phase-trace-controls').replace("len(tasks['tasks'])==15","len(tasks['tasks'])==8")
s=s.replace("[(5, 95155, 'dynamic-03/node5', 4340, 'source-429', 0)]","[(7, 96297, 'dynamic-07/node7', 4760, 'source-474', 0)]")
s=s.replace("current=b/'r256-composition-359/topology/boundary-graph.json'","current=b/'r256-composition-453/topology/boundary-graph.json'")
old="actual=next(x for x in json.loads((b/'r256-old4340-4390-live-spec-readback-696/receipt.json').read_text())['rows']if x['seed']==seed);assert sha(path)==actual['sha256']"
assert old in s
s=s.replace(old,"actual=next(x for x in json.loads((b/'r256-node7-live-readback-719/specs.json').read_text())if x['path']==str(path));assert sha(path)==actual['sha256']")
start=s.index("reason='Reassign")
end=s.index("')",start)
s=s[:start]+"reason='Reassign only exact own S4610 older4760 after12 completed rounds to full phase regression718 then traced current453/S5380 candidate7200. All raw/source/spec preserved. Actual UID/job/host/PID/cmd/source/out/currentgraph/specSHA checked; no old infeasibility claim. Other CUGR3751/current candidates/R/parents untouched. Node7 forecasts32+32+32+64=160GiB;1.2*160+16=208GiB below read719 actual451GiB MemAvailable. No concurrency decrease or final gate relaxation.'"+s[end+1:]
compile(s,'refill723','exec');(p/'control162-refill723-remote.py').write_bytes(s.encode())
