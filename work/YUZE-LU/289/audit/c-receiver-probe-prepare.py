from pathlib import Path
import re,json,hashlib
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
p=r/'audit/C-receiver-probe-v1';p.mkdir(exist_ok=False)
src=r/'cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.spef'
s=src.read_text();h=hashlib.sha256(src.read_bytes()).hexdigest()
assert '*377165 _280589_\n' in s
assert re.search(r'^\*I \*377165:A I ',s,re.M)
end=s.index('*PORTS') if '*PORTS' in s else s.index('*D_NET')
bi=max(map(int,re.findall(r'^\*(\d+) \S+',s[:end],re.M)))+1;ni=bi+1
for size in (1,2,4):
 for tag,R,C in [('short',1,.001),('larger',10,.005)]:
  d=p/f'b{size}-{tag}';d.mkdir()
  z=s[:end]+f'*{bi} i289_root_receiver\n*{ni} i289_root_receiver_stub\n\n'+s[end:]
  z=z.replace('*377165:A',f'*{bi}:A')
  z=re.sub(rf'^(\*I \*{bi}:A I)(?: .*|)$',rf'\1 *D BUF_X{size}',z,flags=re.M)
  z+=f'''\n*D_NET *{ni} {C}
*CONN
*I *{bi}:Z O *D BUF_X{size}
*I *377165:A I
*CAP
1 *{bi}:Z {C/2}
2 *377165:A {C/2}
*RES
1 *{bi}:Z *377165:A {R}
*END
'''
  (d/'conditional.spef').write_text(z)
  (d/'assumptions.json').write_text(json.dumps(dict(accepted=False,conditional_only=True,buffer=f'BUF_X{size}',stub_R_ohm=R,stub_C_fF=C*1000,old_sink_node_rebound_to_buffer_input=True,source_spef_sha256=h),indent=2))
assert hashlib.sha256(src.read_bytes()).hexdigest()==h
(p/'source.json').write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [src,r/'audit/C-static-greedy-v2/best.odb',r/'audit/C-static-greedy-v2/receipt.json']},indent=2))
