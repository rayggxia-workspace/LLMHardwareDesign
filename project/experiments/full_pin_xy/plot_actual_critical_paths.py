"""Actual extracted STA path increments; no invented route or zero-wire bound."""
from pathlib import Path
import gzip,hashlib,json
import expand_candidates as expand


def plot(snapshot,out):
    records=[]
    for case in ['vector','opentpu_aux']:
        folder=Path(snapshot)/'actual_path_audit/r01'/case
        p=folder/'execution.json.gz'
        if not p.exists():return None
        proof=json.loads(gzip.decompress(p.read_bytes()))
        assert proof['native_returncode']==0 and all(proof['source_worst_slacks_exactly_replayed'].values())
        raw=gzip.decompress((folder/'setup_paths.json.gz').read_bytes());paths=json.loads(raw)['checks']
        path=min(paths,key=lambda r:r['slack']);nodes=path['source_path'];cells=nets=0.;nc=nn=0
        for a,b in zip(nodes,nodes[1:]):
            delay=(b['arrival']-a['arrival'])*1e9;assert delay>=0
            if a.get('instance') and a.get('instance')==b.get('instance'):cells+=delay;nc+=1
            else:nets+=delay;nn+=1
        assert abs(cells+nets-(nodes[-1]['arrival']-nodes[0]['arrival'])*1e9)<1e-9
        records.append({'case':case,'startpoint':path['startpoint'],'endpoint':path['endpoint'],
          'cell_arc_increment_ns':cells,'net_arc_increment_ns':nets,'cell_arc_count':nc,'net_arc_count':nn,
          'launch_Q_arrival_ns':nodes[0]['arrival']*1e9,'endpoint_arrival_ns':nodes[-1]['arrival']*1e9,
          'required_time_ns':path['required_time']*1e9,'reported_JSON_rounded_slack_ns':path['slack']*1e9,
          'actual_setup_path_JSON_uncompressed_SHA256':hashlib.sha256(raw).hexdigest(),
          'interpretation':'Adjacent arrival increments from actual extracted STA JSON, rounded by tool; exclude launch clock/Q and required-time terms. Cell arcs include load/slew effects; not zero-wire bounds or isolated RC constants.'})
    result={'scope':'ACTUAL_EXTRACTED_STA_PATH_DIAGNOSIS_NOT_PHYSICAL_REPAIR_OR_WIRELESS_LOWER_BOUND',
      'paths':records,'full_qualification':False,'original_clock_constraints_unchanged':True}
    out=Path(out);(out/'data/actual_critical_path_diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    plt=expand.legacy.plt;fig,ax=plt.subplots(figsize=(13,5.6))
    fig.subplots_adjust(left=.19,right=.96,top=.76,bottom=.32)
    fig.text(.045,.93,'真实提取关键路径 | 延迟来自哪里',fontsize=20,weight='bold',color='#17283c')
    fig.text(.045,.85,'相同原SDC / 真实SPEF重放；统计发射Q至接收D或输出port，不包含发射时钟与required-time项。',fontsize=10,color='#56677d')
    colors=['#328aaa','#e5aa4c']
    for y,r in zip([1,0],records):
        a,b=r['cell_arc_increment_ns'],r['net_arc_increment_ns']
        ax.barh(y,a,height=.38,color=colors[0]);ax.barh(y,b,left=a,height=.38,color=colors[1])
        ax.text(a/2,y,f'{a:.3f}',ha='center',va='center',color='white',weight='bold')
        ax.text(a+b+.08,y,f'cell {r["cell_arc_count"]} 段 / net {r["net_arc_count"]} 段',va='center',fontsize=10,color='#56677d')
    ax.set_xlim(0,8.3);ax.set_ylim(-.6,1.6);ax.set_yticks([1,0],['VECTOR 成本ECO','openTPU SYSTEM 成本ECO'])
    ax.set_xlabel('相邻 arrival 增量之和 (ns)');ax.grid(axis='x',alpha=.18);ax.set_axisbelow(True)
    ax.barh([],[],color=colors[0],label='cell arc（含负载 / slew 影响）');ax.barh([],[],color=colors[1],label='net arc（当前提取STA）')
    ax.legend(loc='upper right',frameon=False,fontsize=9)
    fig.text(.045,.12,'VECTOR：141个cell arc约6.740ns；仅移动接口不能直接消除这条逻辑链，仍需保留失败并研究允许的物理修复。\nSYSTEM：net arc约1.052ns，其中末段到输出port约0.657ns；应进一步检查实际缓冲位置与接入绕行。\n数值来自工具舍入JSON；不等于独立RC常数、真实线长或无连线延迟下界。没有时序通过、面积收益或系统比较结论。',fontsize=10,color='#56677d',linespacing=1.7)
    assets=out/'assets';fig.savefig(assets/'actual_critical_path_diagnosis.png',dpi=180)
    dest=assets/'actual_critical_path_diagnosis.svg'
    with plt.rc_context({'svg.hashsalt':'issue126-extracted-critical-paths'}):fig.savefig(dest,metadata={'Date':None})
    dest.write_text('\n'.join(s.rstrip() for s in dest.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');plt.close(fig)
    return result
