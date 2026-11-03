from pathlib import Path
import json,subprocess,datetime
D=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt737')
r=json.loads((D/"SUBMISSION.json").read_text())
with(D/"step.log").open("w")as f:p=subprocess.run(r["command"],stdout=f,stderr=subprocess.STDOUT)
(D/"STEP_CLIENT_EXIT.json").write_text(json.dumps(dict(time=datetime.datetime.now().isoformat(),exit=p.returncode,parent_job=r["job_id"]),indent=2)+"\n")
