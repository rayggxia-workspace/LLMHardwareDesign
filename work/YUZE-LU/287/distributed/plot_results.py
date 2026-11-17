import pathlib,csv,json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
p=pathlib.Path(__file__).resolve().parent;src=p/'results/sta-all.csv'
rows=list(csv.DictReader(src.open(encoding='utf-8')));assert len(rows)==1292
assert all(len([r for r in rows if r['MHz']==str(f)])==646 for f in [200,300])
out=pathlib.Path('C:/Users/wine10/.codex/visualizations/2026/11/17/01a1e8cf-62f1-7bf3-9a01-7ec244d1932a/distributed-sta');out.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':10,'axes.unicode_minus':False})
styles=[('A','CU','#2879b7','o'),('B','CU','#dc8425','^'),('B','GS','#8754b0','D')]
for metric,title,ylab in [('setup_ns','长度—最差 setup 裕量','最差 setup slack（ns）'),('hold_ns','长度—最差 hold 裕量','最差 hold slack（ns）')]:
 fig,axes=plt.subplots(1,2,figsize=(13,6),sharex=True,sharey=True,layout='constrained')
 for ax,mhz in zip(axes,[200,300]):
  for scheme,group,color,marker in styles:
   data=[r for r in rows if r['MHz']==str(mhz) and r['scheme']==scheme and r['group']==group]
   for bad in [True,False]:
    selected=[r for r in data if (r['source_cap_violation']=='True' or r['source_slew_violation']=='True')==bad]
    ax.scatter([float(r['length_um'])/1000 for r in selected],[float(r[metric]) for r in selected],s=25 if bad else 42,marker=marker,facecolors='none' if bad else color,edgecolors=color,linewidths=.8,alpha=.65 if bad else 1)
  ax.axhline(0,c='#b43b3b',lw=1,ls='--');ax.grid(alpha=.15);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
  ax.set(xlabel='真实线路长度（mm）',xlim=(0,5.6));ax.set_title(f'{mhz} MHz · 646条线路',fontsize=14,pad=12)
 axes[0].set_ylabel(ylab);fig.suptitle(title+'｜同一合格 C/U 基准回放',fontsize=19)
 handles=[Line2D([],[],marker=m,color=c,ls='',markerfacecolor='none',label=s+' · '+g) for s,g,c,m in styles]
 handles += [Line2D([],[],marker='o',color='#526070',ls='',markerfacecolor='none',label='电容或 slew 超限'),Line2D([],[],marker='o',color='#526070',ls='',label='本夹具源端电气检查通过')]
 axes[0].legend(handles=handles,fontsize=9,frameon=False,loc='best')
 fig.text(.06,-.075,'每根真实分布RC作用于同一C/U的128位接口，取最差路径；不是当前A/B版本自身的系统STA。\n空心点的时序可能含库外推，仅作诊断；正setup不代表电气通过。邻线静止、TT库、父层理想时钟，块内时钟树传播。',fontsize=9,color='#526070')
 fig.savefig(out/('length-'+metric+'.png'),dpi=190,bbox_inches='tight');fig.savefig(out/('length-'+metric+'.svg'),bbox_inches='tight');plt.close(fig)
(out/'source.json').write_text(json.dumps({'file':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'cases':1292,'distinct_route_cases':646,'scope':'same accepted C/U replay fixture; not actual A/B system STA'},indent=2))
print(out)
