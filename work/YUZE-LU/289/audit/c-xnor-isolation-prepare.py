from pathlib import Path
import re,json,hashlib
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
p=r/'audit/C-xnor-isolation-conditional-v1';p.mkdir(exist_ok=False)
src=r/'cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.spef'
s=src.read_text();h=hashlib.sha256(src.read_bytes()).hexdigest()
assert '*69042 _069041_\n' in s and '*377165 _280589_\n' in s
start=s.index('*D_NET *69042 ');end=s.index('*END',start)+len('*END')
net=s[start:end];assert net.count('*I *377165:ZN O *D XNOR2_X1')==1
name_end=s.index('*PORTS') if '*PORTS' in s else s.index('*D_NET')
ids=[int(x) for x in re.findall(r'^\*(\d+) \S+',s[:name_end],re.M)]
bi,ni=max(ids)+1,max(ids)+2
new=s[:name_end]+f'*{bi} i289_root_xnor_iso\n*{ni} i289_root_xnor_stub\n\n'+s[name_end:]
new=new.replace('*377165:ZN',f'*{bi}:Z')
new=new.replace(f'*I *{bi}:Z O *D XNOR2_X1',f'*I *{bi}:Z O *D BUF_X8')
stub=f'''\n*D_NET *{ni} 0.001
*CONN
*I *377165:ZN O *D XNOR2_X1
*I *{bi}:A I *D BUF_X8
*CAP
1 *377165:ZN 0.0005
2 *{bi}:A 0.0005
*RES
1 *377165:ZN *{bi}:A 1
*END
'''
new+=stub
# Existing extraction is identical except driver-node rebinding and its model hint.
assert net.replace('*377165:ZN',f'*{bi}:Z').replace(f'*I *{bi}:Z O *D XNOR2_X1',f'*I *{bi}:Z O *D BUF_X8') in new
(p/'conditional.spef').write_text(new)
assert hashlib.sha256(src.read_bytes()).hexdigest()==h
(p/'assumptions.json').write_text(json.dumps(dict(accepted=False,source_spef_sha256=h,driver='_280589_/ZN',net='_069041_',buffer='BUF_X8',stub_R_ohm=1,stub_C_fF=1,original_wire_network_preserved=True,scope='Conditional planning only: exact old RC rebound to new output; explicit hypothetical short stub. No placement/routing/PG/signoff claim'),indent=2))
