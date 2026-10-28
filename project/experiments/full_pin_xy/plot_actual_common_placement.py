"""Draw only actual native six-macro origins, without inventing routed prewires."""
from pathlib import Path
import csv,gzip,hashlib,json
import expand_candidates as expand


def plot(root,snapshot,out):
    p=snapshot/'common_integration/r01/C/placed.instances.tsv.gz'
    if not p.exists():return None
    raw=gzip.decompress(p.read_bytes())
    with gzip.open(p,'rt') as f:rows=list(csv.DictReader(f,delimiter='\t'))
    byname={r['instance']:r for r in rows};assert len(rows)==len(byname)==44
    prep=Path(root)/'common-base-preparation-r04/preparation_contract.json';plan=json.loads(prep.read_text(encoding='utf-8'))
    counts={'act':860,'mxu':2172,'opentpu_aux':2229,'gemm':3753,'vector':2246,'llaccel_aux':13507}
    plt,R=expand.legacy.plt,expand.legacy.Rectangle
    fig,ax=plt.subplots(figsize=(9.4,11.5));fig.subplots_adjust(left=.13,right=.94,bottom=.18,top=.83)
    fig.text(.075,.955,'六资源共同集成 | 原生实际放置',fontsize=20,weight='bold',color='#17283c')
    progress=('父层PG所检完成；256条M10导体已写入，底层布线及两模式尚未闭合。'
      if (snapshot/'common_integration/r01/C/before.shared.tsv.gz').exists()
      else 'PG/后续接入执行中；共享固定导体与两完整适配模式尚未完成。')
    fig.text(.075,.905,'92855 / C：6块 + 38个常量/idle基础设施实例。\n'+progress,fontsize=11,color='#56677d',linespacing=1.6)
    ax.set_facecolor('#f4f6f8')
    for m in plan['instances']:
        r=byname[m['instance']];assert r['master']=='p126_'+m['case'] and r['orientation']=='R0'
        x,y=int(r['x'])/2000,int(r['y'])/2000
        assert abs(x-m['x_um'])<1e-6 and abs(y-m['y_um'])<1e-6
        color='#92b8e3' if m['enabled_in']=='opentpu' else '#9bd2bb'
        ax.add_patch(R((x,y),m['width_um'],m['height_um'],facecolor=color,edgecolor='#42566f',lw=1.2))
        name={'opentpu_aux':'openTPU SYSTEM','llaccel_aux':'llaccel SYSTEM'}.get(m['case'],m['case'].upper())
        ax.text(x+m['width_um']/2,y+m['height_um']/2,name+'\n'+str(counts[m['case']])+(' pin' if m['case']=='act' else ' signal pin'),ha='center',va='center',fontsize=10 if m['case']!='act' else 7,color='#17283c')
    infrastructure=[q for q in rows if not q['master'].startswith('p126_')];assert len(infrastructure)==38
    ax.scatter([int(q['x'])/2000 for q in infrastructure],[int(q['y'])/2000 for q in infrastructure],s=15,color='#c67d3e',zorder=4)
    ax.annotate('38个真实基础设施实例原点\n标记非单元尺寸',xy=(80,10),xytext=(650,420),arrowprops={'arrowstyle':'->','color':'#8c6338'},fontsize=9,color='#8c6338')
    ax.set_xlim(plan['frame_um'][::2]);ax.set_ylim(plan['frame_um'][1::2]);ax.set_aspect('equal')
    ax.set_xlabel('X (μm)');ax.set_ylabel('Y (μm)');ax.grid(alpha=.14)
    fig.text(.075,.065,'蓝色：openTPU资源；绿色：llaccel资源。位置来自原生placed.instances回执，\n外框来自保持不变的实际叶块尺寸。未绘制内部金属、pin或PG，背景不代表可布线区域。\nLL SYSTEM原有4项native DRC、VECTOR/SYSTEM时序及其他资格缺口继续保留。\n实际放置不等于共享预连、合格冻结、M11/M12模式或系统收益已经完成。',fontsize=10,color='#56677d',linespacing=1.65)
    assets=Path(out)/'assets';fig.savefig(assets/'common_placement_actual.png',dpi=180)
    target=assets/'common_placement_actual.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-actual-common-placement'}):fig.savefig(target,metadata={'Date':None})
    target.write_text('\n'.join(s.rstrip() for s in target.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    return {'actual_instances':44,'functional_macro_instances':6,'infrastructure_instances':38,
      'native_placement_uncompressed_SHA256':hashlib.sha256(raw).hexdigest(),'source_preparation_SHA256':hashlib.sha256(prep.read_bytes()).hexdigest(),
      'scope':'ACTUAL_R0_PLACEMENT_ONLY_NOT_PDN_OR_PREWIRE_OR_FROZEN_BASE','full_qualification':False}
