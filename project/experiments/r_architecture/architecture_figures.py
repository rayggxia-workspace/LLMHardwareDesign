"""Scientific plots from measured co-simulation rows, no simulated new points."""
from pathlib import Path
import json,csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[3];D=R/'work/YUZE-LU/157';E=D/'evidence/extended';F=D/'figures'

def main():
 F.mkdir(exist_ok=True);data=[]
 for n in [15,38,55]:data+=json.loads((E/f'attempt{n:03d}/results/RESULTS.json').read_text())
 def name(r):return'A0'if r['architecture']==0 else'B'+str(r['capacity'])if r['architecture']==1 else'C-M'if r['architecture']==2 else'C-E'if r['architecture']==3 else'C-N'
 def get(a,w):return next(r for r in data if name(r)==a and r['workload']==w and r['policy']=='cache'and r['status']=='PASS')
 fig,axes=plt.subplots(2,2,figsize=(10,7),constrained_layout=True)
 for mode in [0,1]:
  ax=axes[0,mode]
  for n in [256,1024,2048]:
   ax.plot([256,512,1024,2048],[get('B'+str(c),f'W0-m{mode}-n{n}-t128.bin')['cycles']for c in [256,512,1024,2048]],'o-',label=str(n)+' state words')
  ax.set_title(('GDN'if mode==0 else'SSM')+': one resident context, 128 tokens')
  ax=axes[1,mode]
  for layers in [8,24]:
   ax.plot([256,512,1024,2048],[get('B'+str(c),f'W1-m{mode}-l{layers}-t128.bin')['cycles']for c in [256,512,1024,2048]],'o-',label=str(layers)+' layers, 1024 words each')
  ax.set_title(('GDN'if mode==0 else'SSM')+': context switching, 128 tokens')
 for ax in axes.flat:
  ax.set_xscale('log',base=2);ax.set_yscale('log');ax.set_xticks([256,512,1024,2048],labels=['256','512','1024','2048']);ax.set_xlabel('R-lite local words per bank (8 lanes fixed)');ax.set_ylabel('Measured recurrence cycles');ax.legend(fontsize=8);ax.grid(alpha=.25)
 fig.savefig(F/'capacity-curves.png',dpi=180);plt.close(fig)
 groups=['DRAM latency','DRAM beats','S ports','Wide arithmetic','Finish','Engine / local protocol','Other control']
 def bucket(k):
  if k=='DRAM_latency':return 0
  if k=='DRAM_data':return 1
  if k.startswith('S_'):return 2
  if k in ['E_native','E_wide','M_wide']:return 3
  if k.startswith('finish'):return 4
  if k.startswith(('A0_','R_','M_','E_')):return 5
  return 6
 fig,axes=plt.subplots(1,2,figsize=(12,5),constrained_layout=True);colours=['#8c564b','#e377c2','#ff7f0e','#17becf','#9467bd','#1f77b4','#aaaaaa'];archs=['A0','B256','B1024','B2048','C-E','C-N'];output=[]
 for ax,w in zip(axes,['W0-m0-n2048-t128.bin','W1-m0-l24-t128.bin']):
  bottom=[0.]*len(archs);parts=[]
  for a in archs:
   r=get(a,w);v=[0]*len(groups)
   for k,n in r['stages'].items():v[bucket(k)]+=n
   total=sum(v);assert total==sum(r['stages'].values());parts.append([100*n/total for n in v]);output.extend(dict(workload=w,candidate=a,phase=g,cycles=n,whole_simulation_cycles=total,percent=100*n/total)for g,n in zip(groups,v))
  for i,g in enumerate(groups):
   vals=[p[i]for p in parts];ax.bar(archs,vals,bottom=bottom,label=g,color=colours[i]);bottom=[x+y for x,y in zip(bottom,vals)]
  ax.set_title(w.removesuffix('.bin'));ax.set_ylim(0,100);ax.set_ylabel('Share of all measured cycles (%)');ax.tick_params(axis='x',rotation=20)
 axes[1].legend(loc='upper left',bbox_to_anchor=(1.01,1),fontsize=8)
 fig.savefig(F/'cycle-breakdown.png',dpi=180);plt.close(fig)
 with(D/'CYCLE_BREAKDOWN.csv').open('w',newline='',encoding='utf-8-sig')as f:
  writer=csv.DictWriter(f,list(output[0]));writer.writeheader();writer.writerows(output)
 print(json.dumps(dict(figures=2,stage_rows=len(output))))

if __name__=='__main__':main()
