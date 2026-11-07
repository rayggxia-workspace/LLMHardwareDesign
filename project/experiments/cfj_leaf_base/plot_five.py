"""Render qualified five-type _128/_64 placements from immutable archives.
Usage: python -B plot_five.py inputs.json OUTPUT_DIRECTORY
inputs.json is a list of {kind, version, archive, archive_sha256}.
Only figure products/source indices are written; archives remain read-only.
"""
import hashlib, io, json, re, sys, tarfile
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle

def sha(b): return hashlib.sha256(b).hexdigest()
aliases={'local_s_base':'S','local_s_p':'S','block_v2_g':'G','block_v2_e_compact':'E','transaction6k':'T','r_stream_local':'R','block_v2_m':'M','block_v2_n':'N','normalize':'N'}
roles={'store':'S','multiply':'M','gate':'G','elementwise':'E','normalize':'N'}
colors=dict(zip('MNGESRT',['#87b9e7','#b3a2e5','#f3cb76','#e9a4a4','#9bd2b1','#8db5e3','#c2addd']))
items=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig')); out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
datasets=[]; sources=[]
for item in items:
 p=Path(item['archive']); actual=hashlib.file_digest(p.open('rb'),'sha256').hexdigest();assert actual==item['archive_sha256'],p
 wanted={}
 with tarfile.open(p,'r|gz') as tar:
  for m in tar:
   if m.name in ('native/6_final.def','native/inputs.json','physical/inventory.json','SHA256SUMS'):
    wanted[m.name]=tar.extractfile(m).read()
 assert 'native/6_final.def' in wanted
 members={n:sha(b) for n,b in wanted.items() if n!='SHA256SUMS'}
 if 'SHA256SUMS' in wanted:
  sums={line[66:].removeprefix('./'):line[:64] for line in wanted['SHA256SUMS'].decode().splitlines() if len(line)>66}
  for n,h in members.items():
   assert sums.get(n)==h,(p,n,sums.get(n),h)
 data=wanted['native/6_final.def'].decode(); units=int(re.search(r'UNITS DISTANCE MICRONS (\d+)',data)[1]); die=re.search(r'DIEAREA\s+\(\s*(\d+)\s+(\d+)\s*\)\s+\(\s*(\d+)\s+(\d+)\s*\)',data)
 assert die and int(die[1])==int(die[2])==0
 size=[int(die[3])/units,int(die[4])/units]
 if 'physical/inventory.json' in wanted:
  inv=json.loads(wanted['physical/inventory.json']); macros=inv['instances']; assert inv['size_um']==size
  dims={v['master']:v['size_um'] for v in macros.values()}
 else:
  cfg=json.loads(wanted['native/inputs.json']);assert cfg['die_um']==size
  dims={a:cfg['dimensions'][r] for a,al in aliases.items() for r,ral in roles.items() if al==ral and r in cfg['dimensions']}
 points=[]; macros=[]
 comp=data.split('COMPONENTS ',1)[1].split('END COMPONENTS',1)[0]
 for part in comp.split(';'):
  m=re.search(r'-\s+(\S+)\s+(\S+).*?\+\s+(?:PLACED|FIXED)\s+\(\s*(\d+)\s+(\d+)\s*\)\s+(\S+)',part,re.S)
  if not m:continue
  name,master,x,y,orient=m.groups();xy=[int(x)/units,int(y)/units]
  if master in dims:
   w,h=dims[master];assert orient in ('N','S','FN','FS'),orient
   macros.append(dict(name=name,master=master,alias=aliases[master],xy_um=xy,size_um=[w,h],orientation=orient))
  elif not master.startswith(('FILLCELL','TAPCELL')):points.append(xy)
 assert len(macros)=={'P':3,'U':3,'C':4,'F':3,'J':3}[item['kind']],(p,macros)
 assert points
 source={k:v for k,v in item.items() if k!='archive'};source.update(archive_name=p.name,member_sha256=members,size_um=size,macros=macros,standard_cell_points=len(points))
 sources.append(source);datasets.append((item,size,macros,points));print(item['kind'],item['version'],len(points),flush=True)
for version in ('128','64'):
 fig,axes=plt.subplots(2,3,figsize=(17,10)); selected=[d for d in datasets if d[0]['version']==version]
 for ax,(item,(w,h),macros,points) in zip(axes.flat,selected):
  x,y=zip(*points);ax.scatter(x,y,s=.3,c='#626b74',alpha=.4,linewidths=0)
  for m in macros:
   x,y=m['xy_um'];mw,mh=m['size_um'];al=m['alias'];ax.add_patch(Rectangle((x,y),mw,mh,facecolor=colors[al],edgecolor='#354052',lw=1,zorder=3))
   label='16 KiB S' if al=='S' else 'R256' if al=='R' else al
   ax.text(x+mw/2,y+mh/2,f'{label}\n{mw:g}×{mh:g}',ha='center',va='center',fontsize=8 if al=='G' else 10,zorder=4)
  ax.add_patch(Rectangle((0,0),w,h,fill=False,ls='--',edgecolor='#75808b'))
  ax.set(xlim=(-20,w+20),ylim=(-20,h+20),aspect='equal',title=f"{item['kind']}_{version} — {w:g} × {h:g} µm",xlabel='µm',ylabel='µm');ax.tick_params(labelsize=8);ax.spines[:].set_visible(False)
 axes.flat[5].axis('off')
 axes.flat[5].text(.05,.7,'每幅为独立验收夹具的实际摆放。\n各面板坐标独立，比例尺见坐标轴。\n\n彩色：独立功能叶宏。\n灰点：局控、适配/服务与物理修复单元。\n不含 filler / tap。\n\n虚线不是组合硬宏边界。\nJ 宏外另有三路汇合算术资源。\n图中尺寸单位均为 µm。',fontproperties=font,fontsize=12,va='top',linespacing=1.7)
 fig.suptitle(f'P / U / C / F / J：_{version} 最终验收摆放',fontproperties=font,fontsize=19)
 fig.tight_layout(rect=(0,.02,1,.95)); fig.savefig(out/f'placement-{version}.png',dpi=150,facecolor='white');plt.close(fig)
(out/'placement-source.json').write_text(json.dumps({'schema':1,'scope':'Independent TT 300 MHz fixtures; not nine-instance placement or joint-top acceptance.','sources':sources},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
