from pathlib import Path
import ast,subprocess,shlex
p=Path(r'D:\Data\电路实验\control162-fastroute-finer-probe171.py');q=ast.literal_eval(ast.parse(p.read_text(encoding='utf-8')).body[2].value)
for a,b in [('source-171','source-172'),('dec7777417befc91a464cf94b0b528ce9ade4c41','9c16b78b7430f636b7833106483da95ef8307232'),('sready171-fastroute24um-probe','sready172-fastroute24um-phase-probe'),('router-fastroute24-preflight-171','router-fastroute24phase-preflight-172')]:
 assert a in q,a;q=q.replace(a,b)
q=q.replace('Actual corrected60um FastRoute no longer hits resource0, but original crossing fixture still has heuristic global overflow and is rejected. Compare24um global guide tiles via unused/unroutable lower search track grids1.6um. Native technology unchanged, actual M11/M12 pitch4um and all original independent geometry/PG/RC gates unchanged; no allow_congestion, no tool patch, no extra node/cancellation. Full three-case fixture and9 negative parser controls mandatory, never system qualification.',
 'Actual171 FastRoute24um finishes all three detailed routes with empty DRC but original independent grid rejects case2 bus7 Y96000DBU (phase0 versus required140). Preserve failure; never round/remap/reinterpret. Source172 sets global guide origin190/140DBU, exactly actual original landing phase, while24um guide half-width12um is a multiple of original4um pitch. All search-only lower grids, native technology and actual M11/M12 pitch/width/spacing/checkerboard/margin/continuity gates unchanged. Full three actual cases and9 negative controls required, no allow_congestion, no tool patch/new node/cancellation or system qualification.')
anchor="state=json.loads((queue/'queue-state.json').read_text())"
q=q.replace(anchor,"assert 'Off-grid Y'in(b/'dynamic-05/node4/00-j-sready171-fastroute24um-probe.log').read_text()\n"+anchor)
compile(q,'phase_aligned_FastRoute_probe172','exec')
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
