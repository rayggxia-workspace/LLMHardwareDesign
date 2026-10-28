"""Actual fixed conductor geometry and native terminal zoom; never a frozen base."""
from pathlib import Path
import csv,gzip,hashlib,json
import expand_candidates as expand


def read(path):return json.loads(gzip.decompress(path.read_bytes()))


def table(path):
    with gzip.open(path,'rt') as f:return list(csv.DictReader(f,delimiter='\t'))


def plot(root,snapshot,out):
    root,snapshot,out=Path(root),Path(snapshot),Path(out)
    audit=snapshot/'shared_conductor_audit/r02/execution.json.gz'
    if not audit.exists():return None
    proof=read(audit)
    assert proof['all_256_native_FIXEDS_and_original_net_bindings_verified'] and proof['all_closed_source_files_unchanged']
    assert not proof['frozen'] and not proof['qualified']
    source=snapshot/'common_integration/r01/C'
    raw=gzip.decompress((source/'before.shared.tsv.gz').read_bytes());native=table(source/'before.shared.tsv.gz')
    expected=read(source/'actual_shared_conductors.json.gz');fixed=read(audit.parent/'native_fixedness.json.gz')
    bypad={q['pad']:q for q in native};status={q['pad']:q for q in fixed}
    assert len(bypad)==len(expected)==len(status)==256
    rows=[]
    for e in expected:
        q=bypad[e['construction_pad']];f=status[q['pad']]
        assert q['layer']==f['native_layer']=='metal10' and f['native_DEF_path_status']=='FIXED' and q['net']==f['net']
        assert [int(q[k]) for k in ['x0','y0','x1','y1']]==f['native_metal_bbox_dbu']
        assert all(int(q[k])==round(e[k+'_um']*2000) for k in ['x0','y0','x1','y1'])
        rows.append({'resource':e['resource'],'pad':q['pad'],'net':q['net'],'layer':'metal10','native_status':'FIXED',
          **{k+'_um':int(q[k])/2000 for k in ['x0','y0','x1','y1']},
          'actual_centerline_length_um':e['length_um'],'actual_width_um':e['width_um']})
    pins=table(source/'before_route.pins.tsv.gz');pinboxes=[q for q in pins if q['pin'] in bypad]
    assert len(pinboxes)==512 and all(q['layer']=='metal10' and int(q['x1'])-int(q['x0'])==1600 and int(q['y1'])-int(q['y0'])==1600 for q in pinboxes)
    obstacles=table(source/'actual_M10_obstacles.tsv.gz')
    plan=json.loads((root/'common-base-preparation-r04/preparation_contract.json').read_text(encoding='utf-8'))
    origins={q['instance']:q for q in table(source/'placed.instances.tsv.gz')}
    plt,R=expand.legacy.plt,expand.legacy.Rectangle
    fig=plt.figure(figsize=(13,9));grid=fig.add_gridspec(2,2,width_ratios=[1.05,1.1],left=.075,right=.96,top=.78,bottom=.25,hspace=.55,wspace=.30)
    overview=fig.add_subplot(grid[:,0]);area=fig.add_subplot(grid[0,1]);contact=fig.add_subplot(grid[1,1])
    fig.text(.045,.95,'共同集成 | 256 条真实 M10 固定导体',fontsize=22,weight='bold',color='#17283c')
    fig.text(.045,.89,'原生 FIXED 属性、逐网绑定与矩形均已独立读回；每条中心线32 μm、宽0.8 μm，总中心线8192 μm。\n仅为底层布线前检查点：未冻结，尚未证明两套完整功能实际复用；M11/M12适配与完整系统检查仍待完成。',fontsize=11,color='#56677d',linespacing=1.5)
    overview.set_facecolor('#f4f6f8')
    for m in plan['instances']:
        q=origins[m['instance']];x,y=int(q['x'])/2000,int(q['y'])/2000
        assert q['orientation']=='R0' and abs(x-m['x_um'])<1e-6 and abs(y-m['y_um'])<1e-6
        color='#92b8e3' if m['enabled_in']=='opentpu' else '#9bd2bb'
        overview.add_patch(R((x,y),m['width_um'],m['height_um'],facecolor=color,edgecolor='#42566f',lw=1))
        name={'opentpu_aux':'openTPU\nSYSTEM','llaccel_aux':'llaccel\nSYSTEM'}.get(m['case'],m['case'].upper())
        overview.text(x+m['width_um']/2,y+m['height_um']/2,name,ha='center',va='center',fontsize=9 if m['case']!='act' else 6,color='#17283c')
    for q in rows:overview.add_patch(R((q['x0_um'],q['y0_um']),q['x1_um']-q['x0_um'],q['y1_um']-q['y0_um'],facecolor='#128977',linewidth=0))
    cluster=[min(q['x0_um'] for q in rows)-25,min(q['y0_um'] for q in rows)-25,max(q['x1_um'] for q in rows)+25,max(q['y1_um'] for q in rows)+25]
    overview.add_patch(R((cluster[0],cluster[1]),cluster[2]-cluster[0],cluster[3]-cluster[1],facecolor='none',edgecolor='#b24a43',ls='--',lw=1.4))
    overview.annotate('256条导体所在区域\n虚框仅为定位ROI',xy=(cluster[2],(cluster[1]+cluster[3])/2),xytext=(cluster[2]+120,cluster[3]+350),fontsize=8,color='#a23c37',arrowprops={'arrowstyle':'->','color':'#a23c37'})
    overview.set_xlim(plan['frame_um'][0],plan['frame_um'][2]);overview.set_ylim(plan['frame_um'][1],plan['frame_um'][3]);overview.set_aspect('equal')
    overview.set_title('六资源原生放置 + 实际导体',loc='left',fontsize=11,weight='bold')
    chosen=rows[0];cx=(chosen['x0_um']+chosen['x1_um'])/2;cy=chosen['y0_um']+.4
    windows=[(area,[cx-35,cy-5,cx+55,cy+40],'接点邻域：仅显示实际 M10 金属'),(contact,[cx-6,cy-2.4,cx+6,cy+2.4],chosen['resource']+' 下端与邻近 M10 接点（未画via）')]
    for ax,window,title in windows:
        ax.set_facecolor('#f4f6f8')
        for ob in obstacles:
            b=[int(ob[k])/2000 for k in ['x0','y0','x1','y1']]
            if b[0]>=window[2] or b[2]<=window[0] or b[1]>=window[3] or b[3]<=window[1]:continue
            pg=ob['kind'].startswith('PG');color='#d5a34a' if pg else '#7c8796'
            ax.add_patch(R((b[0],b[1]),b[2]-b[0],b[3]-b[1],facecolor=color,edgecolor=color,lw=.4,alpha=.55))
        for q in rows:
            if q['x0_um']>=window[2] or q['x1_um']<=window[0] or q['y0_um']>=window[3] or q['y1_um']<=window[1]:continue
            ax.add_patch(R((q['x0_um'],q['y0_um']),q['x1_um']-q['x0_um'],q['y1_um']-q['y0_um'],facecolor='#128977',linewidth=0,alpha=.85))
        for q in pinboxes:
            b=[int(q[k])/2000 for k in ['x0','y0','x1','y1']]
            if b[0]>=window[2] or b[2]<=window[0] or b[1]>=window[3] or b[3]<=window[1]:continue
            ax.add_patch(R((b[0],b[1]),b[2]-b[0],b[3]-b[1],facecolor='none',edgecolor='#2463b6',lw=1.5))
        ax.set_xlim(window[0],window[2]);ax.set_ylim(window[1],window[3]);ax.set_aspect('equal')
        ax.set_title(title,loc='left',fontsize=10,weight='bold');ax.ticklabel_format(style='plain',useOffset=False)
    for ax in [overview,area,contact]:ax.set_xlabel('X (μm)');ax.set_ylabel('Y (μm)');ax.grid(alpha=.14)
    fig.text(.045,.10,'绿色：真实M10导体矩形；蓝框：父层施工port的实际0.8 × 0.8 μm接点；金色/灰色：该层已导出的PG/宏OBS。\n总览用于定位；局部显示真实矩形，不以标记冒充via尺寸。未画M11/M12、via及其他层金属；浅灰不是空白接入许可。\n新增父层M10中间点不改变原叶pin的M5/M6；施工port尚待合法降为模式固定几何。固定属性/几何通过不代表DRC、两模式连通或冻结通过。',fontsize=10,color='#56677d',linespacing=1.6)
    assets=out/'assets';fig.savefig(assets/'common_shared_conductors_actual.png',dpi=180)
    svg=assets/'common_shared_conductors_actual.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-actual-fixed256'}):fig.savefig(svg,metadata={'Date':None})
    svg.write_text('\n'.join(s.rstrip() for s in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    with (out/'data/common_shared_conductors_actual.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    result={'scope':'ACTUAL_NATIVE_FIXED256_PRE_GRT_CHECKPOINT_NOT_FROZEN_OR_TWO_MODE_REUSE',
      'native_fixed_conductors':256,'native_shared_port_boxes':len(pinboxes),'native_metal_layer':'metal10',
      'native_geometry_uncompressed_SHA256':hashlib.sha256(raw).hexdigest(),'all_native_FIXEDS_verified':True,
      'native_centerline_length_um':8192.,'full_qualification':False,'two_complete_mode_reuse':'NOT_VERIFIED'}
    (out/'data/common_shared_conductors_actual.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result
