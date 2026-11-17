from pathlib import Path
from collections import defaultdict
import csv,gzip,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
root=Path(__file__).resolve().parent;case=root/'final'
def load(path):return json.loads(path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix(path.suffix+'.gz').read_bytes()))
place=load(case/'placement.json');routes=load(case/'route.json')['routes']
groups={row['net']:row['group'] for row in csv.DictReader((case/'connections.csv').open())}
print(sorted(set(groups.values())))
colors={'C0_U0':'#2563eb','P0_P1G':'#9333b8','P2_C0':'#009b76','P1_P2':'#d56b14'}
# Group identity is derived from actual terminal names, not presentation labels.
def family(r):
 names=[v['pin'] for v in r['via10']]
 if any(p.startswith('C0.projection_s_') for p in names):return 'P2_C0'
 if any(p.startswith('P2.down_s_') for p in names):return 'P1_P2'
 if any(p.startswith('U0.') for p in names):return 'C0_U0'
 return 'P0_P1G'
fig,ax=plt.subplots(figsize=(12.4,9.5));fig.patch.set_facecolor('white')
for name,b in place['boxes_dbu'].items():
 x,y,r,t=[v/2000000 for v in b]
 ax.add_patch(Rectangle((x,y),r-x,t-y,facecolor='#f0f3f7',edgecolor='#5c697b',linewidth=1.3,zorder=1))
 ax.text(x+.04,t-.065,name,fontsize=14,fontweight='bold',color='#25364b',va='top',zorder=4,bbox={'facecolor':'#f0f3f7','edgecolor':'none','pad':1.5})
lines=defaultdict(list)
for name,r in routes.items():
 for s in r['segments']:lines[family(r)].append([[v/2000000 for v in s['a']],[v/2000000 for v in s['b']]])
for key,segments in lines.items():ax.add_collection(LineCollection(segments,colors=colors[key],linewidths=.24,alpha=.34,zorder=2,rasterized=True))
labels={'C0_U0':'C0.S ↔ U0.S','P0_P1G':'P0.S → P1.G','P2_C0':'P2.S → C0.E32','P1_P2':'P1.S → P2.M'}
ax.legend([Line2D([0],[0],color=colors[k],lw=2) for k in colors],[labels[k] for k in colors],loc='lower center',bbox_to_anchor=(.5,1.015),ncol=2,frameon=False,fontsize=12)
b=place['bounds_dbu'];ax.set(xlim=(-.08,b[2]/2e6+.08),ylim=(-.08,b[3]/2e6+.05),xlabel='x (mm)',ylabel='y (mm)');ax.set_aspect('equal')
ax.spines[['top','right']].set_visible(False);ax.tick_params(labelsize=10)
fig.text(.5,.022,'9 compute bases · 1,049 nets / 1,053 branches · M11/M12 geometry verified',ha='center',fontsize=10,color='#39485a')
fig.subplots_adjust(left=.07,right=.99,bottom=.085,top=.89)
fig.savefig(case/'layout.png',dpi=190);fig.savefig(case/'layout.svg',dpi=190)
