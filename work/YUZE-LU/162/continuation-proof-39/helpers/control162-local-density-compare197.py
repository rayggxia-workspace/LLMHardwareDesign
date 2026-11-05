from pathlib import Path
p=Path(r'D:\Data\电路实验\control162-local-density-diagnostic164.py')
s=p.read_text(encoding='utf-8').replace('[1424,1580,1600,1601,1620,1621,1622]','[1702,1970,1971]').replace('control162-local-density164.json','control162-local-density197.json')
exec(compile(s,'balanced_local_density_actual197','exec'))
