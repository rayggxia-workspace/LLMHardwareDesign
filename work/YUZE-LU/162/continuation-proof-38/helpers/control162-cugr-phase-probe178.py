"""Queue an independent CUGR comparison on the same phase-correct search grid."""
from pathlib import Path
import subprocess, shlex

p = Path(r'D:\Data\电路实验\control162-fastroute-finer-probe171.py')
scope = {}
exec(compile(p.read_text(encoding='utf-8').rsplit('\nprint(subprocess.check_output', 1)[0], str(p), 'exec'), scope)
q = scope['q']
for a, b in [
    ('source-171', 'source-172'),
    ('dec7777417befc91a464cf94b0b528ce9ade4c41', '9c16b78b7430f636b7833106483da95ef8307232'),
    ('sready171-fastroute24um-probe', 'sready178-cugr24um-phase-probe'),
    ('router-fastroute24-preflight-171', 'router-cugr24phase-preflight-178'),
    ("'--openroad-global-router','fastroute'", "'--openroad-global-router','cugr'"),
    ("assert len(state['active'])<=3", "assert len(state['active'])<=4"),
]:
    assert a in q, a
    q = q.replace(a, b)
old = 'Actual corrected60um FastRoute no longer hits resource0, but original crossing fixture still has heuristic global overflow and is rejected. Compare24um global guide tiles via unused/unroutable lower search track grids1.6um. Native technology unchanged, actual M11/M12 pitch4um and all original independent geometry/PG/RC gates unchanged; no allow_congestion, no tool patch, no extra node/cancellation. Full three-case fixture and9 negative parser controls mandatory, never system qualification.'
assert old in q
q = q.replace(old, 'Queue independent CUGR50 on the already fixture-qualified source172 phase-correct24um guide grid; original190/140DBU phase, M11/M12 pitch4um and checkerboard/margin rules unchanged. Existing CUGR candidates use60um guides. Actual1770 FastRoute uses this24um guide grid and continues untouched. This probe waits for a current node4 slot; dynamic controller preserves4x16 and unchanged memory guard, no cancellation/new node/R change. Three actual detailed-route fixtures and9 parser negatives required before admitting any full-scene CUGR24 candidate. No final qualification or physical threshold change.')
q = q.replace("assert json.loads((b/'router-fastroute-preflight-170/receipt.json').read_text())['passed']is False", "assert json.loads((b/'router-fastroute24phase-preflight-172/receipt.json').read_text())['passed']is True")
q = q.replace("print('Appended actual24um FastRoute probe in existing own slot')", "print('Queued CUGR24 phase-correct preflight behind current node4 work; no job cancelled')")
compile(q, 'actual_cugr_phase_probe178', 'exec')
print(subprocess.check_output(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', 'yuzelu@10.129.166.172', 'python3 -c '+shlex.quote(q)], timeout=45).decode())
