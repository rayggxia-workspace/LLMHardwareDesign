from pathlib import Path
import subprocess,shlex
h=Path(__file__).parent
q=(h/'control162-queue434-remote.py').read_text()
q=q.replace("source-429","source-435").replace("sready434-compact-upper","sready439-critical-first")
q=q.replace("r256-memory-envelope-regression-430","r256-critical-partition-regression-438")
q=q.replace("assert json.loads(reg.read_text())['passed']","assert not reg.exists()")
q=q.replace("[(4340,4240,'dynamic-03/node5')]","[(4390,4240,'dynamic-02/node3')]")
q=q.replace("str(seed);a[a.index('--reuse-placement')", "str(4340);a[a.index('--reuse-placement')")
q=q.replace("a+=['--route-resource-labels','8000000']", "a+=['--route-resource-labels','8000000','--route-critical-first']")
q=q.replace("replace('sready408','sready434')", "replace('sready408','sready439')")
q=q.replace("scope='All necessary checks clear but extremely small electrical margin; no route/RC feasibility claim. Larger area is charged to actual scene.'", "scope='Necessary checks clear, high0.912560336; actual81.321408mm2. Controlled comparison against4340: same RNG4340, placement4240 and search parameters, only per-round priority differs. No route feasibility claim.'")
at="template=[r for r"
regcode="""regdir=reg.parent
rspec=dict(script='system_upper.py',source_root=str(source),forecast_gib=16,requires=[str(root/'selected/receipt.json')],args=['--manifest',str(root/'selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--directional-regression-only','--route-regression-baseline',str(b/'source-429/project/experiments/control_v1/tree_router.cpp'),'--out',str(regdir)])
rp=b/'dynamic-02/node3/pending/00-f-sready438-critical-regression.json';assert not rp.exists();rt=rp.with_suffix('.tmp');rt.write_text(json.dumps(rspec));rt.rename(rp);rows.append(dict(path=str(rp),sha256=sha(rp),spec=rspec))

"""
q=q.replace(at,regcode+at,1)
start=q.index("scope='Actual4240",q.index('record.mkdir()'))
end=q.index("'),indent=2",start)
q=q[:start]+"scope='Controlled full7stage4390 vs4340: identical placement4240, RNG4340, cost8/heuristic16/congestion1,8million labels,64attempts16active; only optional constrained-priority partition on each negotiated round changes. Original nine physical/RC/program/budget sources unchanged. Actual438 regression and422 events are mandatory prerequisites; all geometry/nativeXOR/PG/low-base-high300MHz/currentfunction/joint gates retained. No whole-system pass or routing improvement claim. Original failures/sources retained; no foreign/R action.'"+q[end+1:]
compile(q,'queue439','exec');(h/'control162-queue439-remote.py').write_bytes(q.encode())
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
