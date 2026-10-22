"""Render a scientific comparison only from a strictly qualified comparison."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
data=json.loads((HERE/'results/comparison.json').read_text())
inputs=json.loads((HERE/'results/comparison-inputs.json').read_text())['attempts']
out=REPO/'docs/experiments/assets'
out.mkdir(exist_ok=True)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
labels=['Split ACT + MXU','Merged ACT/MXU']
colors=['#3478b9','#f0ab44']
for ax,(private,parent,scale,title,unit) in zip(axes.flat,[
    ('private_leaf_area_um2','parent_stdcell_area_um2',1e3,'Cell area (SRAM included; filler excluded)',r'$10^3\,\mu m^2$'),
    ('private_signal_wire_um','parent_signal_wire_um',1e6,'Signal wire length',r'$10^6\,\mu m$'),
    ('private_signal_vias','parent_signal_vias',1e6,'Signal vias',r'$10^6$ vias')]):
    a=[data['costs'][k][private]/scale for k in ['split','merged']]
    b=[data['costs'][k][parent]/scale for k in ['split','merged']]
    ax.bar(labels,a,color=colors[0],label='Inside blocks',width=.55)
    ax.bar(labels,b,bottom=a,color=colors[1],label='Parent',width=.55)
    for i,(x,y) in enumerate(zip(a,b)):
        ax.text(i,x+y,f'{x+y:.3f}',ha='center',va='bottom')
    ax.set_ylim(0,max(x+y for x,y in zip(a,b))*1.18)
    ax.set_title(title,loc='left',fontsize=10)
    ax.set_ylabel(unit)
    ax.grid(axis='y',alpha=.15)
axes[0,0].legend(frameon=False,fontsize=8)
ax=axes[1,1]
for offset,key,label,color in [(-.16,'complete_setup_ws_ns','Setup',colors[0]),(.16,'complete_hold_ws_ns','Hold',colors[1])]:
    values=[data['costs'][k][key] for k in ['split','merged']]
    x=[i+offset for i in range(2)]
    ax.bar(x,values,width=.3,label=label,color=color)
    for pos,value in zip(x,values):ax.text(pos,value,f'{value:.4f}',ha='center',va='bottom',fontsize=8)
ax.axhline(0,color='#333',linewidth=.7)
ax.set_xticks([0,1],labels)
ax.set_ylabel('ns')
ax.set_title('Complete hierarchical extracted WNS',loc='left',fontsize=10)
ax.legend(frameon=False,fontsize=8)
ax.margins(y=.25)
fig.suptitle('openTPU same-function/resource comparison | 2.5 ns clock',fontsize=13)
fig.savefig(out/'issue-15-ppa.png',dpi=180)
fig.savefig(out/'issue-15-ppa.svg')
plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained')
palette={'u_act':'#68a9cf','u_mxu':'#83bf94','u_merged':'#b39bd1'}
for ax,kind in zip(axes,['split','merged']):
    record=inputs[data['selection']['top_'+kind]]
    meta=record['experiment.json']
    side=meta['die_um'][2]
    ax.add_patch(Rectangle((0,0),side,side,fill=False,linewidth=1.2))
    for path,pg in record['pg_access'].items():
        if not path.startswith('final-pg/'):continue
        name=Path(path).name.split('-pg-')[0]
        a,b,c,d=[v/pg['dbu_per_micron'] for v in pg['instance_bbox_dbu']]
        ax.add_patch(Rectangle((a,b),c-a,d-b,color=palette[name],alpha=.7,ec='#345'))
        ax.text((a+c)/2,(b+d)/2,name.replace('u_','').upper(),ha='center',va='center')
    ax.set(xlim=(-20,side+20),ylim=(-20,side+20),aspect='equal',xlabel=r'$\mu m$',ylabel=r'$\mu m$',title=labels[0 if kind=='split' else 1])
fig.suptitle('Actual final macro boxes | identical die and 1662 external signal pins',fontsize=12)
fig.savefig(out/'issue-15-floorplans.png',dpi=180)
fig.savefig(out/'issue-15-floorplans.svg')
plt.close(fig)
print(out)
