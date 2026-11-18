from pathlib import Path
import os,difflib,re,json
p=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-rcx-zero-normalization-v1/reextract-rewire');os.chdir(p);s=(p/'check-import.py').read_text().split('assert vals')[0];exec(s)
for n in names:
 print(n)
 for side in range(2):print(side,vals[side][n])
