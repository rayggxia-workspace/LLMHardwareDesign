"""Actual failed SYSTEM net geometry and native markers, never a free-space map."""
from pathlib import Path
import csv,gzip,hashlib,io,json,re
import expand_candidates as expand


def plot(snapshot,out):
    folder=Path(snapshot)/'actual_path_audit/r02/opentpu_aux'
    receipt=folder/'execution.json.gz'
    if not receipt.exists():return None
    proof=json.loads(gzip.decompress(receipt.read_bytes()))
    assert proof['native_returncode']==0 and proof['all_sources_unchanged']
    assert proof['source_kind']=='system_existing_buffers_r02' and all(proof['source_worst_slacks_exactly_replayed'].values())
    compressed=gzip.decompress((folder/'fresh_DRC_target_net.tsv.gz.gz').read_bytes())
    assert hashlib.sha256(compressed).hexdigest()==proof['files']['fresh_DRC_target_net.tsv.gz']['sha256']
    raw=gzip.decompress(compressed);rows=list(csv.DictReader(io.StringIO(raw.decode()),delimiter='\t'))
    assert rows and {r['net'] for r in rows}=={'_215139_'}
    source=Path(snapshot)/'output_chain_resume/r02/opentpu_aux-C'
    source_proof=json.loads(gzip.decompress((source/'execution.json.gz').read_bytes()))
    assert source_proof['fresh_DRC_count']==2
    assert proof['source_SHA'][proof['actual_source_directory']+'/routed.odb']==source_proof['files']['routed.odb']['sha256']
    drc=gzip.decompress((source/'independent.drc.gz').read_bytes()).decode()
    matches=re.findall(r'violation type: ([^\n]+)\n\s*srcs: net:_215139_\n\s*bbox = \(([-.\d]+), ([-.\d]+)\) - \(([-.\d]+), ([-.\d]+)\) on Layer (\w+)',drc)
    assert len(matches)==2 and all(m[-1]=='metal2' for m in matches)
    markers=[{'native_type':m[0],'bbox_um':list(map(float,m[1:5])),'layer':m[-1]} for m in matches]
    out=Path(out);data=out/'data';table=io.StringIO();writer=csv.DictWriter(table,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    data.joinpath('system_actual_M2_net_rectangles.csv').write_text(table.getvalue(),encoding='utf-8',newline='\n')
    paths=[]
    for kind in ['setup','hold']:
        raw_path=gzip.decompress((folder/(kind+'_paths.json.gz')).read_bytes())
        path=min(json.loads(raw_path)['checks'],key=lambda r:r['slack']);nodes=path['source_path']
        totals={'cell_arc_ns':0.,'net_arc_ns':0.};counts={'cell_arc_count':0,'net_arc_count':0}
        for a,b in zip(nodes,nodes[1:]):
            delay=(b['arrival']-a['arrival'])*1e9;assert delay>=0
            cell=bool(a.get('instance')) and a.get('instance')==b.get('instance')
            totals['cell_arc_ns' if cell else 'net_arc_ns']+=delay;counts['cell_arc_count' if cell else 'net_arc_count']+=1
        paths.append(dict(kind=kind,startpoint=path['startpoint'],endpoint=path['endpoint'],source_text_slack_ns=source_proof[kind+'_ns'],JSON_rounded_slack_ns=path['slack']*1e9,source_path_uncompressed_SHA256=hashlib.sha256(raw_path).hexdigest(),**totals,**counts))
    result={'scope':'ACTUAL_ONE_FAILED_NET_RECTANGLES_AND_CURRENT_SPEF_PATH_DIAGNOSIS_NOT_REPAIR_OR_WHOLE_NEIGHBOR_DRC',
      'source_native_DRC_count':2,'actual_native_markers':markers,'actual_rectangle_rows':len(rows),'paths':paths,
      'source_receipt_uncompressed_SHA256':hashlib.sha256(gzip.decompress(receipt.read_bytes())).hexdigest(),
      'source_routed_ODB_SHA256':source_proof['files']['routed.odb']['sha256'],
      'source_SPEF_SHA256':source_proof['files']['extracted.spef']['sha256'],'DBU_per_um':2000,
      'full_qualification':False,'plot_contains_other_nets_PDN_or_all_OBS':False,
      'arc_interpretation':'Adjacent arrival increments excluding clock and required-time terms; actual load/slew effects retained, not wireless lower bounds, isolated RC or real wirelength.'}
    data.joinpath('system_actual_M2_and_current_paths.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    plt=expand.legacy.plt;Rectangle=expand.legacy.Rectangle
    fig,axes=plt.subplots(1,2,figsize=(12.4,6.8));fig.subplots_adjust(left=.07,right=.96,top=.78,bottom=.25,wspace=.22)
    fig.text(.045,.94,'SYSTEM 实际路由 | 同一网络的 M2 报项',fontsize=20,weight='bold',color='#17283c')
    fig.text(.045,.88,'源：output_chain_resume/r02；fresh native DRC 2；原SDC / SPEF精确重放，仍setup / hold失败。',fontsize=10,color='#56677d')
    colors={'metal1':'#a9b9c9','metal2':'#328aaa','metal3':'#e5aa4c'}
    for ax in axes:
        ax.set_aspect('equal');ax.set_xlabel('x (μm)');ax.set_ylabel('y (μm)');ax.ticklabel_format(useOffset=False,style='plain');ax.grid(alpha=.15);ax.set_axisbelow(True)
    for q in rows:
        if q['layer'] not in colors:continue
        x0,y0,x1,y1=[int(q[k])/2000 for k in ['x0','y0','x1','y1']]
        axes[0].add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor=colors[q['layer']],edgecolor=colors[q['layer']],alpha=.43,lw=.6,hatch='//' if q['kind']=='ITERM' else None))
        if q['layer']=='metal2':
            color='#e5aa4c' if q['kind']=='VIA' else '#328aaa'
            axes[1].add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor=color,edgecolor=color,alpha=.48,lw=.7))
    for ax in axes:
        for m in markers:
            x0,y0,x1,y1=m['bbox_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,edgecolor='#bf514c',lw=1.2,ls='--'))
    axes[0].set(xlim=(2033.10,2034.60),ylim=(1197.05,1198.55),title='实际整条网：M1 / M2 / M3与端点')
    axes[1].set(xlim=(2033.16,2033.40),ylim=(1197.35,1197.81),title='M2 局部放大（相同实际坐标）')
    axes[0].legend([Rectangle((0,0),1,1,facecolor=c,alpha=.5) for c in colors.values()],['M1','M2','M3'],fontsize=8,loc='upper right',frameon=False)
    axes[1].legend([Rectangle((0,0),1,1,facecolor=c,alpha=.5) for c in ['#328aaa','#e5aa4c']],['M2 wire','M2 via landing'],fontsize=8,loc='upper right',frameon=False)
    fig.text(.045,.06,'只绘真实网 _215139_ 的原生矩形；空白不代表周围无异网、PDN或OBS。端点斜线为真实ITerm矩形。\n红框为两项原生DRC bbox；线框粗细用于显示，不是新增金属、pin或通孔尺寸。\nM2 via landing取自实际via定义；这张图不证明修复通过、完整规则通过或面积/时序收益。',fontsize=10,color='#56677d',linespacing=1.7)
    assets=out/'assets';fig.savefig(assets/'system_actual_M2_conflict.png',dpi=180)
    dest=assets/'system_actual_M2_conflict.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-actual-system-M2'}):fig.savefig(dest,metadata={'Date':None})
    dest.write_text('\n'.join(s.rstrip() for s in dest.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    return result
