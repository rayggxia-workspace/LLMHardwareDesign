"""Unchanged original sweep audits plus explicit S16 bridge cost accounting."""
from pathlib import Path
from generate import load

HERE=Path(__file__).resolve().parent
runner=load(HERE.parent/'optimization_sweep/run.py','bridge_parent_runner')
runner.HERE=HERE
runner.CASES=('base','vector8_s16_n4','vector8_s16_n4_bridge8')
original_check=runner.check


def check(row,reference,name,pool):
    checked=original_check(row,reference,name,pool)
    m=row['optimization_sweep']
    assert m['M_read_new']==m['M_read_old'] and m['M_read_bytes_per_cycle']==64
    if m['nexp_S16_bridge']:
        assert m['bridge_values']==reference['iteration_study']['fallback_values']
        assert m['bridge_cycles']==(m['bridge_values']//8)*m['bridge_cost_per8']
    else:assert m['bridge_values']==m['bridge_cycles']==0
    checked['bridge_cost_conserved']=True
    return checked


runner.check=check

if __name__=='__main__':raise SystemExit(runner.main())
