"""Actual before/after pin-metal loss; proposed repair is never drawn as routed."""
from pathlib import Path
import csv,gzip,hashlib,io,json,re
import expand_candidates as expand


def read(path):return json.loads(gzip.decompress(path.read_bytes()))


def plot(terminal,out):
    terminal,out=Path(terminal),Path(out)
    root=terminal/'owned-cap-spacing-diagnosis-r01';native=terminal/'llsys-owned-cap-access-r01'
    if not (root/'execution.json.gz').exists() or not (native/'execution.json.gz').exists():return None
    q=read(root/'execution.json.gz');n=read(native/'execution.json.gz')
    assert q['actual_old_pin_metal_removed_DBU2']==19600 and n['fresh_DRC_count']==2
    assert q['all_actual_target_WIRE_VIA_and_internal_endpoints_exact'] and n['all_725253_original_WIRE_VIA_rectangle_multisets_identical']
    versions=[]
    for label in ['before','after']:
        raw=gzip.decompress((root/(label+'_failed_nets.tsv.gz')).read_bytes())
        assert hashlib.sha256(raw).hexdigest()==q['files'][label+'_failed_nets.tsv']['sha256']
        versions.append(list(csv.DictReader(io.StringIO(raw.decode()),delimiter='\t')))
    drc=gzip.decompress((native/'independent.drc.gz').read_bytes()).decode()
    markers=[tuple(map(float,m)) for m in re.findall(r'bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer metal5',drc)]
    assert len(markers)==2 and drc.count('violation type: Metal Spacing')==2
    box=lambda r:[int(r[k]) for k in ['x0','y0','x1','y1']]
    pins=[box(next(r for r in rows if r['kind']=='BTERM')) for rows in versions]
    assert pins==q['old_new_actual_M5_pin_boxes_DBU']
    old=pins[0];physical=[box(r) for r in versions[1] if r['layer']=='metal5' and r['kind'] in ['WIRE','VIA']]
    clips=[(max(b[0],old[0]),max(b[1],old[1]),min(b[2],old[2]),min(b[3],old[3])) for b in physical]
    clips=[b for b in clips if b[0]<b[2] and b[1]<b[3]]
    xs=sorted({old[0],old[2]}|{v for b in clips for v in [b[0],b[2]]})
    ys=sorted({old[1],old[3]}|{v for b in clips for v in [b[1],b[3]]})
    lost=[]
    for x0,x1 in zip(xs,xs[1:]):
        for y0,y1 in zip(ys,ys[1:]):
            if not any(b[0]<=x0 and b[2]>=x1 and b[1]<=y0 and b[3]>=y1 for b in clips):lost.append((x0,y0,x1,y1))
    assert sum((b[2]-b[0])*(b[3]-b[1]) for b in lost)==19600
    plt=expand.legacy.plt;Rectangle=expand.legacy.Rectangle
    fig,axes=plt.subplots(2,2,figsize=(12.5,11.5));fig.subplots_adjust(left=.08,right=.96,top=.82,bottom=.20,hspace=.34,wspace=.23)
    fig.text(.045,.95,'LL SYSTEM | 接点移动后的同网间距失败',fontsize=21,weight='bold',color='#17283c')
    fig.text(.045,.906,'bit_433：实际前后各 71 行几何；WIRE / VIA / 内部端点一致，BPin 的位置与占用发生变化。',fontsize=10.5,color='#56677d')
    centers=[((p[0]+p[2])/4000.,(p[1]+p[3])/4000.) for p in pins]
    cx=sum(p[0] for p in centers)/2;cy=sum(p[1] for p in centers)/2
    colors={'metal1':'#b0bcc6','metal2':'#8dafb6','metal3':'#96bca3','metal4':'#b6c599','metal5':'#2a87a8','metal6':'#8d72ae','metal7':'#b6956d'}
    for col,rows in enumerate(versions):
        for row in [0,1]:
            ax=axes[row,col]
            for layer,color in colors.items():
                for r in rows:
                    if r['layer']!=layer or r['kind'] not in ['WIRE','VIA']:continue
                    x0,y0,x1,y1=[v/2000. for v in box(r)]
                    ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor=color,edgecolor=color,linewidth=.4,alpha=.63 if layer=='metal5' else .25))
            x0,y0,x1,y1=[v/2000. for v in pins[col]]
            ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#f1c865',edgecolor='#17283c',linewidth=1.1,zorder=8))
            if col==1:
                a,b,c,d=[v/2000. for v in old];ax.add_patch(Rectangle((a,b),c-a,d-b,fill=False,edgecolor='#6a6a6a',linestyle='--',linewidth=1,zorder=9))
                for b in lost:
                    a,c,d,e=[v/2000. for v in b];ax.add_patch(Rectangle((a,c),d-a,e-c,facecolor='#f6d8dc',edgecolor='#bd3b53',hatch='xxx',linewidth=.7,zorder=10))
                for a,b,c,d in markers:ax.add_patch(Rectangle((a,b),c-a,d-b,fill=False,edgecolor='#c24f46',linewidth=1.1,zorder=11))
            if row==0:
                ax.set_xlim(cx-2.4,cx+2.4);ax.set_ylim(cy-2.4,cy+2.4)
                ax.annotate('原 M5 pin' if col==0 else '当前 M5 pin：同网原 via 帽',xy=centers[col],xytext=(centers[col][0]+.25,centers[col][1]+.65),fontsize=8,color='#56677d',arrowprops={'arrowstyle':'->','color':'#56677d','lw':.8},zorder=20)
            else:
                ax.set_xlim(centers[0][0]-.7,centers[0][0]+.7);ax.set_ylim(centers[0][1]-.7,centers[0][1]+.7)
                if col==1:ax.text(.03,.96,'当前新 pin 已移出此放大窗',transform=ax.transAxes,ha='left',va='top',fontsize=8,color='#56677d')
            ax.set_aspect('equal');ax.grid(alpha=.13);ax.set_axisbelow(True);ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=8)
            ax.set_xlabel('x (μm)',fontsize=9);ax.set_ylabel('y (μm)',fontsize=9)
            ax.set_title(('原四 tip 实际源 | native 0' if col==0 else '实际 10261-pin ECO | native 2')+('\n同范围 4.8 × 4.8 μm' if row==0 else '\n旧接点同坐标 1.4 × 1.4 μm'),fontsize=10.5,color='#17283c')
    handles=[Rectangle((0,0),1,1,facecolor=colors['metal5'],alpha=.63),Rectangle((0,0),1,1,facecolor='#f1c865',edgecolor='#17283c'),Rectangle((0,0),1,1,fill=False,edgecolor='#6a6a6a',linestyle='--'),Rectangle((0,0),1,1,facecolor='#f6d8dc',edgecolor='#bd3b53',hatch='xxx'),Rectangle((0,0),1,1,fill=False,edgecolor='#c24f46')]
    fig.legend(handles,['原生同网 M5 金属','实际 0.14 μm pin','旧 pin 参考轮廓（非当前金属）','移走后缺少的金属：0.0049 μm²','两项原生间距 marker'],loc='lower left',bbox_to_anchor=(.05,.105),ncol=2,frameon=False,fontsize=8.5)
    fig.text(.045,.025,'仅显示该网真实矩形；未绘异网 / PG / OBS 不能视为空闲。所有尺寸按 DBU，无示意连线路径。\n虚线框是旧 pin 位置参考，不是当前金属。小线尾延长 0.115 μm 是待实施修复，不能据图宣布 DRC 通过。\n原层 / pin 尺寸 / 逐 bit 连接保持；本轮 max / min slack −3.909029 / −0.587515 ns，完整物理与系统资格未完成。',fontsize=9,color='#56677d',linespacing=1.6)
    assets=out/'assets';assets.mkdir(exist_ok=True)
    fig.savefig(assets/'llsys_owned_cap_spacing.png',dpi=180)
    svg=assets/'llsys_owned_cap_spacing.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-owned-cap-spacing'}):fig.savefig(svg,metadata={'Date':None})
    svg.write_text('\n'.join(s.rstrip() for s in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    meta={'scope':'ACTUAL_BEFORE_AFTER_PIN_METAL_LOSS_NOT_IMPLEMENTED_REPAIR','full_qualification':False,
          'diagnosis_receipt_SHA256':hashlib.sha256(gzip.decompress((root/'execution.json.gz').read_bytes())).hexdigest(),
          'source_native_receipt_SHA256':hashlib.sha256(gzip.decompress((native/'execution.json.gz').read_bytes())).hexdigest(),
          'actual_rows_before_after':[71,71],'actual_pin_boxes_DBU':pins,'native_DRC_before_after':[0,2],
          'actual_lost_metal_DBU2':19600,'lost_metal_rectangles_DBU':lost,'actual_native_M5_spacing_markers_um':markers,
          'actual_target_WIRE_VIA_internal_endpoints_exact':True,'proposed_repair_implemented':False}
    (out/'data/llsys_owned_cap_spacing_figure.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return meta


if __name__=='__main__':
    import sys
    plot(sys.argv[1],sys.argv[2])
