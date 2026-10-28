"""Actual M6 routing/OBS comparison; parent access remains separately unknown."""
from pathlib import Path
import csv,gzip,hashlib,io,json
import expand_candidates as expand


def rows(p):return list(csv.DictReader(io.StringIO(gzip.decompress(p.read_bytes()).decode()),delimiter='\t'))


def plot(snapshot,out):
    snapshot=Path(snapshot);out=Path(out);folder=snapshot/'pin_escape_views/r01/mxu-C';p=folder/'execution.json.gz'
    if not p.exists():return None
    proof=json.loads(gzip.decompress(p.read_bytes()))
    assert proof['native_export_returncode']==proof['fresh_model_read_returncode']==0 and proof['matching_all_signal_model_pins']==2172
    ctx=proof['actual_M6_OBS_context'];assert not ctx['M6_polygon_lines_not_silently_treated_as_empty']
    compressed=gzip.decompress((folder/'target_pin_access.tsv.gz.gz').read_bytes());assert hashlib.sha256(compressed).hexdigest()==proof['files']['target_pin_access.tsv.gz']['sha256']
    new=list(csv.DictReader(io.StringIO(gzip.decompress(compressed).decode()),delimiter='\t'));assert {r['net'] for r in new}=={'act_data[12]'}
    oldfolder=snapshot/'parent_region_audit/r01';old=rows(oldfolder/'leaf_costed_ECO.tsv.gz');parent=rows(oldfolder/'parent.tsv.gz')
    oldproof=json.loads(gzip.decompress((oldfolder/'execution.json.gz').read_bytes()));dx,dy=oldproof['sources']['leaf_costed_ECO']['to_parent_translation_um']
    oldobs=[[int(r[k])/2000-d for k,d in zip(['x0','y0','x1','y1'],[dx,dy,dx,dy])] for r in parent if r['layer']=='metal6' and r['kind']=='MACRO_OBS' and r['owner']=='u_macro']
    pin=ctx['original_pin_box_um'];oldpin=[r for r in old if r['kind']=='BTERM' and r['net']=='act_data[12]' and r['layer']=='metal6']
    assert len(oldpin)==1 and all(abs(int(oldpin[0][k])/2000-v)<1e-8 for k,v in zip(['x0','y0','x1','y1'],pin))
    def overlap_area(rectangles):
        clipped=[]
        for r in rectangles:
            b=[max(pin[0],r[0]),max(pin[1],r[1]),min(pin[2],r[2]),min(pin[3],r[3])]
            if b[2]>b[0] and b[3]>b[1]:clipped.append([round(x*2000) for x in b])
        xs=sorted({x for r in clipped for x in [r[0],r[2]]});total=0
        for a,b in zip(xs,xs[1:]):
            intervals=sorted((r[1],r[3]) for r in clipped if r[0]<=a and r[2]>=b);length=0;end=None
            for c,d in intervals:
                if end is None or c>end:length+=d-c;end=d
                elif d>end:length+=d-end;end=d
            total+=(b-a)*length
        return total/4e6
    via_links={r['link'] for r in new if r['kind']=='VIA' and r['layer']=='via5'};assert len(via_links)==1
    landing=[r for r in new if r['kind']=='VIA' and r['layer']=='metal6' and r['link'] in via_links];assert len(landing)==1
    b=[int(landing[0][k])/2000 for k in ['x0','y0','x1','y1']];xy=[(b[0]+b[2])/2,(b[1]+b[3])/2]
    result={'scope':'REAL_M6_ROUTING_AND_OBS_CONTEXT_NOT_NEW_PARENT_ACCESS_OR_PIN_MIGRATION',
      'original_pin_box_um':pin,'before_OBS_intersection_pin_union_area_um2':overlap_area(oldobs),
      'after_OBS_intersection_pin_union_area_um2':overlap_area(ctx['actual_M6_OBS_rectangles_um']),
      'actual_existing_via5_M6_landing_box_um':b,'actual_existing_via5_center_um':xy,
      'existing_via_is_next_XY_research_region_not_a_migrated_pin':True,'new_parent_validation':'NOT_EXECUTED',
      'view_source_routed_ODB_SHA256':proof['source_geometry_sha256'],'view_source_SPEF_SHA256':proof['source_SPEF_sha256'],
      'full_qualification':False,'interpretation':'Both observed OBS intersections are geometry observations, not a new native parent DRC result. Gray is actual occupied OBS; paths use actual rectangles only.'}
    data=out/'data';data.joinpath('mxu_actual_M6_escape_context.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    table=io.StringIO();w=csv.DictWriter(table,fieldnames=list(new[0]),lineterminator='\n');w.writeheader();w.writerows(new);data.joinpath('mxu_actual_escape_net_rectangles.csv').write_text(table.getvalue(),encoding='utf-8',newline='\n')
    plt=expand.legacy.plt;Rect=expand.legacy.Rectangle;fig,axes=plt.subplots(1,3,figsize=(15.8,6.8))
    fig.subplots_adjust(left=.055,right=.98,top=.78,bottom=.27,wspace=.32)
    fig.text(.04,.94,'MXU M6 实际重接、OBS 与接入区域',fontsize=20,weight='bold',color='#17283c')
    fig.text(.04,.87,'原 act_data[12]：M6 / 0.14 × 0.14 μm / XY保持；新叶 native0、原SDC余量为正，父层尚未验证。',fontsize=10,color='#56677d')
    for ax in axes:
        ax.set_aspect('equal');ax.set_xlabel('x (μm)');ax.set_ylabel('y (μm)');ax.ticklabel_format(useOffset=False,style='plain');ax.grid(alpha=.15);ax.set_axisbelow(True)
    for ax,geom,obs,title in zip(axes[:2],[old,new],[oldobs,ctx['actual_M6_OBS_rectangles_um']],['旧叶块 / 旧父层OBS映射','新实际重接 / 新真实LEF OBS']):
        for r in obs:ax.add_patch(Rect((r[0],r[1]),r[2]-r[0],r[3]-r[1],facecolor='#c6ced8',edgecolor='#929eac',alpha=.65,lw=.6))
        for r in geom:
            if r['net']!='act_data[12]' or r['layer']!='metal6' or r['kind'] not in ['WIRE','VIA']:continue
            a,c,d,e=[int(r[k])/2000 for k in ['x0','y0','x1','y1']];ax.add_patch(Rect((a,c),d-a,e-c,facecolor='#328aaa',edgecolor='#328aaa',alpha=.60,lw=.5))
        ax.add_patch(Rect((pin[0],pin[1]),pin[2]-pin[0],pin[3]-pin[1],fill=False,edgecolor='#e5aa4c',lw=1.7))
        ax.set(xlim=(327.95,329.25),ylim=(1068.25,1069.85),title=title)
    marker=oldproof['actual_parent_DRC_marker_um'];marker=[v-d for v,d in zip(marker,[dx,dy,dx,dy])]
    axes[0].add_patch(Rect((marker[0],marker[1]),marker[2]-marker[0],marker[3]-marker[1],fill=False,edgecolor='#bf514c',lw=1.2,ls='--'))
    colors={'metal1':'#8b99aa','metal2':'#8b99aa','metal3':'#9baf85','metal4':'#71a896','metal5':'#e5aa4c','metal6':'#328aaa'}
    for r in new:
        if r['layer'] not in colors:continue
        a,c,d,e=[int(r[k])/2000 for k in ['x0','y0','x1','y1']];axes[2].add_patch(Rect((a,c),d-a,e-c,facecolor=colors[r['layer']],edgecolor=colors[r['layer']],alpha=.7,lw=.5))
    axes[2].scatter([(pin[0]+pin[2])/2,xy[0]],[(pin[1]+pin[3])/2,xy[1]],s=46,facecolors='none',edgecolors=['#bf514c','#8158a0'],linewidths=1.4)
    axes[2].annotate('当前 M6 pin',((pin[0]+pin[2])/2,(pin[1]+pin[3])/2),xytext=(329.3,1069.5),fontsize=9,color='#bf514c')
    axes[2].annotate('真实既有 via5 / M6\n后续 XY 研究区域',xy,xytext=(329.4,1082),fontsize=9,color='#8158a0',arrowprops={'arrowstyle':'-','color':'#8158a0','lw':.8})
    axes[2].set(xlim=(327.5,340),ylim=(1067.4,1095.5),title='当前网络实际 M1–M6 端点路径')
    fig.text(.04,.12,'灰：实际OBS占用；蓝：该网M6实金属；金色边框：真实原pin尺寸。两次OBS均与原pin相交约0.0098 μm²，不能当作父层已可达。\n红框只来自旧父层原生M6报项；新父层未执行。右图圆圈为显示标记，非真实pin/via大小；路径均为真实矩形。\n既有via5位置来自真实路由，尚未把pin迁到该处；没有新父层DRC通过、完整规则通过或面积/时序收益声明。',fontsize=9.5,color='#56677d',linespacing=1.65)
    assets=out/'assets';fig.savefig(assets/'mxu_actual_M6_escape_context.png',dpi=180)
    dest=assets/'mxu_actual_M6_escape_context.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-actual-mxu-M6-context'}):fig.savefig(dest,metadata={'Date':None})
    dest.write_text('\n'.join(s.rstrip() for s in dest.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    return result
