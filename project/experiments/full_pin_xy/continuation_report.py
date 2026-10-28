"""Publish continuation receipts and true/proposed geometry without merging stages."""
from pathlib import Path
import csv, gzip, hashlib, html, json, shutil
import numpy as np
import pandas as pd
import expand_candidates as expand

CASES=['act','mxu','opentpu_aux','gemm','vector','llaccel_aux']
COUNTS=dict(zip(CASES,[860,2172,2229,3753,2246,13507]))


def read(p):
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())


def gzcopy(p,d):
    d.parent.mkdir(parents=True,exist_ok=True)
    with d.open('wb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:f.write(p.read_bytes())


def stage_native(snapshot,dest):
    """Keep useful native text byte-exact; large geometry remains SHA-indexed."""
    dest.mkdir(parents=True,exist_ok=True)
    manifest=read(snapshot/'snapshot.json')
    gzcopy(snapshot/'snapshot.json',dest/'remote_snapshot_index.json.gz')
    for r in manifest['records']:
        if r['storage']!='LOSSLESS_SNAPSHOT':continue
        p=snapshot/r['relative'];name=p.name
        geometry=any(t in name for t in ['.cells.tsv','.pdn.tsv','whole_access.tsv','selected_access.tsv']) or name.endswith('.lef.gz') or name.startswith('timing.selected_')
        keep=(not geometry and p.stat().st_size<2*1024*1024) or str(r['relative']).startswith('upper_layer_')
        if keep:
            d=dest/r['relative'];d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
        else:
            r['storage']='REMOTE_SNAPSHOT_ONLY'
            r['remote_snapshot_file']=manifest['source_root']+'/continuation_snapshots/'+snapshot.name+'/'+r['relative']
            r['publication_note']='Large native geometry/text retained in immutable remote snapshot and local task work; original and compressed SHA remain indexed. Not deleted or reported as passed.'
    manifest['publication_scope']='Curated native evidence; exact original snapshot index in remote_snapshot_index.json.gz. Large physical evidence is remote SHA-indexed.'
    (dest/'snapshot.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


def frame(fig,title,subtitle):
    fig.text(.04,.955,title,fontsize=21,weight='bold',color='#17283c')
    fig.text(.04,.90,subtitle,fontsize=10,color='#56677d')


def save(fig,assets,name):
    for ext in ['png','svg']:fig.savefig(assets/(name+'.'+ext),dpi=180)
    expand.legacy.plt.close(fig)


def plot_upper(root,assets):
    plt,R=expand.legacy.plt,expand.legacy.Rectangle
    source=root/'upper_layer_probe/r01/access.tsv'
    d=pd.read_csv(source,sep='\t');fig,axes=plt.subplots(1,2,figsize=(15,8.4))
    fig.subplots_adjust(left=.065,right=.98,top=.81,bottom=.22,wspace=.2)
    frame(fig,'研究 M11 / M12 | 已实际布线的原生小例','2 nets / 4 ports；独立读回 native DRC = 0，所检几何连通通过。不是完整系统或共同底座。')
    colors={'a':'#0072b2','b':'#d55e00'}
    for ax in axes:
        for _,r in d.iterrows():
            if r.layer=='UNROUTED':continue
            x,y,u,v=np.array([r.x0,r.y0,r.x1,r.y1],float)/2000
            if str(r.layer).startswith('via'):
                face='#17283c';z=4
            else:face=colors[r.net];z=2
            ax.add_patch(R((x,y),u-x,v-y,fc=face,ec='none',alpha=.8,zorder=z))
            if r.kind=='BTERM':ax.text((x+u)/2,(y+v)/2+2,r.net+' / M10',fontsize=9,color=colors[r.net],ha='center')
        ax.set_aspect('equal');ax.set_xlabel('X (μm)');ax.set_ylabel('Y (μm)');ax.grid(alpha=.1)
    axes[0].set(xlim=(0,110),ylim=(0,110));axes[0].set_title('A. actual ODB rectangles',loc='left',weight='bold')
    # The actual bottom-left contact, not a hand-drawn via icon.
    bt=d[d.kind=='BTERM'].iloc[0];x=(bt.x0+bt.x1)/4000;y=(bt.y0+bt.y1)/4000
    axes[1].set(xlim=(x-3,x+6),ylim=(y-3,y+6));axes[1].set_title('B. actual M10–M12 stack zoom',loc='left',weight='bold')
    fig.text(.04,.055,'实心矩形均为真实 ODB 导出：蓝=a、橙=b，深色=cut；按真实尺寸绘制，没有示意路径。\nM11/M12规则复制原M9/M10完整PRL表：宽0.8μm、pitch1.6μm；via10/11 cut0.8μm、间距0.88μm，LEF零包围为研究假设。\n层高/RC为外推，尚无12层校准RCX、完整制造DRC或两套功能实现；单个小例通过不代表完整技术资格。',fontsize=10,color='#56677d')
    save(fig,assets,'research_upper_actual')


def plot_pg(root,assets):
    plt,R=expand.legacy.plt,expand.legacy.Rectangle
    a=pd.read_csv(root/'llaccel_aux_pin_coordinates.csv',low_memory=False);a=a[a.plan=='C'].set_index('pin')
    c=pd.read_csv(root/'trial-inputs-llsys-pg-r03/llaccel_aux_C_pg_r03_all_pins.csv',low_memory=False).set_index('pin').loc[a.index]
    proof=read(root/'ll-fullC-actual-fixed-PG-proof-r01/proof.json');contacts=proof['contacts'];pins=sorted({q['pin'] for q in contacts});assert len(pins)==26
    chosen=contacts[0]['pin'];old=a.loc[chosen];new=c.loc[chosen];center=np.array([(old.x_um+new.x_um)/2,(old.y_um+new.y_um)/2])
    fig,axes=plt.subplots(1,3,figsize=(18,8.3));fig.subplots_adjust(left=.045,right=.98,top=.80,bottom=.26,wspace=.25)
    frame(fig,'llaccel SYSTEM | 固定 PG 直接接触修订','全部13,507信号pin保留，13,184个仍在内部；实际place_pin回读匹配、PG指纹不变。完整布线/DRC另行验收。')
    axes[0].scatter(c.x_um,c.y_um,c=np.where(c.layer=='metal5','#0072b2','#b47bac'),s=1.4,alpha=.5)
    axes[0].scatter(c.loc[pins].x_um,c.loc[pins].y_um,s=18,facecolor='none',edgecolor='#d55e00')
    axes[0].set(xlim=(-20,2120),ylim=(-20,2120));axes[0].set_title('A. 全部 pin；圈出26个修订点',loc='left',fontsize=11,weight='bold')
    layer=old.layer
    shapes=[]
    for chunk in pd.read_csv(root/'physical/llaccel_aux/shapes.tsv.gz',sep='\t',chunksize=250000):
        q=chunk[(chunk.layer==layer)&chunk.kind.str.startswith('pg')]
        for _,r in q.iterrows():
            # Export is in DBU; plot only actual geometry near this zoom.
            b=np.array([r.x0,r.y0,r.x1,r.y1],float)/2000
            if b[0]<center[0]+13 and b[2]>center[0]-13 and b[1]<center[1]+13 and b[3]>center[1]-13:shapes.append(b)
    for ax,d,title in zip(axes[1:],[a,c],['B. 原完整 C：26 pin / 44接触对','C. PG修订：实际直接接触0']):
        for x,y,u,v in shapes:ax.add_patch(R((x,y),u-x,v-y,fc='#ddac69',ec='none',alpha=.75))
        near=d[(abs(d.x_um-center[0])<13)&(abs(d.y_um-center[1])<13)&(d.layer==layer)]
        for pin,r in near.iterrows():
            ax.add_patch(R((r.x0_um,r.y0_um),r.x1_um-r.x0_um,r.y1_um-r.y0_um,fc='#0072b2',ec='none',zorder=4))
            if pin==chosen:ax.scatter(r.x_um,r.y_um,s=95,facecolor='none',edgecolor='#d55e00',zorder=5);ax.annotate(pin,(r.x_um,r.y_um),xytext=(5,10),textcoords='offset points',fontsize=8)
        ax.set(xlim=(center[0]-12,center[0]+12),ylim=(center[1]-12,center[1]+12));ax.set_title(title,loc='left',fontsize=11,weight='bold')
    for ax in axes:ax.set_aspect('equal');ax.set_xlabel('X (μm)');ax.set_ylabel('Y (μm)');ax.grid(alpha=.1)
    fig.text(.04,.065,'总览点/圈为显示标记，不是pin/via尺寸；放大图蓝色信号矩形及金色PG按真实尺寸绘制，仅显示所选'+layer+'。\n26个原始接触pin按实际PG、OBS和分束局部修订，原功能/方向/网络/层/矩形尺寸保持；未删任何常量或声明位。\n“直接接触0”只说明同层pin矩形与固定PG不相交；不代替via接入、间距、完整DRC、RC/STA及父层可达性检查。',fontsize=10,color='#56677d')
    save(fig,assets,'llsys_pg_revision')


def plot_common(root,assets):
    plt,R=expand.legacy.plt,expand.legacy.Rectangle
    prep=root/'common-base-preparation-r04';p=pd.read_csv(prep/'common_floorplan.csv');w=pd.read_csv(prep/'shared_prewire_geometry.csv');contract=read(prep/'preparation_contract.json')
    fig,axes=plt.subplots(1,2,figsize=(18,9.6),gridspec_kw={'width_ratios':[1.15,1]});fig.subplots_adjust(left=.055,right=.98,top=.80,bottom=.23,wspace=.22)
    frame(fig,'六块资源并集 | 共同底座准备方案（proposed）','两功能计划使用相同256个有限M10导体；尚无共同底座实际布线、冻结manifest或两套M11/M12实现。')
    colors={'opentpu':'#d9eaf4','llaccel':'#d6eee4'}
    for _,r in p.iterrows():
        axes[0].add_patch(R((r.x_um,r.y_um),r.width_um,r.height_um,fc=colors[r.enabled_in],ec='#52667d'))
        x,y=r.x_um+r.width_um/2,r.y_um+r.height_um/2
        label=expand.TITLES[r['case']].replace(' ','\n')+'\n'+str(COUNTS[r['case']])+' pins'
        if r['case']=='act':
            axes[0].annotate('openTPU ACT · 860 pins',(x,y),xytext=(x,y+650),ha='center',fontsize=9,
                             arrowprops={'arrowstyle':'-','color':'#52667d','lw':.6})
        else:axes[0].text(x,y,label,ha='center',va='center',fontsize=9.5)
    for ax in axes:
        for _,r in w.iterrows():ax.add_patch(R((r.x0_um,r.y0_um),r.x1_um-r.x0_um,r.y1_um-r.y0_um,fc='#8b6bb1',ec='none'))
        ax.set_aspect('equal');ax.set_xlabel('X (μm)');ax.set_ylabel('Y (μm)');ax.grid(alpha=.1)
    axes[0].set(xlim=(0,contract['frame_um'][2]),ylim=(0,contract['frame_um'][3]));axes[0].set_title('A. 交错六块；固定预连仍待实现',loc='left',weight='bold')
    axes[1].set(xlim=(w.x0_um.min()-6,w.x1_um.max()+6),ylim=(w.y0_um.min()-10,w.y1_um.min()+42));axes[1].set_title('B. 1组32个拟议M10导体放大',loc='left',weight='bold')
    fig.text(.04,.065,'紫色为proposed有限导体矩形：每段宽0.8μm、中心线长32μm、中心距3.2μm；共8组×32段，预算8192μm。尚未写入物理数据库。\nopenTPU绑定原ACT→MXU的r_data[0:255]；llaccel绑定原SYSTEM→GEMM的gemm_a_rdata[0:255]，是研究切分，不是新lane。\n保持原六块及完整逐bit语义；新闲置时钟/常量/外部接入基础设施仍待实现。宏轮廓外走廊不能证明PG/上层金属可用。\nR0位置取11.2μm整数倍保留0.28/0.8/1.6μm轨道相位；未缩小框，不报告面积收益。',fontsize=10,color='#56677d')
    save(fig,assets,'common_base_proposed')


def render(root,out):
    root,out=Path(root),Path(out);snapshots=sorted((root/'continuation_evidence').glob('milestone-*'))
    if not snapshots:return ''
    snapshot=snapshots[-1];dest=out/'data/continuation';dest.mkdir(exist_ok=True)
    stage_native(snapshot,dest/'native'/snapshot.name)
    for name in ['common-base-preparation-r04','llsys-pg-r03-contact-proof','llsys-pg-r03-actual-pin-input']:
        for p in (root/name).iterdir():
            if p.is_file():gzcopy(p,dest/name/(p.name+'.gz'))
    inputs={c:('trial-inputs-act-access-publication-r04' if c=='act' else 'trial-inputs-'+c+'-access-'+('r04' if c.endswith('_aux') else 'r03')) for c in CASES}
    pin_links=[]
    for c,directory in inputs.items():
        folder=root/directory;tables=list(folder.glob('*all_pins.csv'));assert len(tables)==1
        d=pd.read_csv(tables[0],low_memory=False);original=pd.read_csv(root/(c+'_pin_coordinates.csv'),low_memory=False);original=original[original.plan=='A'].set_index('pin');d=d.set_index('pin').loc[original.index]
        assert len(d)==COUNTS[c] and d.index.is_unique
        for k in ['layer','direction','use','net']:assert d[k].equals(original[k]),(c,k)
        assert np.allclose(d.x1_um-d.x0_um,original.x1_um-original.x0_um) and np.allclose(d.y1_um-d.y0_um,original.y1_um-original.y0_um)
        for p in folder.iterdir():
            if p.is_file() and p.suffix in ['.csv','.json','.tcl']:gzcopy(p,dest/'inputs'/c/(p.name+'.gz'))
        pin_links.append('<li><a href="data/continuation/inputs/'+c+'/'+tables[0].name+'.gz">'+html.escape(expand.TITLES[c])+'：'+str(COUNTS[c])+'个完整增量pin坐标</a></li>')
    for p in (root/'trial-inputs-llsys-pg-r03').iterdir():
        if p.is_file() and p.suffix in ['.csv','.json','.tcl']:gzcopy(p,dest/'inputs/llsys-pg-r03'/(p.name+'.gz'))
    stages=[]
    for c in CASES:
        revision='act-access-r03' if c=='act' else 'access-r03';d=snapshot/'trials'/revision/(c+'-C');p=d/'execution.json.gz';j=read(p) if p.exists() else {}
        f=snapshot/'finalized'/revision/(c+'-C')/'execution.json.gz';q=read(f) if f.exists() else {}
        def slack(kind):
            p=d/('timing.'+kind+'.txt.gz')
            if not p.exists():return None
            import re
            m=re.search(r'worst slack (?:min|max)\s+([-\d.]+)',gzip.decompress(p.read_bytes()).decode());return float(m[1]) if m else None
        p=d/'timing.checks.txt.gz';viol=sum('(VIOLATED)' in x for x in gzip.decompress(p.read_bytes()).decode().splitlines()) if p.exists() else None
        stages.append({'block':expand.TITLES[c],'all_pins':COUNTS[c],'selected_internal':j.get('selected_pin_count'),'job':j.get('scheduler_job'),
                       'trial_terminal':bool(j.get('finished_utc')),'route_returncode':j.get('returncode'),'independent_native_DRC':q.get('independent_DRC_count'),
                       'whole_geometry':q.get('whole_access',{}).get('pass'),'setup_ns':slack('setup'),'hold_ns':slack('hold'),'electrical_timing_violator_rows':viol,
                       'full_qualification':False,'source_receipt':str((d/'execution.json.gz').relative_to(snapshot)) if (d/'execution.json.gz').exists() else None})
    summary={'scope':'CONTINUATION_STAGE_RECEIPTS_NOT_FULL_SYSTEM_QUALIFICATION','snapshot':snapshot.name,'blocks':stages,
             'complete_original_pin_count':24767,'candidate_rows_preserved':74301,'common_base_frozen':False,
             'M11_M12_complete_functions_implemented':False,'system_comparison_complete':False,
             'source_manifest_SHA':hashlib.sha256((snapshot/'snapshot.json').read_bytes()).hexdigest()}
    (dest/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    plot_upper(root,out/'assets');plot_pg(root,out/'assets');plot_common(root,out/'assets')
    table=pd.DataFrame(stages).drop(columns=['source_receipt','full_qualification']).astype(object).where(pd.notna(pd.DataFrame(stages).drop(columns=['source_receipt','full_qualification'])),'待验证').to_html(index=False,border=0)
    section='''<section class="card" id="continuation"><h2>2026-10-28 接续：真实接入与共同底座（进行中）</h2>
<div class="warn"><b>当前范围与状态：</b>用户已确认六块资源并集、交错布局、两功能共享实际固定预连导体；本轮包含研究M11/M12建模。下方旧报告“不扩展M11/M12”仅描述此前阶段。本节不宣布共同M1–M10实现/冻结、两套M11/M12功能或完整系统对照完成。</div>
<h3>六块完整内部接入窗口试验</h3><div class="scroll">'''+table+'''</div><p>空项为待验证，不是0。候选覆盖24,767个原始pin/74,301行A/B/C未改；本轮另提供六块完整增量pin表，保留层/网络/方向/矩形及常量。真实相邻层轨道和临时接入窗口指导实际重布线，移除的只有新建临时约束，原OBS、单元、允许层集合及PDN保留。该方法重布全部信号/时钟，不能混入旧局部rip同组对照的纯XY收益。ACT740个内部pin的新叶视图独立native0/4819网连通通过，当前源约束setup1.255988ns、hold0.031533ns、违规行0；仍有SRAM/GDS/规则/边界模型资格缺项。</p>
<p><a href="data/continuation/summary.json">本轮阶段摘要</a> · <a href="data/continuation/native/'''+snapshot.name+'''/snapshot.json">原始回执、远程物理产物与SHA索引</a>。VECTOR旧C在原3ns约束的最差路径是块内寄存器到寄存器，精确RC/SDC重放仍约−4.17ns；openSYS也有setup/hold/电气失败。没有放宽时钟或删检查，尚未证明新窗口试验修复这些失败。</p>
<h3>llaccel SYSTEM：先消除实际固定PG直接接触</h3><img loading="lazy" src="assets/llsys_pg_revision.png" alt="llSYS PG直接接触局部修订"><p><a href="assets/llsys_pg_revision.svg">SVG</a>。原C的26pin/44接触对及失败检查点保留。PG修订r03经实际place_pin回读全部13,507pin匹配，PG指纹相同、同层直接接触0；13,184个pin仍移动。92648/92649与后续完整窗口重布线是不同试验，状态分别读取；直接接触0不代表DRC/STA通过。</p>
<h3>ACT：原层到父层M10的真实接入</h3><p>原宏860个M5/M6 pin未升级金属层；256个read bus bit经实际布线接入新的父层M10中间接点，其余604个父端口与原宏端口真实同层重合，单独记录为零线长。89.6μm平移保持上层轨道相位，Aopt夹具native0、双PG和860网/1720端点连通通过。C完整内部窗口叶视图通过，但父夹具r04仍有1项r_data[195]与VDD的M10间距错误；via限定修复拒绝修改电源条带，保留失败。保留PG的真实条带避让重布线结果见本轮原始回执；没有将夹具通过写成系统通过。</p>
<h3>研究M11/M12：实际工具/通孔小例</h3><img loading="lazy" src="assets/research_upper_actual.png" alt="真实M11 M12小例路由"><p><a href="assets/research_upper_actual.svg">SVG</a>。92650/92653的2网/4端点独立native0、实际via10/11及所检几何连通通过，新增下层金属只在既有M10接点内。原十层规则块哈希不变。层厚2μm、高14.09/18.09μm、RC来自原M9/M10外推，via零包围是研究假设；尚无12层完整制造deck、校准RCX或系统STA。0.5/1/2倍RC敏感性仍待执行。</p>
<h3>六块共同底座：已编译完整逻辑与布局合同，尚未实现冻结</h3><img loading="lazy" src="assets/common_base_proposed.png" alt="六块共同底座拟议布局与共享预连"><p><a href="assets/common_base_proposed.svg">SVG</a>。完整两功能逐bit图、所有24,767pin、37个独立常量TOP_IO声明和相同256导体预算已编译。资源并集不意味着共享同一计算实例；共享导体必须在两功能物理实现中实际使用。图中的proposed位置/导体不是布通结果。其余固定私有连接、闲置时钟/复位/外部输入及常量驱动、PG/完整接入仍待实现；两套独立旧父层不冒充共同底座。底层未冻结，无哈希一致性或面积收益结论。</p>
<p>旧openTPU父层r07终态独立native11失败（10项M9 spacing、1项via cut spacing），虽3207网几何连通/双PG通过也未资格化；旧llaccel父层ll-r01在GRT-0116拥塞失败。92476/92477被实际物理门槛阻止，RC/STA未执行。完整GDS、缺失SRAM、天线和WELL规则语义问题继续保留。优化Aopt与内部C都继续保留，局部块内线长增加并不能替代完整系统收益判断。</p></section>'''

    access_rows=[]
    for area in ['escape_fixtures','escape_pg_repair','escape_spacing_reroute']:
        for p in sorted((snapshot/area).glob('*/*/execution.json.gz')):
            j=read(p);g=j.get('whole_signal_geometry',{})
            access_rows.append({'fixture':str(p.parent.relative_to(snapshot)), 'job':j.get('scheduler_job'),
                                'native_return':j.get('native_route_returncode',j.get('native_repair_returncode')),
                                'fresh_DRC':j.get('independent_DRC_count',j.get('fresh_DRC_count')),
                                'whole_geometry':g.get('pass'),'status':j.get('status','待验证')})
    if access_rows:
        rows=pd.DataFrame(access_rows).astype(object).where(pd.notna(pd.DataFrame(access_rows)),'待验证').to_html(index=False,border=0)
        section=section.replace('<h3>研究M11/M12', '<h4>实际接入夹具逐轮回执（不等于系统实现）</h4><div class="scroll">'+rows+'</div><p>ACT0.8μm条带避让轮原PG间距项消失，但出现2项信号间距错误；全部PG指纹和860网连通通过仍不能改写DRC失败。GEMM旧内部C在gemm_a_rdata[142]报DRT-0073无接入点，新完整窗口视图另行验证。</p><h3>研究M11/M12')
    stamp=read(snapshot/'snapshot.json')['created_utc']
    section=section.replace('<h3>六块完整内部接入窗口试验</h3>','<p>本节原始物理回执快照UTC：'+html.escape(stamp)+'；运行中的作业不以文件存在或Slurm成功作为通过。</p><h3>六块完整内部接入窗口试验</h3>')
    section=section.replace('<h3>llaccel SYSTEM：','<p>下方原A/B/C交互查询保留原候选；本轮增量C坐标另按原pin名称逐项对应：</p><ul>'+''.join(pin_links)+'</ul><h3>llaccel SYSTEM：')
    return section
