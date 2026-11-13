"""Fixture-only reset-counter acceleration for exact native wrap reproduction."""
import argparse
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--p',type=Path,required=True);p.add_argument('--m',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
p.add_argument('--early-fence',type=int,choices=(0,1),default=0)
p.add_argument('--stale-permit-control',type=int,choices=(0,1),default=0)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
for path,old,new in (
    (a.p,'context_generation[i]<=0;context_next_k[i]<=0;', "context_generation[i]<=i==0?16'hfffe:16'd0;context_next_k[i]<=0;"),
    (a.m,'scope_generation[s]<=0;scope_epoch[s]<=0;', "scope_generation[s]<=s==0?16'hfffe:16'd0;scope_epoch[s]<=0;"),
):
    text=path.read_text();assert text.count(old)==1
    text=text.replace(old,new)
    if path==a.p and a.early_fence:
        needle='next_session<=1;control_session<=0;'
        assert text.count(needle)==1
        text=text.replace(needle,'next_session<=SESSION_LIMIT;control_session<=0;')
    if path==a.p and a.stale_permit_control:
        needle="if(current_context_generation==0||current_context_generation==16'hffff)context_wrap_allowed[context_id]<=0;"
        assert text.count(needle)==1
        text=text.replace(needle,"if(current_context_generation==0)context_wrap_allowed[context_id]<=0;")
    (a.out/path.name).write_text(text)

