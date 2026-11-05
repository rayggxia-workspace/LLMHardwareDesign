from pathlib import Path
home=Path(r'D:\Data\电路实验')
for name in ['control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py']:
 p=home/name;s=p.read_text(encoding='utf-8');old="'s-ready-internal-channel-openroad-source157.json'";new="'s-ready-clear-placement-openroad-source157.json'";assert s.count(old)==1 and new not in s
 s=s.replace(old,old+','+new);compile(s,name,'exec');p.write_text(s,encoding='utf-8');print(name,'new source157 record discovered; original joint gates retained')
