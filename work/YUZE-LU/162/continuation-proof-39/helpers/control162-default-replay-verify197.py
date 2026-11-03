from pathlib import Path
p=Path(r'D:\Data\电路实验\control162-default-replay-verify196.py')
exec(compile(p.read_text(encoding='utf-8').replace('1962','1972').replace('sready196-default','sready197-default'),'balanced_default_replay197','exec'))
