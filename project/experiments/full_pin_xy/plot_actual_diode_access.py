"""Actual source-specific GDS marker bounds and new real diode placements.

Marker bounds are visual ROIs, never a net-assignment or routed-path substitute.
Overview symbols have display sizes; the inset draws native placement bboxes.
"""
from pathlib import Path
import csv,gzip,hashlib,io,json
from matplotlib.patches import Rectangle
import expand_candidates as expand


def plot(snapshot,out):
    snapshot,out=Path(snapshot),Path(out)
    folder=snapshot/'antenna_incremental_eco/r01/gemm-C'
    p=folder/'execution.json.gz'
    if not p.exists():return None
    read=lambda p:gzip.decompress(p.read_bytes())
    proof=json.loads(read(p))
    if proof.get('native_returncodes',{}).get('implementation')!=0:return None
    assert read(folder/'before.pins.tsv.gz')==read(folder/'after.pins.tsv.gz')
    assert read(folder/'before.pdn.tsv.gz')==read(folder/'after.pdn.tsv.gz')
    assert read(folder/'before.die.tsv.gz')==read(folder/'after.die.tsv.gz')
    diodes=list(csv.DictReader(io.StringIO(read(folder/'diode_placed.tsv.gz').decode()),delimiter='\t'))
    receivers=list(csv.DictReader(io.StringIO(read(folder/'diode_receivers.tsv.gz').decode()),delimiter='\t'))
    assert len(diodes)==len(receivers)==22 and len({d['net'] for d in diodes})==22
    markers=json.loads(read(snapshot/'post_diode_netmap/cap-r01/marker_net_correlations.json.gz'))
    assert len(markers)==37 and {m['native_net'] for m in markers}=={d['net'] for d in diodes}
    die=[int(n)/2000 for n in read(folder/'before.die.tsv.gz').decode().split()];assert len(die)==4
    pins=[]
    for line in read(folder/'before.pins.tsv.gz').decode().splitlines():
        q=line.split()
        if q[2] in ['POWER','GROUND']:continue
        b=[int(n)/2000 for n in q[-4:]];pins.append((q[-5],(b[0]+b[2])/2,(b[1]+b[3])/2))
    assert len(pins)==3753
    plt=expand.legacy.plt;fig,axes=plt.subplots(1,3,figsize=(16,7),gridspec_kw={'width_ratios':[1,1,1.1]})
    fig.subplots_adjust(left=.055,right=.975,bottom=.27,top=.76,wspace=.30)
    fig.text(.035,.94,'GEMM 真实接入 | 37项原GDS报项 → 22条实际网',fontsize=20,weight='bold',color='#17283c')
    fig.text(.035,.865,'左：636diode+两换型版原deck几何；中/右：定向增加22个ANTENNA_X1后的实际放置。两个物理来源独立记录。',fontsize=10,color='#56677d')
    colors={'metal5':'#328aaa','metal6':'#e5aa4c'}
    for ax,title in zip(axes[:2],['原GDS：37个实际多边形的bbox','新增接入：22个实际diode位置']):
        ax.set_facecolor('#f6f8fa');ax.add_patch(Rectangle(die[:2],die[2]-die[0],die[3]-die[1],fill=False,edgecolor='#56677d',lw=1))
        for layer in sorted(colors):
            ps=[p for p in pins if p[0]==layer];ax.scatter([p[1] for p in ps],[p[2] for p in ps],s=2,c=colors[layer],alpha=.35,linewidths=0,label=layer+'原pin')
        ax.set_xlim(die[0]-15,die[2]+15);ax.set_ylim(die[1]-15,die[3]+15);ax.set_aspect('equal');ax.set_xlabel('x (μm)');ax.set_ylabel('y (μm)');ax.set_title(title,fontsize=11)
    for m in markers:
        x0,y0,x1,y1=m['source_polygon_bbox_um']
        axes[0].add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,edgecolor='#c85853',lw=.75,alpha=.85))
    axes[1].scatter([int(d['x_dbu'])/2000 for d in diodes],[int(d['y_dbu'])/2000 for d in diodes],marker='x',s=32,color='#c85853',lw=1.2)
    axes[0].legend(loc='upper left',frameon=True,fontsize=8)
    d=next(d for d in diodes if d['orientation']=='R0');r=next(r for r in receivers if r['diode']==d['diode'])
    cell=[int(d['x_dbu'])/2000,int(d['y_dbu'])/2000,int(d['width_dbu'])/2000,int(d['height_dbu'])/2000]
    receiver=[int(n)/2000 for n in r['receiver_bbox_dbu'].split()]
    axes[2].add_patch(Rectangle(cell[:2],cell[2],cell[3],facecolor='#e5aa4c',edgecolor='#b47428',alpha=.8,label='新diode实际LEF placement bbox'))
    axes[2].add_patch(Rectangle(receiver[:2],receiver[2]-receiver[0],receiver[3]-receiver[1],facecolor='#328aaa',edgecolor='#256680',alpha=.6,label='原真实receiver instance bbox'))
    x0=min(cell[0],receiver[0])-.4;x1=max(cell[0]+cell[2],receiver[2])+.4
    y0=min(cell[1],receiver[1])-.45;y1=max(cell[1]+cell[3],receiver[3])+.45
    axes[2].set_xlim(x0,x1);axes[2].set_ylim(y0,y1);axes[2].set_aspect('equal');axes[2].set_xlabel('x (μm)');axes[2].set_ylabel('y (μm)')
    axes[2].set_title(d['net']+' 实际局部',fontsize=11)
    axes[2].text(.03,.97,'diode '+str(cell[2])+' × '+str(cell[3])+' μm\nR0 / 真实master尺寸',transform=axes[2].transAxes,va='top',fontsize=8,color='#56677d')
    axes[2].legend(loc='lower left',bbox_to_anchor=(-.10,-.18),frameon=False,fontsize=8)
    for ax in axes:ax.grid(alpha=.15);ax.set_axisbelow(True)
    fig.text(.035,.13,'总览：pin点和diode十字为显示符号，尺寸不代表pin / via占地；红框为原GDS多边形bbox，逐网归属来自精确多边形交集。\n局部：按真实DBU绘制LEF placement bbox，非GDS轮廓或pin / via几何。22个新单元另计master面积5.852μm²，block外框不变。\n原3753个信号pin的XY/层/尺寸及PG保持；新版本fresh DRC、全网/数字合同及严格GDS分别看回执，不能从这张图推断通过。',fontsize=9,color='#56677d',linespacing=1.7)
    assets=out/'assets';fig.savefig(assets/'gemm_real_diode_access.png',dpi=180)
    svg=assets/'gemm_real_diode_access.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-real-diode-access'}):fig.savefig(svg,metadata={'Date':None})
    svg.write_text('\n'.join(s.rstrip() for s in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    result={'scope':'SOURCE_SPECIFIC_REAL_GDS_BOUNDS_AND_ACTUAL_DIODE_CELL_PLACEMENTS_NOT_ROUTE_OR_DRC_PASS',
      'old_GDS_findings':37,'new_actual_diodes':22,'unchanged_original_signal_pins':3753,'new_master_bbox_area_um2':sum(int(d['width_dbu'])*int(d['height_dbu'])/4e6 for d in diodes),
      'actual_selected_receiver':r,'actual_selected_diode':d,'full_qualification':False,
      'source_files_uncompressed_SHA256':{str(q.relative_to(snapshot)):hashlib.sha256(read(q)).hexdigest() for q in [p,folder/'diode_placed.tsv.gz',folder/'diode_receivers.tsv.gz',folder/'before.pins.tsv.gz']}}
    (out/'data/gemm_real_diode_access.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result
