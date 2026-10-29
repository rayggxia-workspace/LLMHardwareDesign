"""Draw original native rectangles before/after three actual LL pin repairs."""
from pathlib import Path
from collections import Counter
import csv,gzip,hashlib,io,json
import expand_candidates as expand


def read(p):return json.loads(gzip.decompress(p.read_bytes()))


def plot(snapshot,out):
    snapshot,out=Path(snapshot),Path(out)
    ap=snapshot/'parent_noap_grid_audit/r01/execution.json.gz'
    if not ap.exists():return None
    audit=read(ap);assert audit['all_closed_sources_unchanged']
    old=snapshot/'llsys_DRC_diagnosis/r01';op=old/'execution.json.gz';before=read(op)
    current=snapshot/'llsys_actual_via_tips/r02';cp=current/'execution.json.gz';after=read(cp)
    assert before['source_native_DRC_count']==4 and after['fresh_DRC_count']==0
    assert after['all_actual_target_via_rectangle_multisets_preserved']
    assert after['exactly_eight_actual_WIRE_rectangles_removed_no_added_wire_or_via_material']
    whole=[h for p,h in audit['source_SHA'].items() if p.endswith('/llsys_actual_via_tips/r02/whole_access.tsv.gz')]
    assert whole==[after['files']['whole_access.tsv.gz']['sha256']]
    raw=gzip.decompress((ap.parent/'actual_error_and_three_repaired_complete_nets.tsv.gz').read_bytes())
    assert hashlib.sha256(raw).hexdigest()==audit['files']['actual_error_and_three_repaired_complete_nets.tsv']['sha256']
    targets=['bit_1382013','bit_6907','bit_1389626']
    rows0=list(csv.DictReader(io.StringIO(gzip.decompress((old/'three_complete_actual_nets.tsv.gz').read_bytes()).decode()),delimiter='\t'))
    rows1=[r for r in csv.DictReader(io.StringIO(raw.decode()),delimiter='\t') if r['net'] in targets]
    assert len(rows0)==862 and len(rows1)==854
    def box(r):return tuple(int(r[k])/2000 for k in ['x0','y0','x1','y1'])
    def key(r):return tuple(r[k] for k in ['net','layer','x0','y0','x1','y1','kind'])
    a,b=Counter(map(key,rows0)),Counter(map(key,rows1))
    removed=list((a-b).elements());added=list((b-a).elements())
    assert Counter(r[-1] for r in removed)=={'WIRE':8,'BTERM':3} and Counter(r[-1] for r in added)=={'BTERM':3}
    plt=expand.legacy.plt;Rectangle=expand.legacy.Rectangle
    fig,axes=plt.subplots(3,2,figsize=(13.5,11.8));fig.subplots_adjust(left=.09,right=.97,top=.84,bottom=.16,hspace=.52,wspace=.24)
    fig.text(.045,.955,'llaccel SYSTEM | 三处真实 pin / 末端接线修复',fontsize=21,weight='bold',color='#17283c')
    fig.text(.045,.91,'完整内部 C 保留；13507 信号 pin 中仅三点作增量修复，原 M5/M6 / 尺寸 / 网络 / 方向保持。',fontsize=10.5,color='#56677d')
    colors={'metal4':'#68a28d','metal5':'#328aaa','metal6':'#8a6eb0','via4':'#a3bd89','via5':'#bc9a5c','via6':'#c07aa1'}
    for i,pin in enumerate(targets):
        pair=[[r for r in rs if r['net']==pin] for rs in [rows0,rows1]]
        pp=[box(next(r for r in rs if r['kind']=='BTERM')) for rs in pair]
        x0=min(z[0] for z in pp)-.7;x1=max(z[2] for z in pp)+.7
        y0=min(z[1] for z in pp)-.7;y1=max(z[3] for z in pp)+.7
        for col,rs in enumerate(pair):
            ax=axes[i,col]
            for layer,color in colors.items():
                for r in rs:
                    if r['layer']!=layer or r['kind'] in ['BTERM','ITERM']:continue
                    a0,c0,d0,e0=box(r)
                    if a0>x1 or d0<x0 or c0>y1 or e0<y0:continue
                    ax.add_patch(Rectangle((a0,c0),d0-a0,e0-c0,facecolor=color,edgecolor=color,alpha=.48,linewidth=.5))
            z=pp[col];ax.add_patch(Rectangle((z[0],z[1]),z[2]-z[0],z[3]-z[1],facecolor='#f5cc67',edgecolor='#17283c',linewidth=1.2))
            if col==0:
                for r in rs:
                    if r['kind']=='WIRE' and key(r) in removed:
                        z=box(r);ax.add_patch(Rectangle((z[0],z[1]),z[2]-z[0],z[3]-z[1],fill=False,edgecolor='#d75852',linestyle='--',linewidth=1.2))
            ax.set_xlim(x0,x1);ax.set_ylim(y0,y1);ax.set_aspect('equal');ax.grid(alpha=.12);ax.set_axisbelow(True)
            ax.set_title(pin+' | '+('修复前' if col==0 else '真实修复后'),fontsize=11,color='#17283c')
            ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=8);ax.set_xlabel('x (μm)',fontsize=9);ax.set_ylabel('y (μm)',fontsize=9)
    handles=[Rectangle((0,0),1,1,facecolor=c,alpha=.6) for c in colors.values()]
    handles += [Rectangle((0,0),1,1,facecolor='#f5cc67',edgecolor='#17283c'),Rectangle((0,0),1,1,fill=False,edgecolor='#d75852',linestyle='--')]
    fig.legend(handles,list(colors)+['真实 0.14μm pin','实际删除的末端 WIRE'],loc='lower left',bbox_to_anchor=(.055,.09),ncol=4,frameon=False,fontsize=9)
    fig.text(.045,.025,'全部为真实原生矩形，左右各对使用同一坐标尺度；只画所选原网，白底不代表无异网 / PG / OBS。\n完整块 fresh native 4 → 0；setup / hold −3.909029 / −0.587515 ns 仍失败。父层接入 / 完整规则 / 功能未通过或待验证。',fontsize=9.5,color='#56677d',linespacing=1.6)
    assets=out/'assets';fig.savefig(assets/'llsys_actual_via_tip_repair.png',dpi=180)
    p=assets/'llsys_actual_via_tip_repair.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-llsys-native-via-tip'}):fig.savefig(p,metadata={'Date':None})
    p.write_text('\n'.join(s.rstrip() for s in p.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    result={'scope':'ACTUAL_THREE_TARGET_NET_NATIVE_RECTANGLES_NOT_SCHEMATIC','full_qualification':False,
      'source_native_DRC_before_after':[4,0],'actual_rows_before_after':[862,854],
      'removed_WIRE_rectangles':8,'all_actual_vias_preserved':True,'signal_pins':13507,'changed_pin_XY':targets,
      'before_receipt_SHA256':hashlib.sha256(gzip.decompress(op.read_bytes())).hexdigest(),
      'after_receipt_SHA256':hashlib.sha256(gzip.decompress(cp.read_bytes())).hexdigest(),
      'after_ODB_SHA256':after['files']['routed.odb']['sha256'],'setup_hold_ns':[after['setup_ns'],after['hold_ns']],
      'not_drawn':['Other nets','PG','OBS'],'not_verified_by_figure':['Parent access','Complete rules','Function','System gains']}
    (out/'data/llsys_actual_via_tip_repair.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return result
