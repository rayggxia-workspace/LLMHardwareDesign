"""Actual M6 one-pin/route ECO before/after; source-bound, not a sketch."""
from pathlib import Path
from collections import Counter
import csv,gzip,hashlib,io,json
import expand_candidates as expand


def read(p):return json.loads(gzip.decompress(p.read_bytes()))


def plot(snapshot,terminal,out):
    snapshot,terminal,out=Path(snapshot),Path(terminal),Path(out)
    old=snapshot/'pin_escape_views/r01/mxu-C';new=terminal/'mxu-actual-tip-views-r01'
    if not (new/'execution.json.gz').exists():return None
    before,after=read(old/'execution.json.gz'),read(new/'execution.json.gz')
    actual=read(terminal/'mxu-actual-via-tip-r01/execution.json.gz')
    fresh=read(terminal/'mxu-actual-tip-fresh-r01/execution.json.gz')
    assert after['matching_all_signal_model_pins']==2172 and after['all_2172_current_pins_and_PG_match_actual_after_edit']
    assert after['source_geometry_sha256']==fresh['source_actual_ECO_ODB_SHA256']==actual['files']['routed.odb']['sha256']
    assert fresh['native_fresh_returncode']==fresh['fresh_DRC_count']==0 and fresh['all_closed_sources_unchanged']
    assert after['SPEF_replay_matches_source'] and after['all_sources_and_pre_RCX_geometry_unchanged']
    originals=[v for p,v in actual['source_SHA'].items() if p.endswith('/pin_escape_route/r02/mxu-C/routed.odb')]
    assert originals==[before['source_geometry_sha256']]
    versions=[]
    for folder,q in [(old,before),(new,after)]:
        raw=gzip.decompress((folder/'target_pin_access.tsv.gz.gz').read_bytes())
        assert hashlib.sha256(raw).hexdigest()==q['files']['target_pin_access.tsv.gz']['sha256']
        rows=list(csv.DictReader(io.StringIO(gzip.decompress(raw).decode()),delimiter='\t'))
        assert {r['net'] for r in rows}=={'act_data[12]'};versions.append(rows)
    assert list(map(len,versions))==[24,20]
    key=lambda r:tuple(r[k] for k in ['kind','layer','x0','y0','x1','y1'])
    a,b=[Counter(map(key,rows)) for rows in versions];removed=a-b;added=b-a
    assert Counter(k[0] for k in removed.elements())=={'WIRE':4,'BTERM':1}
    assert Counter(k[0] for k in added.elements())=={'BTERM':1}
    def box(r):return [int(r[k])/2000 for k in ['x0','y0','x1','y1']]
    boxes=[box(r) for rows in versions for r in rows]
    full=[min(z[0] for z in boxes)-.5,max(z[2] for z in boxes)+.5,min(z[1] for z in boxes)-.5,max(z[3] for z in boxes)+.5]
    pp=[box(next(r for r in rows if r['kind']=='BTERM')) for rows in versions]
    plt=expand.legacy.plt;Rectangle=expand.legacy.Rectangle
    fig,axes=plt.subplots(2,2,figsize=(13.5,12),gridspec_kw={'height_ratios':[2.7,1]})
    fig.subplots_adjust(left=.08,right=.96,top=.83,bottom=.19,hspace=.34,wspace=.22)
    fig.text(.045,.955,'openTPU MXU | 原 M6 pin 接至真实 via 落脚',fontsize=21,weight='bold',color='#17283c')
    fig.text(.045,.91,'act_data[12]：只改 XY 并删除四条旧 M6 末端线；2172 位逐 pin 合同、原 via / 单元 / PG / 外框保持。',fontsize=10.5,color='#56677d')
    colors={'metal1':'#9aa7b4','metal2':'#4098ac','metal3':'#68a28d','metal4':'#aec199','metal5':'#328aaa','metal6':'#8a6eb0'}
    for col,rows in enumerate(versions):
        z=pp[col];cx,cy=(z[0]+z[2])/2,(z[1]+z[3])/2
        for row in [0,1]:
            ax=axes[row,col]
            for layer,color in colors.items():
                for r in rows:
                    if r['layer']!=layer or r['kind'] in ['BTERM','ITERM']:continue
                    x0,y0,x1,y1=box(r);ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor=color,edgecolor=color,alpha=.58,linewidth=.5))
            for r in rows:
                if r['kind']=='BTERM':
                    x0,y0,x1,y1=box(r);ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#f5cc67',edgecolor='#17283c',linewidth=1))
                if r['kind']=='ITERM':
                    x0,y0,x1,y1=box(r);ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='none',edgecolor='#5b6d80',hatch='///',linewidth=.8))
                if col==0 and r['kind']=='WIRE' and key(r) in removed:
                    x0,y0,x1,y1=box(r);ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,edgecolor='#d75852',linestyle='--',linewidth=1.1))
            limits=full if row==0 else [cx-1.2,cx+1.2,cy-1.2,cy+1.2]
            ax.set_xlim(limits[:2]);ax.set_ylim(limits[2:]);ax.set_aspect('equal');ax.grid(alpha=.12);ax.set_axisbelow(True)
            ax.set_title(('原实际接线' if col==0 else '实际 via-tip 接线')+(' | 完整目标网' if row==0 else ' | pin 附近 2.4 × 2.4 μm'),fontsize=11,color='#17283c')
            ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=8);ax.set_xlabel('x (μm)',fontsize=9);ax.set_ylabel('y (μm)',fontsize=9)
            if row==0:ax.annotate('原 M6 pin' if col==0 else '同网原 via5 的 M6 帽',xy=(cx,cy),xytext=(cx+1,cy+1),fontsize=8,color='#56677d',arrowprops={'arrowstyle':'->','color':'#56677d','lw':.8})
    handles=[Rectangle((0,0),1,1,facecolor=c,alpha=.6) for c in colors.values()]
    handles += [Rectangle((0,0),1,1,facecolor='#f5cc67',edgecolor='#17283c'),Rectangle((0,0),1,1,fill=False,edgecolor='#d75852',linestyle='--')]
    fig.legend(handles,list(colors)+['真实 0.14 μm pin','实际删除的 M6 WIRE'],loc='lower left',bbox_to_anchor=(.055,.095),ncol=4,frameon=False,fontsize=9)
    fig.text(.045,.025,'真实原生矩形（含 via 各金属落脚），箭头不是金属；上排同范围，下排同倍率，pin 与 via 尺寸按 DBU。\n只画该网，未绘的异网 / PG / OBS 不能视为空闲。原范围 fresh native 0；setup / hold 0.246690 / 0.038538 ns。\n首次检查驱动 DRT-0155 原文保留；完整 GDS / SRAM / 规则 / 父层 / RTL 仍未通过或待验证，未报告系统收益。',fontsize=9.2,color='#56677d',linespacing=1.6)
    assets=out/'assets';fig.savefig(assets/'mxu_actual_via_tip_repair.png',dpi=180)
    p=assets/'mxu_actual_via_tip_repair.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-mxu-native-via-tip'}):fig.savefig(p,metadata={'Date':None})
    p.write_text('\n'.join(s.rstrip() for s in p.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    result={'scope':'ACTUAL_M6_VIA_TIP_RECTANGLES_NOT_SCHEMATIC','full_qualification':False,
      'source_ODB_before_after_SHA256':[before['source_geometry_sha256'],after['source_geometry_sha256']],
      'actual_target_rows_before_after':[24,20],'removed_M6_WIRE_rectangles':4,
      'signal_pin_count':2172,'only_changed_XY_pins':['act_data[12]'],'all_actual_vias_unchanged':True,
      'source_original_range_fresh_DRC_count':fresh['fresh_DRC_count'],
      'source_setup_hold_ns':[actual['setup_ns'],actual['hold_ns']],
      'pin_boxes_before_after_um':pp,'not_drawn':['Foreign nets','PG','OBS'],
      'not_verified_by_figure':['Parent access','Complete GDS/rules','RTL or system equivalence','System area/timing/RC benefit']}
    (out/'data/mxu_actual_via_tip_repair.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result
