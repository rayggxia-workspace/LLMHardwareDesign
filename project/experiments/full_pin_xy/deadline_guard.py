"""Report hard-deadline phase; never cancel existing jobs."""
from pathlib import Path
import datetime,json,sys
p=Path(__file__).resolve().parents[3]/'docs/experiments/issue-126-full-pin/data/deadline_run.json'
r=json.loads(p.read_text(encoding='utf-8'));now=datetime.datetime.now(datetime.timezone.utc)
start=datetime.datetime.fromisoformat(r['budget_start_utc']);deadline=datetime.datetime.fromisoformat(r['hard_deadline_utc']);delivery=datetime.datetime.fromisoformat(r['delivery_window_starts_utc'])
phase='DEADLINE_DELIVER_NOW_NO_NEW_ENGINEERING' if now>=deadline else 'FINAL_DELIVERY_WINDOW_NO_NEW_HEAVY_JOBS' if now>=delivery else 'EXECUTE'
print(json.dumps({'phase':phase,'now_utc':now.isoformat(),'hours_elapsed':(now-start).total_seconds()/3600,'hours_remaining':max(0,(deadline-now).total_seconds()/3600),'deadline_Asia_Shanghai':r['hard_deadline_Asia_Shanghai'],'hourly_report_due_at_latest':min(int((now-start).total_seconds()//3600),12),'never_cancel_existing_jobs':True}))
sys.exit(2 if now>=deadline else 0)
