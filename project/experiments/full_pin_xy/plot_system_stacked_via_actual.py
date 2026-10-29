"""Actual before/after target-net rectangles; no inferred or invented routes."""
from pathlib import Path
from collections import Counter
import csv,gzip,hashlib,io,json,re
import expand_candidates as expand


def read(path):return json.loads(gzip.decompress(path.read_bytes()))


def plot(snapshot,out):
    snapshot,out=Path(snapshot),Path(out)
    folder=snapshot/'system_stacked_via_views/r01/opentpu_aux-C';vp=folder/'execution.json.gz'
    if not vp.exists():return None
    view=read(vp)
    if not view.get('completed_utc') or view.get('native_export_returncode')!=0:return None
    assert view['before_target_actual_export_returncode']==0 and view['matching_all_signal_model_pins']==2229
    assert view['all_original_signal_and_PG_pins_and_size_exactly_preserved'] and view['SPEF_replay_matches_source']
    previous=snapshot/'system_patch_route/r02/opentpu_aux-C';current=snapshot/'system_stacked_via_route/r01/opentpu_aux-C'
    before,after=read(previous/'execution.json.gz'),read(current/'execution.json.gz')
    assert before['fresh_DRC_count']==2 and after['fresh_DRC_count']==0
    assert view['before_actual_geometry_sha256']==before['files']['routed.odb']['sha256']
    assert view['source_geometry_sha256']==after['files']['routed.odb']['sha256']
    assert view['source_receipt_SHA256']==hashlib.sha256(gzip.decompress((current/'execution.json.gz').read_bytes())).hexdigest()
    versions=[];allrows=[]
    for tag,name in [('before','before_actual_target.tsv.gz'),('after','after_actual_target.tsv.gz')]:
        raw=gzip.decompress((folder/(name+'.gz')).read_bytes())
        assert hashlib.sha256(raw).hexdigest()==view['files'][name]['sha256']
        rows=list(csv.DictReader(io.StringIO(gzip.decompress(raw).decode()),delimiter='\t'))
        assert {r['net'] for r in rows}=={'_215139_'}
        versions.append(rows);allrows.extend(dict(r,version=tag) for r in rows)
    text=gzip.decompress((previous/'independent.drc.gz').read_bytes()).decode()
    markers=[list(map(float,m[:4])) for m in re.findall(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)',text)]
    assert len(markers)==2
    plt=expand.legacy.plt;Rectangle=expand.legacy.Rectangle
    fig,axes=plt.subplots(1,2,figsize=(13.5,7.1))
    fig.subplots_adjust(left=.08,right=.96,top=.76,bottom=.30,wspace=.21)
    fig.text(.045,.94,'openTPU SYSTEM | 真实 M2 接入修复',fontsize=20,weight='bold',color='#17283c')
    fig.text(.045,.87,'原接口 pin / 单元 / PG 保持；_215139_ 为块内两单元间网（无 BTerm），fresh native 2 → 0；负时序保留。',fontsize=10.4,color='#56677d')
    colors={'metal1':'#e5aa4c','metal2':'#328aaa','metal3':'#63a28b','via1':'#8a6eb0','via2':'#c07aa1'}
    unit=after['actual_detail_edit']['DBU_per_um'];assert unit==2000
    points=[tuple(int(r[k])/unit for k in ['x0','y0','x1','y1']) for rows in versions for r in rows]
    limits=(min(b[0] for b in points)-.15,max(b[2] for b in points)+.15,min(b[1] for b in points)-.15,max(b[3] for b in points)+.15)
    for ax,rows,title in zip(axes,versions,['重接前：实际 clean_patches/r02，native 2','重接后：实际 stacked_via/r01，native 0']):
        for layer in colors:
            for r in rows:
                if r['layer']!=layer:continue
                x0,y0,x1,y1=[int(r[k])/unit for k in ['x0','y0','x1','y1']]
                ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor=colors[layer],edgecolor=colors[layer],alpha=.52 if layer.startswith('metal') else .85,linewidth=.7,hatch='//' if r['kind']=='ITERM' else None))
        ax.set_xlim(limits[:2]);ax.set_ylim(limits[2:]);ax.set_aspect('equal');ax.set_title(title,fontsize=11,color='#17283c')
        ax.set_xlabel('x (μm)');ax.set_ylabel('y (μm)');ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=8);ax.grid(alpha=.12);ax.set_axisbelow(True)
    for b in markers:axes[0].add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor='#d75852',linestyle='--',linewidth=1.4))
    d=after['actual_detail_edit'];sx,sy=[v/unit for v in d['new_sink_stack_xy_dbu']]
    axes[1].annotate('原 via1 / via2 定义\n在真实 M1 端点内叠放',xy=(sx,sy),xytext=(sx+.18,sy+.48),fontsize=9,color='#56677d',arrowprops={'arrowstyle':'->','color':'#56677d','lw':.9})
    handles=[Rectangle((0,0),1,1,facecolor=c,alpha=.65) for c in colors.values()]
    handles.append(Rectangle((0,0),1,1,fill=False,edgecolor='#d75852',linestyle='--'))
    fig.legend(handles,list(colors)+['旧原生 DRC bbox'],loc='lower left',bbox_to_anchor=(.07,.17),ncol=6,frameon=False,fontsize=9)
    fig.text(.045,.065,'全部图形为两份实际 ODB 的原生导出矩形，非示意路径；尺寸按真实 DBU，斜线表示真实 M1 ITerm。\n只画该网，周边异网 / PG / OBS 未绘，白底不是空闲许可。完整块已独立检查，局部图不替代全块验证。\nsetup / hold −0.056396 / −0.119919 ns；完整 GDS / 父层 / RTL / 共同冻结仍未通过或未验证，无面积或系统收益声明。',fontsize=9.4,color='#56677d',linespacing=1.6)
    assets=out/'assets';fig.savefig(assets/'system_stacked_via_actual.png',dpi=180)
    path=assets/'system_stacked_via_actual.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-system-actual-stacked-via'}):fig.savefig(path,metadata={'Date':None})
    path.write_text('\n'.join(s.rstrip() for s in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    data=out/'data'
    with (data/'system_stacked_via_actual_rectangles.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(allrows[0]),lineterminator='\n');w.writeheader();w.writerows(allrows)
    result={'scope':'ACTUAL_COMPLETE_TARGET_NET_BEFORE_AFTER_NATIVE_RECTANGLES_NOT_SCHEMATIC_OR_FULL_QUALIFICATION','full_qualification':False,
      'before_ODB_SHA256':view['before_actual_geometry_sha256'],'after_ODB_SHA256':view['source_geometry_sha256'],
      'source_view_receipt_SHA256':hashlib.sha256(gzip.decompress(vp.read_bytes())).hexdigest(),'DBU_per_um':unit,
      'source_native_DRC_before_after':[2,0],'before_actual_markers_um':markers,
      'actual_rows_before_after':[len(rows) for rows in versions],'actual_layer_rows_before_after':[dict(Counter(r['layer'] for r in rows)) for rows in versions],
      'setup_hold_ns':[after['setup_ns'],after['hold_ns']],'all_2229_signal_pins_and_PG_preserved':True,
      'not_checked_by_figure':['Foreign metal/PG/OBS not drawn','Full GDS/rules','Parent accessibility','RTL/system equivalence','System area/RC/timing gain']}
    (data/'system_stacked_via_actual.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result
