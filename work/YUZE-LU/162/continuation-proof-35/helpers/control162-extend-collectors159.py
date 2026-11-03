from pathlib import Path
home=Path(r'D:\Data\电路实验')
for name in ['control162-system-ready140.py','control162-final-receipts-retry140.py','control162-next-gate143.py']:
 p=home/name;s=p.read_text(encoding='utf-8');old="'s-ready-openroad-source157.json'";new="'s-ready-internal-channel-openroad-source157.json'"
 assert s.count(old)==1 and new not in s,name
 s=s.replace(old,old+','+new)
 if name=='control162-next-gate143.py':
  old='1510';assert old in s
  # Only the explicit retired seed set; avoid any command/path substitution.
  import re
  matches=list(re.finditer(r'\{[^{}\n]*1510[^{}\n]*\}',s))
  if len(matches)==1:
   m=matches[0];s=s[:m.start()]+m.group()[:-1]+',1432,1433}'+s[m.end():]
 compile(s,name,'exec');p.write_text(s,encoding='utf-8')
 print('Extended unchanged strict record discovery',name)
