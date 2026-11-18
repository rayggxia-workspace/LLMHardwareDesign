from pathlib import Path
import re,json
paths=[Path('/public/home/yuzelu/project-circuit/main-blockv2-f300-side-01/flow/results/nangate45/f-native-frame/base/6_final.def'),Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4-repair3/candidate.def')]
for p in paths:
 print(p)
 text=p.read_text();section=text.split('\nNETS ',1)[1].split('\nEND NETS',1)[0]
 for rec in re.split(r'\n\s*- ',section)[1:]:
  n=rec.split()[0];clean=n.replace('\\','')
  if clean.endswith('s_rsp_data[119]') or clean.endswith('s_rsp_data[120]') or clean=='net24988':
   print(rec.split('+ ROUTED')[0][:1600])
