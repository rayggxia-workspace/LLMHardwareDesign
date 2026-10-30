"""Actual native M5 restore before/after; all rectangles source-hash bound."""
from pathlib import Path
from collections import Counter
import csv,gzip,hashlib,io,json,re
import expand_candidates as expand

def read(p):return json.loads(gzip.decompress(p.read_bytes()))
def plot(terminal,out):
    terminal,out=Path(terminal),Path(out);before=terminal/'owned-cap-spacing-diagnosis-r01';after=terminal/'llsys-owned-restored-views-r01';repair=terminal/'owned-cap-wire-restore-r01'
    if not all((p/'execution.json.gz').exists() for p in [before,after,repair]):return None
    bq,aq,rq=[read(p/'execution.json.gz') for p in [before,after,repair]]
    assert rq['fresh_DRC_count']==0 and aq['source_geometry_sha256']==rq['files']['routed.odb']['sha256'] and aq['all_sources_and_pre_RCX_geometry_unchanged']
    raw=gzip.decompress((before/'after_failed_nets.tsv.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==bq['files']['after_failed_nets.tsv']['sha256']
    versions=[list(csv.DictReader(io.StringIO(raw.decode()),delimiter='\t'))]
    raw=gzip.decompress((after/'actual_restored_bit433.tsv.gz.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==aq['files']['actual_restored_bit433.tsv.gz']['sha256']
    versions.append(list(csv.DictReader(io.StringIO(gzip.decompress(raw).decode()),delimiter='\t')))
    box=lambda r:tuple(int(r[k]) for k in ['x0','y0','x1','y1'])
    key=lambda r:(r['kind'],r['layer'])+box(r)
    others=lambda rows:Counter(key(r) for r in rows if r['kind']!='WIRE')
    assert others(versions[0])==others(versions[1]) and len(versions[0])==len(versions[1])==71
    wires=[Counter(key(r) for r in rows if r['kind']=='WIRE') for rows in versions];removed=list((wires[0]-wires[1]).elements());added=list((wires[1]-wires[0]).elements())
    assert len(removed)==len(added)==1 and removed[0][1]==added[0][1]=='metal5'
    assert list(removed[0][2:])==[3975490,2411220,3975910,2411500] and list(added[0][2:])==[3975490,2411220,3976140,2411500]
    metals=[[box(r) for r in rows if r['layer']=='metal5' and r['kind']!='UNROUTED'] for rows in versions]
    xs=sorted({x for boxes in metals for b in boxes for x in [b[0],b[2]]});ys=sorted({y for boxes in metals for b in boxes for y in [b[1],b[3]]});gain=[];loss=[]
    for x0,x1 in zip(xs,xs[1:]):
        for y0,y1 in zip(ys,ys[1:]):
            occupied=[any(b[0]<=x0 and b[2]>=x1 and b[1]<=y0 and b[3]>=y1 for b in boxes) for boxes in metals]
            if occupied==[False,True]:gain.append((x0,y0,x1,y1))
            if occupied==[True,False]:loss.append((x0,y0,x1,y1))
    assert not loss and sum((b[2]-b[0])*(b[3]-b[1]) for b in gain)==19600
    native=terminal/'llsys-owned-cap-access-r01';drc=gzip.decompress((native/'independent.drc.gz').read_bytes()).decode()
    markers=[tuple(map(float,m)) for m in re.findall(r'bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer metal5',drc)];assert len(markers)==2
    pin=next(box(r) for r in versions[0] if r['kind']=='BTERM');old=bq['old_new_actual_M5_pin_boxes_DBU'][0]
    cnew=((pin[0]+pin[2])/4000,(pin[1]+pin[3])/4000);cold=((old[0]+old[2])/4000,(old[1]+old[3])/4000);center=((cnew[0]+cold[0])/2,(cnew[1]+cold[1])/2)
    plt=expand.legacy.plt;Rectangle=expand.legacy.Rectangle;fig,axes=plt.subplots(2,2,figsize=(12.5,11.5));fig.subplots_adjust(left=.08,right=.96,top=.82,bottom=.19,hspace=.34,wspace=.23)
    fig.text(.045,.95,'LL SYSTEM | 实际线尾修复：native 2 → 0',fontsize=21,weight='bold',color='#17283c')
    fig.text(.045,.906,'bit_433：前后各71行原生几何；10261内部点全部保留，当前pin及全部via不变。',fontsize=10.5,color='#56677d')
    colors={'metal1':'#b0bcc6','metal2':'#8dafb6','metal3':'#96bca3','metal4':'#b6c599','metal5':'#2a87a8','metal6':'#8d72ae','metal7':'#b6956d'}
    for col,rows in enumerate(versions):
        for row in [0,1]:
            ax=axes[row,col]
            for r in rows:
                if r['layer'] not in colors or r['kind'] not in ['WIRE','VIA']:continue
                x0,y0,x1,y1=[v/2000 for v in box(r)];color=colors[r['layer']];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor=color,edgecolor=color,lw=.4,alpha=.63 if r['layer']=='metal5' else .25))
            x0,y0,x1,y1=[v/2000 for v in pin];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#f1c865',edgecolor='#17283c',lw=1.1,zorder=8))
            if col==0:
                for x0,y0,x1,y1 in markers:ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,edgecolor='#c24f46',lw=1.1,zorder=10))
            else:
                for b in gain:
                    x0,y0,x1,y1=[v/2000 for v in b];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#c6e6cf',edgecolor='#31714a',hatch='///',lw=.7,zorder=10))
            c,half=(center,2.4) if row==0 else (cold,.7)
            ax.set_xlim(c[0]-half,c[0]+half);ax.set_ylim(c[1]-half,c[1]+half);ax.set_aspect('equal');ax.grid(alpha=.13);ax.set_axisbelow(True);ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=8)
            ax.set_xlabel('x (μm)',fontsize=9);ax.set_ylabel('y (μm)',fontsize=9);ax.set_title(('实际10261点源 | native 2' if col==0 else '实际单M5恢复 | native 0')+('\n同坐标4.8 × 4.8μm' if row==0 else '\n同坐标1.4 × 1.4μm'),fontsize=10.5,color='#17283c')
    handles=[Rectangle((0,0),1,1,facecolor='#2a87a8',alpha=.63),Rectangle((0,0),1,1,facecolor='#f1c865',edgecolor='#17283c'),Rectangle((0,0),1,1,fill=False,edgecolor='#c24f46'),Rectangle((0,0),1,1,facecolor='#c6e6cf',edgecolor='#31714a',hatch='///')]
    fig.legend(handles,['原生同网M5金属','原位保持的实际0.14μm pin','修复前两项native间距marker','实际补回的导体并集：0.0049μm²'],loc='lower left',bbox_to_anchor=(.05,.10),ncol=2,frameon=False,fontsize=8.5)
    fig.text(.045,.025,'均为真实数据库导出矩形，无示意路径；未绘异网/PG/OBS不能视为空闲。线尾实际延长0.115μm，不是block面积节省。\n原层/尺寸/功能保持，独立native2→0；max/min仍−3.909029/−0.587515ns，完整时序/电气/规则及系统资格未通过。',fontsize=9,color='#56677d',linespacing=1.6)
    assets=out/'assets';fig.savefig(assets/'llsys_actual_wire_restore.png',dpi=180)
    with plt.rc_context({'svg.hashsalt':'issue126-actual-wire-restore'}):fig.savefig(assets/'llsys_actual_wire_restore.svg',metadata={'Date':None})
    p=assets/'llsys_actual_wire_restore.svg';p.write_text('\n'.join(t.rstrip() for t in p.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    meta={'scope':'ACTUAL_NATIVE_SINGLE_M5_RESTORE_BEFORE_AFTER_NOT_CANDIDATE','full_qualification':False,'source_view_receipt_SHA256':hashlib.sha256(gzip.decompress((after/'execution.json.gz').read_bytes())).hexdigest(),'source_actual_ODB_SHA256':aq['source_geometry_sha256'],'actual_rows_before_after':[71,71],'actual_removed_WIRE':removed,'actual_added_WIRE':added,'actual_added_metal_DBU2':19600,'actual_added_metal_rectangles_DBU':gain,'actual_removed_metal_DBU2':0,'current_pin_box_DBU':pin,'actual_vias_and_internal_endpoints_and_pin_exact':True,'native_DRC_before_after':[2,0],'original_negative_STA_preserved':True}
    (out/'data/llsys_actual_wire_restore_figure.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n');return meta
if __name__=='__main__':
    import sys
    plot(sys.argv[1],sys.argv[2])
