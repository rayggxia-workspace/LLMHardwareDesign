"""Measured M6 hierarchy zoom; same-net occupancy is not a DRC waiver."""
from pathlib import Path
import csv,gzip,hashlib,json,math
import expand_candidates as expand


def intersection(a,b):
    c=[max(a[0],b[0]),max(a[1],b[1]),min(a[2],b[2]),min(a[3],b[3])]
    return c if c[2]>c[0] and c[3]>c[1] else None


def covered_area(box,rectangles):
    pieces=[q for r in rectangles if (q:=intersection(box,r))]
    xs=sorted({box[0],box[2]}|{v for q in pieces for v in [q[0],q[2]]});area=0
    for x0,x1 in zip(xs,xs[1:]):
        spans=sorted((q[1],q[3]) for q in pieces if q[0]<=x0 and q[2]>=x1)
        length=0;bottom=top=None
        for lo,hi in spans:
            if top is None:bottom,top=lo,hi
            elif lo>top:length+=top-bottom;bottom,top=lo,hi
            else:top=max(top,hi)
        if top is not None:length+=top-bottom
        area+=(x1-x0)*length
    return area


def plot(snapshot,out):
    source=Path(snapshot)/'parent_region_audit/r01';proof=source/'execution.json.gz'
    if not proof.exists():return None
    rec=json.loads(gzip.decompress(proof.read_bytes()));assert rec['all_sources_unchanged']
    groups={};raw_hash={}
    for label,info in rec['sources'].items():
        assert info['native_returncode']==0
        p=source/(label+'.tsv.gz');raw=gzip.decompress(p.read_bytes());raw_hash[label]=hashlib.sha256(raw).hexdigest()
        with gzip.open(p,'rt') as f:rows=list(csv.DictReader(f,delimiter='\t'))
        dx,dy=[round(v*2000) for v in info['to_parent_translation_um']]
        for q in rows:
            q['box']=[int(q[k])+v for k,v in zip(['x0','y0','x1','y1'],[dx,dy,dx,dy])]
        groups[label]=[q for q in rows if q['layer']=='metal6']
    key=lambda q:(q['net'],q['kind'],tuple(q['box']))
    identical=sorted(map(key,groups['leaf_before_ECO']))==sorted(map(key,groups['leaf_costed_ECO']))
    marker=[round(v*2000) for v in rec['actual_parent_DRC_marker_um']]
    own=[q['box'] for q in groups['leaf_costed_ECO'] if q['role']=='SELECTED_INTERFACE_NET' and q['kind'] in ['WIRE','VIA']]
    offending=[q for q in groups['parent'] if q['kind']=='MACRO_OBS' and intersection(q['box'],marker)]
    coverage=[]
    for q in offending:
        b=q['box'];area=(b[2]-b[0])*(b[3]-b[1]);covered=covered_area(b,own)
        coverage.append({'parent_OBS_box_um':[v/2000 for v in b],'area_um2':area/4e6,
          'actual_same_net_leaf_metal_covered_um2':covered/4e6,'fully_covered_by_same_net_leaf_metal':covered==area})
    parent_signal=[q['box'] for q in groups['parent'] if q['role']=='SELECTED_INTERFACE_NET' and q['kind'] in ['WIRE','VIA']]
    foreign=[q['box'] for q in groups['leaf_costed_ECO'] if q['role']!='SELECTED_INTERFACE_NET' and q['kind'] in ['WIRE','VIA','PG_WIRE','PG_VIA']]
    gap=min(math.hypot(max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0))/2000 for a in parent_signal for b in foreign)
    result={'scope':'BOUNDED_M6_OWNERSHIP_AND_GEOMETRIC_GAP_NOT_FULL_DRC_LVS_OR_ACCESS_PASS',
      'old_and_costed_leaf_all_exported_M6_rectangles_and_net_labels_equal':identical,
      'marker_intersecting_parent_M6_OBS_same_net_coverage':coverage,
      'nearest_exported_foreign_M6_metal_to_parent_landing_geometric_gap_um':gap,
      'gap_is_not_a_rule_pass':True,'original_parent_native_DRC_count_retained':2,
      'unchecked_leaf_OBS_transforms':{k:v['unchecked_macro_transform_rows'] for k,v in rec['sources'].items()},
      'raw_native_region_uncompressed_SHA256':raw_hash,'full_qualification':False,
      'interpretation':'Same-net ownership evidence for this OBS, not permission to delete OBS or waive parent/native/full hierarchical rules.'}
    (Path(out)/'data/mxu_parent_region_ownership.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    plt,R=expand.legacy.plt,expand.legacy.Rectangle;fig,axes=plt.subplots(1,3,figsize=(17,8.3))
    fig.subplots_adjust(left=.06,right=.98,top=.77,bottom=.26,wspace=.28)
    fig.text(.045,.95,'MXU | 原生 M6 接入报项与真实金属归属',fontsize=21,weight='bold',color='#17283c')
    fig.text(.045,.89,'act_data[12]：原pin与新父层via的M6落脚均为真实0.14 × 0.14 μm矩形；三个面板采用相同全局坐标与3 × 3 μm窗口。',fontsize=10,color='#56677d')
    labels=[('leaf_before_ECO','旧叶块真实M6'),('leaf_costed_ECO','成本ECO叶块真实M6'),('parent','父层真实M6与宏OBS')]
    box=rec['sources']['parent']['local_window_um']
    for ax,(label,title) in zip(axes,labels):
        ax.set_facecolor('#f4f6f8')
        for q in groups[label]:
            b=[v/2000 for v in q['box']];pin=q['kind'] in ['BTERM','ITERM'];obs=q['kind']=='MACRO_OBS'
            color='#20a48c' if q['role']=='SELECTED_INTERFACE_NET' else '#d5a34a' if q['role']=='PG' else '#7c8796'
            ax.add_patch(R((b[0],b[1]),b[2]-b[0],b[3]-b[1],facecolor='none' if pin or obs else color,
              edgecolor='#2463b6' if pin else '#7461a1' if obs else color,lw=1.5 if pin else .7,
              hatch='////' if obs else None,alpha=.8 if pin or obs else .55))
        m=[v/2000 for v in marker];ax.add_patch(R((m[0],m[1]),m[2]-m[0],m[3]-m[1],facecolor='none',edgecolor='#d2443e',ls='--',lw=1.6))
        ax.set_xlim(box[0],box[2]);ax.set_ylim(box[1],box[3]);ax.set_aspect('equal');ax.grid(alpha=.14)
        ax.ticklabel_format(style='plain',useOffset=False);ax.tick_params(axis='x',rotation=25)
        ax.set_title(title,loc='left',weight='bold',fontsize=12);ax.set_xlabel('X (μm)');ax.set_ylabel('Y (μm)')
    fig.text(.045,.12,'绿色：该信号实际金属；灰色：已导出异网金属；蓝框：原pin/宏pin；紫斜线：父层所读宏OBS；红虚框：原生DRC范围（不是via尺寸）。\n实际落脚只显示M6金属，不代表via切孔或整栈占地。重叠OBS被真实同网叶金属覆盖，是占用归属证据，不是空白或规则豁免。\n其余层/完整层次规则未检查，两个叶源各有2项OBS变换未核对；原父层2项native失败保留，须继续真实修复/层次验证。',fontsize=10,color='#56677d',linespacing=1.7)
    assets=Path(out)/'assets';fig.savefig(assets/'mxu_M6_actual_ownership.png',dpi=180)
    path=assets/'mxu_M6_actual_ownership.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-mxu-real-M6'}):fig.savefig(path,metadata={'Date':None})
    path.write_text('\n'.join(s.rstrip() for s in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    return result
