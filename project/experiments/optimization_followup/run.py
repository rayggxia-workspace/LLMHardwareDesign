"""Keep the original sweep runner/audits; add explicit followup checks."""
import importlib.util
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'optimization_sweep'
# Import this directory's generator before loading the parent runner.
from generate import generate, load, sha

runner=load(BASE/'run.py','followup_parent_runner')
runner.HERE=HERE
runner.CASES=('base','s16_n4','s16_n8','vector16_s16_n4','read128','m16_feed2_read128','balanced')
original_check=runner.check


def check(row,reference,name,pool):
    checked=original_check(row,reference,name,pool)
    m=row['optimization_sweep']
    if m['nexp_S16_bridge']:
        assert m['bridge_cycles']==m['bridge_values']//8, 'current workload bridge accounting'
        assert m['bridge_values']==reference['iteration_study']['fallback_values'], 'S16 eligibility mismatch'
    else:
        assert m['bridge_cycles']==m['bridge_values']==0
    assert m['M_read_new']<=m['M_read_old'], 'negative local-read saving'
    if m['M_read_bytes_per_cycle']==64:
        assert m['M_read_new']==m['M_read_old']
    checked['followup_cost_accounting']=True
    return checked


runner.check=check

if __name__=='__main__':
    raise SystemExit(runner.main())
