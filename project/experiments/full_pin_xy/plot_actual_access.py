"""Actual ACT pilot routes from native geometry, without schematic connections."""
from pathlib import Path
from collections import Counter
import csv,gzip,json,tkinter
import numpy as np
import expand_candidates as expand

def draw(root,out):
    root=Path(root);out=Path(out);plt=expand.legacy.plt;R=expand.legacy.Rectangle
    from matplotlib.collections import PatchCollection
    interp=tkinter.Tcl();records={}
    for p in ['A','B','C']:
        source=sorted((root/'trial_receipts').glob(f'*/trials/r02/act-{p}/independent-access.tsv.gz'))[-1]
        with gzip.open(source,'rt') as f:records[p]=list(csv.DictReader(f,delimiter='\t'))
    meta=json.loads((root/'act.meta.json').read_text());dims=np.array(meta['die_dbu'])/2000
    fig,axes=plt.subplots(1,3,figsize=(19.5,8.4));fig.subplots_adjust(left=.045,right=.985,top=.80,bottom=.25,wspace=.18)
    fig.text(.04,.95,'ACT | 实际重新接线的局部对照（8-pin pilot）',fontsize=23,weight='bold')
    fig.text(.04,.90,'全块860个信号pin均显示；852个保持原位。彩色实心金属/通孔来自各方案真实路由ODB，没有示意路径。',fontsize=11,color='#56677d')
    colors={f'metal{k}':c for k,c in enumerate(['#c0c9d0','#b9cdd7','#9fb7b8','#85a6b8','#0072b2','#b47bac','#d0ab65','#81926a','#6e8195','#36556e'],1)}
    counts=Counter()
    for ax,plan in zip(axes,['A','B','C']):
        ax.add_patch(R(dims[:2],dims[2]-dims[0],dims[3]-dims[1],fc='#f7f9fb',ec='#52667d',lw=1.1))
        for m in meta['macros']:
            b=np.array(m['bbox_dbu'])/2000;ax.add_patch(R(b[:2],b[2]-b[0],b[3]-b[1],fc='#d9dee5',ec='#94a3b2',lw=.6))
        for layer in sorted({r['layer'] for r in records[plan]},key=lambda x:('via' in x,x)):
            patches=[]
            for r in records[plan]:
                if r['layer']!=layer or r['kind'] in ['ITERM','BTERM']:continue
                bb=np.array([int(r[k]) for k in ['x0','y0','x1','y1']])/2000
                patches.append(R(bb[:2],bb[2]-bb[0],bb[3]-bb[1]))
                if layer.startswith('via'):counts[plan,layer,round(bb[2]-bb[0],6),round(bb[3]-bb[1],6)]+=1
            if patches:ax.add_collection(PatchCollection(patches,facecolor=colors.get(layer,'#17283c'),edgecolor='none',alpha=.8,zorder=3))
        pinfile=sorted((root/'trial_receipts').glob(f'*/trials/r02/act-{plan}/after.pins.tsv.gz'))[-1]
        with gzip.open(pinfile,'rt') as f:pins=[r for line in f if (r:=interp.splitlist(line))[2] not in ['POWER','GROUND']]
        assert len(pins)==860
        xy=np.array([[(int(r[5])+int(r[7]))/4000,(int(r[6])+int(r[8]))/4000] for r in pins]);ax.scatter(xy[:,0],xy[:,1],s=3,c='#9eabb8',zorder=4)
        for r in records[plan]:
            if r['kind']=='BTERM':
                bb=np.array([int(r[k]) for k in ['x0','y0','x1','y1']])/2000
                ax.scatter((bb[0]+bb[2])/2,(bb[1]+bb[3])/2,s=28,marker='o' if r['layer']=='metal5' else 's',facecolor='white',edgecolor=colors[r['layer']],lw=1,zorder=6)
        ax.set_xlim(-6,dims[2]+6);ax.set_ylim(-6,dims[3]+6);ax.set_aspect('equal');ax.set_xlabel('X (μm)');ax.set_ylabel('Y (μm)')
        ax.set_title({'A':'A. 原始实际布线','B':'B. 8-pin 贴边多排 · actual trial','C':'C. 8-pin 内部二维 · actual trial'}[plan],loc='left',fontsize=11,weight='bold')
        ax.text(0,-.15,'M5蓝 / M6紫；其余层淡色；cut层深色\n独立native DRC、RC/STA与连通回执另列',transform=ax.transAxes,fontsize=9,color='#56677d')
    fig.text(.04,.07,'圈/方框只强调8个所选BTerm位置，不是通孔大小。实际金属和cut矩形按ODB原尺寸绘制，各层尺寸/数量见 act_actual_access_via_geometry.csv；\nvia1–via9分别衔接M1–M2至M9–M10，图中只显示实际使用项，未统一外扩。852个其他pin未迁移，不能把本图称为全C已实现。\n实心路径不同于端点图的虚线；本图不证明父层可接入、GDS/LVS或完整工艺签核。',fontsize=10,color='#56677d')
    for ext in ['png','svg']:fig.savefig(out/'assets'/f'act_actual_access.{ext}',dpi=180)
    plt.close(fig)
    with (out/'data/act_actual_access_via_geometry.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['plan','cut_layer','cut_width_um','cut_height_um','actual_cut_rectangles','source'])
        for (p,l,x,y),n in sorted(counts.items()):w.writerow([p,l,x,y,n,'Actual routed ODB via boxes; no assumed spacing/keepout'])
if __name__=='__main__':
    import sys;draw(*sys.argv[1:3])
