"""Join independently computed gates without rewriting their receipts."""
import sys,json,hashlib,re
from pathlib import Path
c=Path(sys.argv[1]).resolve();role=sys.argv[2];assert role in ('G','S')
q=c/'qualification-v2'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
physical=read(q/'physical-receipt.json')
formal=read(c/'formal/receipt.json')
state=read(c/'formal/state-preservation-v2.json')
counts=dict(line.split() for line in (c/'independent-sta-counts.tsv').read_text().splitlines())
log=(c/'independent-sta-worker.log').read_text()
assert physical['hashes'][str(c/'candidate.odb')]==sha(c/'candidate.odb')
assert formal['hashes'][str(c/'candidate.v')]==sha(c/'candidate.v')
assert physical['full_deck_items']==0 and physical['native_drc_empty']
assert formal['passed'] and state['passed'] and state['clock_reset_upstream_cones_identical']
assert set(counts)=={'setup','hold','capacitance','slew','fanout'} and all(int(v)==0 for v in counts.values())
assert all(x in log for x in ['All shapes on net VDD are connected.','All shapes on net VSS are connected.','Found 0 net violations.','Found 0 pin violations.'])
assert 'GS_CANDIDATE_COMPLETE_NOT_QUALIFIED' in (c/'implementation.log').read_text()
changes=(c/'changes.tsv').read_text().splitlines()[1:]
assert len(changes)==(33 if role=='G' else 1)
assert all(line.split('\t')[-2:]==['BUF_X4','BUF_X8'] for line in changes)
model='block_v2_g' if role=='G' else 'local_s_base'
paths=[c/'candidate.odb',c/'candidate.def',c/'candidate.spef',c/'candidate.sdc',c/'candidate.v',q/(model+'.lib'),q/(model+'.lef'),q/'physical-receipt.json',c/'formal/receipt.json',c/'formal/state-preservation-v2.json',c/'independent-sta-counts.tsv',c/'independent-sta-worker.log',c/'changes.tsv']
report=dict(passed=True,scope='Leaf macro only; parent integration and top-line loading remain separate',role=role,selected_driver_count=len(changes),state_count=state['state_count'],counts=counts,clock_period_line=next(x for x in (c/'candidate.sdc').read_text().splitlines() if x.startswith('create_clock')),sha256={str(p):sha(p) for p in paths})
(c/'accepted-leaf.json').write_text(json.dumps(report,indent=2))
