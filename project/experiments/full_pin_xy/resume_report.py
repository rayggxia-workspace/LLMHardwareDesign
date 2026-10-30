"""Add resume evidence and a true-size LL repair zoom without claiming qualification."""
from pathlib import Path
import csv,gzip,hashlib,html,json,re,shutil
import numpy as np
import pandas as pd
import expand_candidates as expand


def read(p):
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())


def plot(root,out):
    plt,R=expand.legacy.plt,expand.legacy.Rectangle
    inputs=root/'trial-inputs-ll-local-patch-r01'
    revision=read(inputs/'revision.json');old=pd.read_csv(root/'trial-inputs-llsys-pg-r03/llaccel_aux_C_pg_r03_all_pins.csv',low_memory=False).set_index('pin')
    new=pd.read_csv(inputs/'llaccel_aux_C_local_patch_r01_all_pins.csv',low_memory=False).set_index('pin')
    assert len(old)==len(new)==13507 and set(old.index)==set(new.index)
    names=[r['pin'] for r in revision['changes']];assert len(names)==3
    for key in ['layer','direction','net','use']:assert old[key].equals(new[key])
    assert set(old.index[(abs(old.x_um-new.x_um)>1e-8)|(abs(old.y_um-new.y_um)>1e-8)])==set(names)
    drc=root/'terminal_updates/LLPG-r01/finalized/llsys-pg-r03/llaccel_aux-C/independent.drc.gz'
    boxes={n:[] for n in names};native=gzip.decompress(drc.read_bytes()).decode()
    for block in native.split('violation type:')[1:]:
        hit=re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\)',block);assert hit
        for n in names:
            if re.search(r'net:'+re.escape(n)+r'(?:\s|$)',block):boxes[n].append(tuple(map(float,hit.groups())))
    assert sorted(map(len,boxes.values()))==[1,1,2]
    assert read(root/'llaccel_aux.meta.json')['units_per_micron']==2000
    pg={n:[] for n in names}
    for chunk in pd.read_csv(root/'physical/llaccel_aux/shapes.tsv.gz',sep='\t',chunksize=250000):
        q=chunk[chunk.kind.str.startswith('pg')]
        for n in names:
            a,b=old.loc[n],new.loc[n];cx=(a.x_um+b.x_um)/2;cy=(a.y_um+b.y_um)/2
            for _,r in q[(q.layer==a.layer)&(q.x0/2000<cx+1.1)&(q.x1/2000>cx-1.1)&(q.y0/2000<cy+1.1)&(q.y1/2000>cy-1.1)].iterrows():
                pg[n].append(np.array([r.x0,r.y0,r.x1,r.y1])/2000)
    fig,axes=plt.subplots(1,3,figsize=(18,8.2));fig.subplots_adjust(left=.055,right=.98,top=.78,bottom=.24,wspace=.26)
    fig.text(.04,.95,'llaccel SYSTEM | 三处局部 XY 修复与实际失败证据',fontsize=21,weight='bold',color='#17283c')
    fig.text(.04,.89,'完整13,507 pin / 13,184个内部移动保留；只增量修订3点。92747实际 DRT 因另一未移动 pin bit_4812 无接入点失败。',fontsize=10,color='#56677d')
    for ax,n in zip(axes,names):
        a,b=old.loc[n],new.loc[n];cx=(a.x_um+b.x_um)/2;cy=(a.y_um+b.y_um)/2
        for x,y,u,v in pg[n]:ax.add_patch(R((x,y),u-x,v-y,fc='#ddac69',alpha=.7,ec='none'))
        for r,color,label in [(a,'#0072b2','原实际 C pin'),(b,'#d55e00','proposed 修订 pin')]:
            ax.add_patch(R((r.x0_um,r.y0_um),r.x1_um-r.x0_um,r.y1_um-r.y0_um,fill=False,ec=color,lw=1.7,label=label,zorder=4))
        for i,(x,y,u,v) in enumerate(boxes[n]):
            ax.add_patch(R((x,y),u-x,v-y,fc='#c94343',ec='#c94343',alpha=.5,lw=1.2,label='原生 DRC marker bbox' if i==0 else None,zorder=5))
        ax.annotate('',xy=(b.x_um,b.y_um),xytext=(a.x_um,a.y_um),arrowprops={'arrowstyle':'->','color':'#d55e00','linestyle':'--','lw':1})
        bus=next(r['semantic_mapping'] for r in revision['changes'] if r['pin']==n)
        ax.set_title(n+' / '+a.layer+'\n'+bus['semantic_bus']+'['+str(bus['semantic_bit'])+']',loc='left',fontsize=11,weight='bold')
        ax.set(xlim=(cx-1.1,cx+1.1),ylim=(cy-1.1,cy+1.1),xlabel='X (μm)',ylabel='Y (μm)');ax.set_aspect('equal');ax.grid(alpha=.12)
        ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=8)
    axes[0].legend(loc='lower left',fontsize=8,framealpha=.95)
    fig.text(.04,.07,'三图使用相同2.2 × 2.2 μm窗口和比例；pin矩形按真实0.14 × 0.14 μm尺寸绘制，边线仅用于显示。金色为该层真实固定PG。\n红色是旧版原生DRC诊断范围，不是通孔或金属尺寸；虚线箭头只表示XY位移，不是真实走线。未显示其余信号、via与OBS，背景不等于可用区域。\n旧版4项DRC失败保留；三点修复未完成详细布线，不能声称新位置通过。完整接入窗口方案92690/92691是另一独立试验。',fontsize=10,color='#56677d')
    fig.savefig(out/'assets/llsys_local_repair_attempt.png',dpi=180)
    with plt.rc_context({'svg.hashsalt':'issue126-resume'}):fig.savefig(out/'assets/llsys_local_repair_attempt.svg',dpi=180,metadata={'Date':None})
    svg=out/'assets/llsys_local_repair_attempt.svg';svg.write_bytes(b'\n'.join(line.rstrip(b' \t\r') for line in svg.read_bytes().splitlines())+b'\n')
    plt.close(fig)
    source_paths=[drc,inputs/'revision.json',inputs/'llaccel_aux_C_local_patch_r01_all_pins.csv',
                  root/'trial-inputs-llsys-pg-r03/llaccel_aux_C_pg_r03_all_pins.csv',root/'physical/llaccel_aux/shapes.tsv.gz']
    record={'scope':'ACTUAL_OLD_PIN_FIXED_PG_NATIVE_MARKERS_AND_PROPOSED_NEW_PIN_NOT_ROUTED_PASS',
            'input_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
            'scale_um':[2.2,2.2],'pin_shape_um':[.14,.14],'via_footprint':'NOT_DISPLAYED',
            'arrow':'XY_displacement_only_not_route','full_qualification':False}
    (out/'data/continuation/resume/llsys_local_repair_figure_sources.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')


def render(root,out):
    root,out=Path(root),Path(out);sources=sorted((root/'resume_evidence').glob('resume-*'))
    if not sources:return ''
    snapshot=sources[-1];dest=out/'data/continuation/resume'/snapshot.name
    manifest=read(snapshot/'snapshot.json');assert not manifest['full_qualification']
    for r in manifest['records']:
        if r['storage']!='LOSSLESS_SNAPSHOT':continue
        p=snapshot/r['relative'];stored=p.read_bytes();raw=gzip.decompress(stored)
        assert hashlib.sha256(stored).hexdigest()==r['stored_sha256'] and hashlib.sha256(raw).hexdigest()==r['sha256']
        assert len(raw)==r['source_bytes']
    shutil.copytree(snapshot,dest,dirs_exist_ok=True)
    inputs=root/'trial-inputs-ll-local-patch-r01';target=out/'data/continuation/inputs/ll-local-patch-r01';target.mkdir(parents=True,exist_ok=True)
    for p in inputs.iterdir():
        if not p.is_file():continue
        with (target/(p.name+'.gz')).open('wb') as f,gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as stream:stream.write(p.read_bytes())
    profiles=[]
    for case,label in [('ll_original','LL原始'),('ll_pg_full_C','LL PG修订C'),('gemm_access','GEMM接入窗口C'),('mxu_access','MXU接入窗口C')]:
        p=snapshot/'constraint_audit/r05'/case/'NDR_wire_width_profiles.tsv.gz'
        if not p.exists():continue
        with gzip.open(p,'rt') as f:rows=list(csv.DictReader(f,delimiter='\t'))
        count=sum(int(r['shape_count']) for r in rows);under=sum(int(r['shape_count']) for r in rows if r['NDR_nominal_width_dbu']!='UNKNOWN' and int(r['min_box_dimension_dbu'])<int(r['NDR_nominal_width_dbu']))
        profiles.append('<tr><td>'+label+'</td><td>'+str(count)+'</td><td>'+str(under)+'</td></tr>')
    plot(root,out)
    link='data/continuation/resume/'+snapshot.name+'/'
    eco_rows=[]
    for case,revision in [('gemm','r03'),('mxu','r04')]:
        relative='leaf_eco/'+revision+'/'+case+'-C/';p=snapshot/relative/'execution.json.gz'
        if not p.exists():continue
        j=read(p)
        if not j.get('completed_utc'):continue
        cost=j.get('separate_cell_ECO_cost',{});delta=cost.get('standard_cell_master_bbox_area_after_um2',0)-cost.get('standard_cell_master_bbox_area_before_um2',0)
        def slack(kind):
            q=snapshot/relative/(kind+'.txt.gz')
            if not q.exists():return '未知'
            m=re.search(r'worst slack (?:min|max)\s+([-\d.]+)',gzip.decompress(q.read_bytes()).decode());return m[1] if m else '未知'
        eco_rows.append('<tr><td><a href="'+link+relative+'execution.json.gz">'+case.upper()+' '+revision+'</a></td><td>'+str(j.get('fresh_DRC_count'))+'</td><td>'+str(j.get('whole_signal_geometry',{}).get('pass'))+'</td><td>'+slack('setup')+' / '+slack('hold')+'</td><td>'+str(cost.get('changed_master_original_instances'))+'</td><td>+'+format(delta,'.3f')+'</td></tr>')
    eco_table=('<h3>定点ECO已收齐的实际终态（不替换纯XY对照）</h3><table><thead><tr><th>版本/原文</th><th>fresh native DRC</th><th>所检全块连通</th><th>setup / hold ns</th><th>换型单元数</th><th>标准单元bbox面积增量 μm²</th></tr></thead><tbody>'+''.join(eco_rows)+'</tbody></table><p>两块本版本的report_check_types均未列违例，原层/全部pin/PG/外框不变、宏资源位置不变；均需完整规则与设计形式等价。填充单元拆装计数不当功能单元增减或面积节省。92757整个Slurm为失败是并行MXU前置Lib读取失败所致，GEMM子试验须按其独立终态回执判定，不能用批作业状态替代每个block结果。</p>') if eco_rows else ''
    exported=[]
    for case,count in [('gemm',3753),('mxu',2172)]:
        relative='eco_views/r02/'+case+'-C/execution.json.gz';p=snapshot/relative
        if not p.exists():continue
        j=read(p)
        if j.get('completed_utc') and j.get('native_export_returncode')==0:
            assert j['matching_all_signal_model_pins']==count and j['SPEF_replay_matches_source'] and j['pre_RCX_geometry_and_all_sources_unchanged']
            assert not j['full_qualification']
            exported.append('<a href="'+link+relative+'">'+case.upper()+': '+str(count)+' bit及方向、物理/研究时序视图、SPEF重放匹配</a>')
    view_status='<p><b>新增视图已取得终态：</b>'+ '；'.join(exported)+'。原预RCX ODB哈希保持、全部signal/PG pin及外框一致、默认与详细OBS视图一致性检查通过。没有完整设计形式等价、SRAM器件表征或完整制造规则通过证据。</p>' if exported else ''
    return '''<section class="card" id="resume20261028"><h2>10月28日晚接续：真实修复、约束审计及失败保留</h2>
<p>用户要求继续执行后，先核对PR129仍open/draft及28a2c93 head、本人活动作业和实际终态，未重做既有候选或合并PR。随后新增三点局部实际重接线、定点驱动增强及估算器修复；下列提交/运行均不代表物理资格。</p>
<h3>LL SYSTEM：完整接口保留，三点修复实际未成功</h3>
<p>在真实PG修订C（native DRC4失败、725253网所检连通通过）上，只移动bit_1382013、bit_6907、bit_1389626；对应真实gemm_w_rdata[391]、bank_rdata[1409]、vec_rd0_rdata[498]，均为读数据，无关联strobe。其余13504点不改，原层/方向/尺寸/网络/逐bit语义不改，13184内部移动仍保留。</p>
<p><b>92747已实际失败：</b>增量GRT执行后，DRT报DRT-1231：未移动的输出bank_wdata[1362]（bit_4812，M6，957.6/1249.36μm）无access point。92748只返回NO_COMPLETED_ROUTE，不是独立检查通过。保留此失败，完整窗口92690/92691仍是不同候选/布线试验，不能把任何一者替代另一者。<a href="data/continuation/inputs/ll-local-patch-r01/llaccel_aux_C_local_patch_r01_all_pins.csv.gz">全部13507点新表</a>；<a href="'''+link+'''snapshot.json">原生证据及SHA索引</a>。</p>
<figure><img loading="lazy" src="assets/llsys_local_repair_attempt.png" alt="LL三点修复：真实PG、旧pin、原生DRC范围和proposed点；实际DRT仍失败"><figcaption>实际几何与proposed分开。未显示金属不等于空白；箭头不是布线路径。<a href="assets/llsys_local_repair_attempt.svg">SVG</a></figcaption></figure>
<h3>NDR：数据库规则、实际矩形宽度与未检条件分开</h3>
<p>只读审计92749/92751/92752的接口/查询失败保留；92753及92759成功读取所有四份源ODB，源SHA不变。LL原始与PG修订C的28条NDR网名及规则关联逐字节相同；CTS_NDR_0原本hard_spacing=0。安装镜像未带匹配GRT源码，不能仅凭警告推断其内存处理或完整NDR通过。</p>
<table><thead><tr><th>实际视图</th><th>有NDR网的常规wire矩形数</th><th>短边小于该层NDR名义宽度</th></tr></thead><tbody>'''+''.join(profiles)+'''</tbody></table>
<p>此处没有发现被统计矩形的宽度不足；不含via、端点缩颈例外、NDR spacing、所有时钟网或实时92690内存状态检查。最终仍须读取其实际终态ODB并做完整检查；没有修改软间距属性或删掉NDR。</p>
<h3>GEMM/MXU定点电气修复与VECTOR/SYSTEM时序修复</h3>
<p>原GEMM三项cap及MXU一项cap失败继续保留。实际驱动与dont-touch已查：BUF_X1、XOR2_X1、DFFR_X1和BUF_X1，均未锁定。92757（GEMM r03）、92758（MXU r04）分别将这些实际单元换到X2，并核对Liberty逻辑/触发器状态、原端口网络不变；恢复原类型填充并增量重布线。92761为MXU读取/绑定路径改进后的同配置复测，不当作独立XY方案或新增收益。它们是单列成本ECO，不是纯XY改善，也没有完整设计形式等价资格。</p>
<p>此前read_guides使resizer出现EST-0027、用wire-load模型；不能把旧优化过程说成按提取RC修复。92762先用原SPEF准确复现VECTOR和openSYS的setup/hold，随后在估算状态切换后EST-0104失败。92767显式切回放置估算后，VECTOR仍报EST-0104；openSYS完成单元修复，协商合法化迭代降到0个非法单元，随后工具Signal11崩溃。保留失败，不把合法化中间计数写成最终检查通过，也不把SPEF状态作为已完全查明的唯一原因。</p>
<p>92770的新r08改为重新建立原生GRT几何模型再估算，而非仅读取guide；SYSTEM采用工具支持的diamond合法化且保留check_placement，并在单元修复后保存独立检查点。原SDC不改，openSYS仍仅M2–M8/clock M4–M8。最终只能由新详细布线、RCX及STA判定，不用估算slack宣布通过。方法参考<a href="https://openroad.readthedocs.io/en/latest/main/src/est/README.html">OpenROAD寄生估算</a>及<a href="https://openroad.readthedocs.io/en/latest/main/src/grt/README.html">GRT官方说明</a>，最新版文档不当作本镜像版本证明。</p>
<p>r08的VECTOR仍EST-0104，openSYS保存真实单元修复检查点后仍在合法化阶段Signal11。92775将VECTOR的精确源SPEF重放与修复拆到独立原生进程，仍EST-0104失败；因此“SPEF导入状态残留”未获证明，不能宣称根因已经解决。92778复用SYSTEM检查点时，前置脚本错误要求存在CORE_SPACER而失败，未调用合法化；实际原始清单为423453 CORE、15378 CORE_WELLTAP、21 BLOCK，没有CORE_SPACER。92780保留原本无spacer的事实、固定原macro/welltap坐标朝向后独立合法化，恢复原状态再检查，不重复单元修复，现已原生命令/放置检查执行成功且pin/PG/die不变；产物仍明确NOT_ROUTED。</p>
<p>随后92781从该已检查放置继续实际完整信号/时钟重布线、双PG、RCX、STA及独立native DRC。脚本先从原源ODB独立导出OBS对象ID与几何，逐项核对检查点新增OBS恰为原接入窗口，详细布线后只移除这些临时约束；不删除原OBS、master OBS或PDN，不放宽原M2–M8/clock M4–M8及SDC。提交/运行不是布线或时序通过，按实际终态更新。</p>
'''+eco_table+'''
<p>92773/92774已实际导出新的物理LEF/DEF/网表，但因漏挂载原SDC目录而在时序模型阶段失败，原目录/日志保留。92776/92777在独立eco_views/r02只读补挂原始材料，重新导出匹配同一预RCX ODB/SPEF的物理/时序视图；须检查实际终态、逐bit模型方向和SPEF重放后再使用。物理/研究时序视图不提升为器件表征、制造签核或完整功能等价。</p>
'''+view_status+'''
<p>两份新ECO视图的严格GDS合并及原有完整FreePDK45 deck另以92783继续，远程streamout/costed-r01，单列C_ECO、不混入纯XY收益。缺SRAM GDS仍按实际合并失败记录，allow-empty保持禁用；不伪造宏几何，不改原deck或删除WELL、天线、包围等检查。该阶段尚无通过结论。</p>
<p>ACT另一个2.4μm临时避让版本92707已native0、860网/1720端点连通和双PG通过（escape_spacing_reroute/r03）；1.6μm版本92706仍两项spacing失败。已成功的92719接点修复继续保留，互不覆盖。</p>
<p><a href="'''+link+'''scheduler.tsv">此次调度状态快照</a>（'''+html.escape(manifest['created_utc'])+'''）；RUNNING/PENDING不是完成。仍无合格六块、共同M1–M10实际预连/冻结、两完整M11/M12功能或端到端系统收益结论。缺失匹配SRAM GDS、完整适用规则及原历史handoff层映射继续明确保留。</p></section>'''
