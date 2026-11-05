from pathlib import Path
import json,time
root=Path(r'D:\Data\电路实验').resolve();source=root/'LLMHardwareDesign-worktrees/issue-162-control/work/YUZE-LU/162/continuation-proof-57';parent=root/'LLMHardwareDesign-deliveries/issue-162';target=parent/'incomplete-proof57-capture-01'
assert source.resolve().is_relative_to(root)and target.resolve().is_relative_to(root)
assert source.parent==root/'LLMHardwareDesign-worktrees/issue-162-control/work/YUZE-LU/162'and source.is_dir()and not(source/'index.json').exists()and not target.exists()
parent.mkdir(parents=True,exist_ok=True);source.rename(target)
d=dict(time=time.time(),preserved_partial_capture=str(target),index_written=False,remote_evidence_untouched=True,first_failure='span532 local NameError: Path was not imported; before SSH execution',dependent_capture_failure='collect534 missing local generated control162-s-span532-remote.py before index write',scope='Preserved local incomplete capture, not an accepted evidence index. Fix import then fresh unique complete proof57 capture; no original remote result modified. Raw tool stderr was shown in session, not saved as a separate raw file.')
(root/'control162-capture535-failure.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print('preserved incomplete local capture; remote results unchanged')
