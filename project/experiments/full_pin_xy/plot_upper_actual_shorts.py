"""Source-bound actual M11 wire/via10 landing shorts, not proposed routes."""
from pathlib import Path
import csv,gzip,hashlib,io,json,re
import expand_candidates as expand


def plot(snapshot,out):
    folder=Path(snapshot)/'upper_branch_repair/r01/llaccel';receipt=folder/'execution.json.gz'
    if not receipt.exists():return None
    q=json.loads(gzip.decompress(receipt.read_bytes()))
    assert q['fresh_DRC_count']==10 and q['all_closed_sources_unchanged'] and q['all_770_branch_geometry']['pass']
    data=gzip.decompress((folder/'branch_access.tsv.gz.gz').read_bytes())
    assert hashlib.sha256(data).hexdigest()==q['files']['branch_access.tsv.gz']['sha256']
    rows=list(csv.DictReader(io.StringIO(gzip.decompress(data).decode()),delimiter='\t'))
    drc=gzip.decompress((folder/'independent.drc.gz').read_bytes())
    assert hashlib.sha256(drc).hexdigest()==q['files']['independent.drc']['sha256']
    assert len(re.findall(r'^violation type: Short$',drc.decode(),re.M))==2
    native_markers={}
    for m in re.finditer(r'violation type: Short\s+srcs: net:adapter_edge_(\d+) net:adapter_edge_(\d+)\s+bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer (\w+)',drc.decode()):
        assert m[7]=='metal11';native_markers[frozenset([int(m[1]),int(m[2])])]=list(map(float,[m[3],m[4],m[5],m[6]]))
    assert len(native_markers)==2
    box=lambda r:[int(r[k])/2000 for k in ['x0','y0','x1','y1']]
    cases=[]
    for fixed,link,kind,cross,wire in [(243,'via_46','VIA',248,'wire_33'),(199,'wire_14','WIRE',206,'wire_14')]:
        cap=[r for r in rows if r['net']=='src['+str(fixed)+']' and r['kind']==kind and r['layer']=='metal11' and r['link']==link]
        hit=[r for r in rows if r['net']=='src['+str(cross)+']' and r['kind']=='WIRE' and r['layer']=='metal11' and r['link']==wire]
        assert len(cap)==len(hit)==1
        via=[r for r in rows if r['net']==cap[0]['net'] and r['kind']=='VIA' and r['link']==link]
        if kind=='VIA':assert {r['layer'] for r in via}=={'via10','metal10','metal11'}
        a,b=box(cap[0]),box(hit[0]);intersection=[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
        if kind=='VIA':assert all(abs(intersection[k]-a[k])<1e-8 for k in range(4))
        assert abs((intersection[2]-intersection[0])*(intersection[3]-intersection[1])-.64)<1e-8
        assert all(abs(x-y)<1e-8 for x,y in zip(intersection,native_markers[frozenset([fixed,cross])]))
        center=[(intersection[0]+intersection[2])/2,(intersection[1]+intersection[3])/2]
        cases.append({'reference_branch':fixed,'reference_kind':kind,'wire_branch':cross,'actual_reference_link':link,'actual_wire_link':wire,
          'actual_overlap_box_um':intersection,'actual_overlap_area_um2':.64,'center_um':center,
          'via10_landing_in_actual_overlap':kind=='VIA','original_rows':(via if kind=='VIA' else cap)+hit})
    plt,R=expand.legacy.plt,expand.legacy.Rectangle
    fig,axes=plt.subplots(2,2,figsize=(13.5,11.2))
    fig.subplots_adjust(left=.075,right=.96,top=.80,bottom=.22,hspace=.35,wspace=.21)
    fig.text(.045,.955,'M11/M12 适配接入 | 两处实际异网短接',fontsize=21,weight='bold',color='#17283c')
    fig.text(.045,.905,'r01 历史闭合 helper：10 项独立 native 报项 = 2 Short + 8 间距；只定位两处 Short。\n真实 770 支路 / 1540 接点已连通，但异网隔离失败；后续修复结果单列，不覆盖本图源。',fontsize=11,color='#56677d',linespacing=1.6)
    for col,c in enumerate(cases):
        cx,cy=c['center_um'];fixed='src['+str(c['reference_branch'])+']';cross='src['+str(c['wire_branch'])+']'
        for row,span in enumerate([16.,3.2]):
            ax=axes[row,col]
            for r in sorted(rows,key=lambda r:r['net'] in [fixed,cross]):
                if r['layer'] not in ['metal11','metal12'] or r['kind'] not in ['WIRE','VIA']:continue
                x0,y0,x1,y1=box(r)
                if x0>cx+span/2 or x1<cx-span/2 or y0>cy+span/2 or y1<cy-span/2:continue
                color='#4187b7' if r['net']==fixed else '#db9640' if r['net']==cross else '#a4aeb9'
                selected=r['net'] in [fixed,cross]
                ax.add_patch(R((x0,y0),x1-x0,y1-y0,facecolor=color if r['layer']=='metal11' else 'none',
                  edgecolor=color,hatch='..' if r['layer']=='metal12' else None,alpha=.62 if selected else .22,linewidth=.65 if selected else .3))
            a=c['actual_overlap_box_um'];ax.add_patch(R((a[0],a[1]),a[2]-a[0],a[3]-a[1],fill=False,edgecolor='#c64242',hatch='///',linewidth=1.4,zorder=20))
            ax.set_xlim(cx-span/2,cx+span/2);ax.set_ylim(cy-span/2,cy+span/2);ax.set_aspect('equal')
            ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=8);ax.grid(alpha=.12);ax.set_axisbelow(True)
            ax.set_title(('实际 16 × 16 μm 区域' if row==0 else '同倍率 3.2 × 3.2 μm 放大')+' | '+str(c['reference_branch'])+' / '+str(c['wire_branch']),fontsize=10.5,color='#17283c')
            ax.set_xlabel('x (μm)',fontsize=9);ax.set_ylabel('y (μm)',fontsize=9)
            if row==0:ax.annotate('异网 M11 导线覆盖\nvia10 的 M11 帽' if c['via10_landing_in_actual_overlap'] else '两条异网 M11 导线\n在同层实际交叉',xy=(cx,cy),xytext=(cx-7,cy+5),fontsize=8,color='#a22f36',arrowprops={'arrowstyle':'->','color':'#a22f36','lw':.8},zorder=30)
    handles=[R((0,0),1,1,fc='#4187b7',alpha=.62),R((0,0),1,1,fc='#db9640',alpha=.62),R((0,0),1,1,fc='#a4aeb9',alpha=.25),R((0,0),1,1,fill=False,ec='#777',hatch='..'),R((0,0),1,1,fill=False,ec='#c64242',hatch='///')]
    fig.legend(handles,['参考支路（含真实落脚）','发生交叠的另一支路','其他实际适配金属','M12 实际矩形（描边）','0.8 × 0.8 μm 实际交叠'],loc='lower left',bbox_to_anchor=(.045,.115),ncol=3,frameon=False,fontsize=9)
    fig.text(.045,.025,'所有金属来自真实 dbWire/via 矩形；红框按真实交叠尺寸绘制，箭头不是布线。两列同尺度、同放大倍率。\nvia10 连接 M10→M11；所示帽为原生 0.8 μm 研究接入几何，原叶块 M5/M6 pin 未绘且没有升层。\n仅绘局部适配金属，未绘下层 PG/OBS 不代表空闲；不是完整规则/冻结/RC/STA 或系统收益证明。\n原 10 项失败保留；新残余涉网修复与 guard15 各自验证，不把每网连通当异网隔离通过。',fontsize=9.2,color='#56677d',linespacing=1.6)
    assets=Path(out)/'assets';fig.savefig(assets/'upper_actual_via10_shorts.png',dpi=180)
    svg=assets/'upper_actual_via10_shorts.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-actual-upper-via10-shorts'}):fig.savefig(svg,metadata={'Date':None})
    svg.write_text('\n'.join(s.rstrip() for s in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    result={'scope':'ACTUAL_CLOSED_ADAPTER_WIRE_VIA10_INTERSECTIONS_NOT_PROPOSED_ROUTES','full_qualification':False,
      'source_receipt_SHA256':hashlib.sha256(gzip.decompress(receipt.read_bytes())).hexdigest(),
      'source_branch_geometry_SHA256':hashlib.sha256(data).hexdigest(),'source_native_DRC_SHA256':hashlib.sha256(drc).hexdigest(),
      'source_variant':'upper_branch_repair/r01/llaccel','native_total_findings':10,'actual_short_count':2,'DBU_per_um':2000,'cases':cases,
      'both_intersection_boxes_exactly_match_native_DRC_markers':True,
      'not_verified':['Complete system function','Qualified lower freeze','Full applicable rules','RC/STA','System benefit']}
    (Path(out)/'data/upper_actual_via10_shorts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result
