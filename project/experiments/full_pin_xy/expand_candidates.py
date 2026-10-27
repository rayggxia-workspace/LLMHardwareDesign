"""Extend PR120 to the four remaining *physical* blocks; never regenerate ACT/GEMM.

This is geometry-only. Same-source OBS/wires/PG are screened, not re-routed here.
"""
from pathlib import Path
from collections import Counter,defaultdict
import argparse,csv,gzip,json,math,importlib.util,shutil
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
spec=importlib.util.spec_from_file_location('pr120_geometry',REPO/'project/experiments/pin_xy_candidates/analyze_layout.py')
legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
ROOT=None
TITLES={'act':'openTPU ACT','mxu':'openTPU MXU','opentpu_aux':'openTPU SYSTEM',
        'gemm':'llaccel GEMM','vector':'llaccel VECTOR','llaccel_aux':'llaccel SYSTEM'}
EXTRA={'t_memory':('#8b6bb1','TMEM 读写'),'position':('#586e99','位置参数'),
       'sram':('#8b6bb1','外部 SRAM bank'),'dram':('#d55e00','DRAM 接口'),
       'gemm_link':('#0072b2','GEMM 连接'),'vector_link':('#009e73','VECTOR 连接'),
       'mxu_link':('#56b4e9','MXU 连接'),'collective':('#aa9900','Collective'),
       'system_control':('#65758a','控制 / 状态 / 外部 IO')}
for k,(color,label) in EXTRA.items():legacy.COLORS[k]=color;legacy.LABELS[k]=label

def jsave(p,j):p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def read(c,name):return pd.read_csv(ROOT/'physical'/c/(name+'.tsv.gz'),sep='\t')
def category(case,m):
    b=m['semantic_bus'].lower();peers={q['block'] for q in m['logical_peers']}
    if b in ['clk','rst','rst_n'] or b.endswith(('.clk','.rst','.rst_n')):return 'clock'
    if b.startswith('bank_'):return 'sram'
    if b.startswith('dram_'):return 'dram'
    if 'collect' in b or b.startswith('coll_'):return 'collective'
    if 'gemm' in peers:return 'gemm_link'
    if 'vector' in peers:return 'vector_link'
    if 'act' in peers:return 'act_link'
    if 'mxu' in peers:return 'mxu_link'
    return 'system_control'

def load_new(case,mapping,original):
    b=read(case,'bterms');b.pin=b.pin.map(legacy.norm);b.net=b.net.map(legacy.norm)
    actual_use=pd.read_csv(ROOT/'pin-use-r01'/(case+'.tsv'),sep='\t').set_index('pin').sig_type.to_dict()
    design={}
    with gzip.open(ROOT/'physical'/case/'design.tsv.gz','rt') as f:
        for line in f:
            row=line.strip().split('\t');design[row[0]]=row[1:]
    dbu=int(design['dbu_per_um'][0]);assert dbu==2000
    dims=np.array([float(x)/dbu for x in design['die']]);assert np.allclose(dims[:2],0)
    macros=read(case,'macros');macroboxes=macros[['x0','y0','x1','y1']].to_numpy(float)/dbu
    pg=b[b.pin.isin(['VDD','VSS'])].copy();sig=b[~b.pin.isin(['VDD','VSS'])].copy().reset_index(drop=True)
    assert sig.pin.nunique()==len(sig) and set(sig.pin)==set(mapping),(case,'physical port-set mismatch')
    actual=original[original['case']==case].set_index('pin') if case in ['mxu','vector'] else None
    rows=[]
    for _,q in sig.iterrows():
        m=mapping[q.pin];assert q.direction.lower()==m['original_direction']
        rect=q[['x0','y0','x1','y1']].to_numpy(float)/dbu;x,y=(rect[:2]+rect[2:])/2
        edge=min(zip([x,dims[2]-x,y,dims[3]-y],['W','E','S','N']))[1]
        if actual is not None:
            old=actual.loc[q.pin];assert old.layer==q.layer
            assert np.allclose(old[['x0_um','y0_um','x1_um','y1_um']].to_numpy(float),rect,atol=1e-8)
            interface=old.interface;bus=old.bus
        else:interface=category(case,m);bus=q.pin
        row={'case':case,'pin':q.pin,'bus':bus,'interface':interface,'direction':q.direction,'use':actual_use[q.pin],
             'layer':q.layer,'edge':edge,'x_um':x,'y_um':y,'x0_um':rect[0],'y0_um':rect[1],'x1_um':rect[2],'y1_um':rect[3],
             'net_id':int(q.net_id),'net':q.net,'semantic_bus':m['semantic_bus'],'semantic_bit':int(m['semantic_bit'])}
        if actual is not None:row['use']=actual.loc[q.pin,'use']
        rows.append(row)
    df=pd.DataFrame(rows)
    anchors={};directs={}
    for name,lookup in [('anchors',anchors),('endpoints',directs)]:
        a=read(case,name);a.pin=a.pin.map(legacy.norm)
        for pin,g in a.groupby('pin'):lookup[pin]=g[['x','y']].to_numpy(float)/dbu
    for _,r in df.iterrows():
        if r.interface=='clock':anchors.pop(r.pin,None)
    tech=read(case,'tech').set_index('layer')
    # Canonical tech via definitions, bounded by the original block's allowed layer set.
    allowed_top=8 if case.endswith('_aux') else 10
    for k in ['metal5','metal6']:assert k in tech.index
    meta={'case':case,'spec':{'title':TITLES[case],'odb':str(read_config()['physical_blocks'][case]['odb']),
          'quality':read_config()['physical_blocks'][case]['source_limits']},'units_per_micron':dbu,'die_dbu':[int(x) for x in design['die']],
          'macros':[{'name':r.inst,'master':r.master,'orientation':r.orient,'bbox_dbu':[int(r[x]) for x in ['x0','y0','x1','y1']]} for _,r in macros.iterrows()],
          'allowed_signal_top_routing_level':allowed_top,'source_odb_sha256':read_config()['physical_blocks'][case]['expected_sha256']}
    jsave(ROOT/(case+'.meta.json'),meta)
    return df,pg,anchors,directs,dims,macroboxes,tech

def read_config():return json.loads((HERE/'sources.json').read_text(encoding='utf-8'))
def groups(case,df,edge_local=False):
    bysem=defaultdict(dict)
    for i,r in df.iterrows():bysem[r.semantic_bus][int(r.semantic_bit)]=i
    output=[];used=set()
    # Real byte strobes from RTL: VECTOR write and the llaccel bank boundary.
    pairs=[('vec_wr_wdata','vec_wr_wstrb',64)] if case=='vector' else [('bank_wdata','bank_we',256)] if case=='llaccel_aux' else []
    for data,strobe,n in pairs:
        if data not in bysem or strobe not in bysem:continue
        for k in range(n):
            needed=[bysem[data].get(8*k+j) for j in range(8)]+[bysem[strobe].get(k)]
            assert all(i is not None for i in needed),(case,data,k)
            output.append((f'{data}__byte{k:03}',needed,'RTL byte data/enable association'));used.update(needed)
    if case=='mxu':
        # Actual packed [3:0][31:0] t_wdata and per-lane t_wen; not a byte strobe.
        for k in range(4):
            needed=[bysem['t_wdata'][32*k+j] for j in range(32)]+[bysem['t_wen'][k]]
            output.append((f't_write_lane{k}',needed,'RTL: 32-bit TMEM write lane with t_wen[k]'));used.update(needed)
    keys=['semantic_bus','edge'] if edge_local else ['semantic_bus']
    for key,g in df.groupby(keys,sort=False):
        label=key[0] if isinstance(key,tuple) else key
        ids=[i for i in g.index if i not in used]
        ids.sort(key=(lambda i:df.loc[i,'y_um' if df.loc[i,'edge'] in 'WE' else 'x_um']) if edge_local else (lambda i:df.loc[i,'semantic_bit']))
        for k in range(0,len(ids),32):
            name=f'{label}__{g.iloc[0].edge}_{k//32:03}' if edge_local else f'{label}__{k//32:03}'
            output.append((name,ids[k:k+32],'actual parent bus, original-edge geometric neighbors' if edge_local else 'actual parent bus, contiguous logical-index drawing bundle; lane/bank not inferred'))
    assert sorted(i for _,ids,_ in output for i in ids)==list(range(len(df)))
    return output

def propose(case,df,anchors,dims,macros,index,tech):
    original=df[['x_um','y_um']].to_numpy();w,h=dims[2:];result={'A':original.copy()};patches={};allgroups={};reasons={}
    widths=Counter(df.semantic_bus)
    for plan in ['B','C']:
        gg=groups(case,df,plan=='B');allgroups[plan]=gg;movable=set();why={}
        for gn,ids,sem in gg:
            constbyte=case=='vector' and gn.startswith('vec_wr_wdata__byte') and int(gn.split('byte')[-1])>=32
            for i in ids:
                r=df.loc[i]
                if r.interface=='clock':why[i]='clock/reset: preserve original access and clock tree'
                elif constbyte:why[i]='RTL constant-zero whole byte: preserve scattered drivers and logical strobe association'
                elif r.pin not in anchors:why[i]='no traced internal ITerm: keep declared/idle bit, do not invent endpoint'
                elif plan=='C' and widths[r.semantic_bus]<64 and not('byte' in gn or 'write_lane' in gn):why[i]='narrow control/address/status transaction: boundary retained'
                else:movable.add(i);why[i]='real traced endpoint and actual-bus/RTL association support proposed movement'
        fixed=[i for i in range(len(df)) if i not in movable];fixedxy=original[fixed];occupied=[];specs=[];xy=original.copy()
        margin=max(15.68,.02*min(w,h));centers=np.array([(x,y) for x in np.arange(margin,w-margin,8.96) for y in np.arange(margin,h-margin,8.96)])
        tree=cKDTree(centers)
        for gn,allids,sem in gg:
            ids=[i for i in allids if i in movable]
            if not ids:continue
            off=legacy.footprint(len(ids),1.12 if plan=='B' else 2.24)
            source=np.median(original[ids],axis=0);target=np.median(np.vstack([anchors[df.loc[i,'pin']] for i in ids]),axis=0)
            opts=[]
            if plan=='B':
                preferred=Counter(df.loc[ids,'edge']).most_common(1)[0][0]
                for edge in [preferred]+[e for e in 'SWNE' if e!=preferred]:
                    length=w if edge in 'SN' else h;tangent=source[0] if edge in 'SN' else source[1]
                    ts=np.arange(10.08,length-10.08,1.12);order=np.argsort(np.abs(ts-tangent))
                    for t in ts[order[:min(512,len(order))]]:
                        pts=off.copy()+[t,2.80]
                        if edge=='N':pts[:,1]=h-pts[:,1]
                        elif edge=='W':pts=pts[:,[1,0]]
                        elif edge=='E':pts=pts[:,[1,0]];pts[:,0]=w-pts[:,0]
                        opts.append((abs(t-tangent)+(0 if edge==preferred else length),pts,edge))
            else:
                _,near=tree.query(target,k=min(1024,len(centers)),p=1)
                for j in np.atleast_1d(near):
                    center=centers[j];cost=np.abs(center-target).sum()+.08*np.abs(center-source).sum();opts.append((cost,off+center,'interior'))
            opts.sort(key=lambda r:r[0]);short=[];oc=np.array(occupied) if occupied else None
            for cost,pts,edge in opts:
                bb=legacy.bbox(pts)
                if bb[0]<0 or bb[1]<0 or bb[2]>w or bb[3]>h:continue
                if len(macros) and np.any((bb[0]-.56<macros[:,2])&(bb[2]+.56>macros[:,0])&(bb[1]-.56<macros[:,3])&(bb[3]+.56>macros[:,1])):continue
                if oc is not None and np.any((bb[0]-.56<oc[:,2])&(bb[2]+.56>oc[:,0])&(bb[1]-.56<oc[:,3])&(bb[3]+.56>oc[:,1])):continue
                if len(fixedxy) and np.any((fixedxy[:,0]>bb[0]-.56)&(fixedxy[:,0]<bb[2]+.56)&(fixedxy[:,1]>bb[1]-.56)&(fixedxy[:,1]<bb[3]+.56)):continue
                short.append((cost,pts,edge))
                if len(short)==12:break
            assert short,(case,plan,gn,'no macro-safe group window')
            best=None
            for cost,pts,edge in short:
                hit=0
                for i,(x,y) in zip(ids,pts):
                    r=df.loc[i];hit+=bool(index.hits(r.layer,x,y,.07,.07,float(tech.loc[r.layer,'spacing'])/2000,int(r.net_id)))
                score=cost+hit*(1 if plan=='B' else 3)
                if best is None or score<best[0]:best=(score,pts,edge,hit)
            _,pts,edge,hit=best;xy[ids]=pts;bb=legacy.bbox(pts);occupied.append(bb)
            specs.append({'group':gn,'ids':ids,'semantic':sem,'bbox_um':bb.tolist(),'placement_region':edge,'pitch_um':1.12 if plan=='B' else 2.24,'pin_count':len(ids),'screen_cost_pin_hits':hit})
        result[plan]=np.round(xy,6);patches[plan]=specs;reasons[plan]=why
    allgroups['A']=groups(case,df,False);reasons['A']={i:'actual original database' for i in range(len(df))}
    return result,patches,allgroups,reasons

def plot(case,df,plans,patches,metrics,anchors,dims,macros,index):
    plt=legacy.plt;Rectangle=legacy.Rectangle;Line2D=legacy.Line2D
    bg=legacy.background(case,dims);w,h=dims[2:];leg=[Line2D([0],[0],marker='o',ls='',color=legacy.COLORS[k],label=f'{legacy.LABELS[k]} ({n:,})',markersize=5) for k,n in Counter(df.interface).items()]
    fig,axes=plt.subplots(1,3,figsize=(19.5,9.2));fig.subplots_adjust(left=.045,right=.985,top=.75,bottom=.24,wspace=.18)
    fig.text(.04,.95,f'{TITLES[case]} | 全 pin A/B/C 对照',fontsize=22,weight='bold')
    fig.text(.04,.90,f'{len(df):,} 信号 pin · {w:g} × {h:g} μm · M5 {sum(df.layer=="metal5"):,} / M6 {sum(df.layer=="metal6"):,} · pin 层/网络/方向/尺寸保持',fontsize=11,color='#56677d')
    fig.legend(handles=leg,loc='upper left',bbox_to_anchor=(.035,.875),ncol=4,frameon=False,fontsize=9)
    zoom={}
    for ax,(p,xy) in zip(axes,plans.items()):
        legacy.draw_base(ax,bg,dims,macros);legacy.points(ax,df,xy)
        for pp in patches.get(p,[]):
            bb=pp['bbox_um'];ax.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fill=False,ec='#8198ad',lw=.3,alpha=.6,zorder=3))
        if p=='A':
            bins=defaultdict(list)
            for i,(x,y) in enumerate(xy):bins[int(x//30),int(y//30)].append(i)
            ids=max(bins.values(),key=len);center=np.median(xy[ids],axis=0);zoom[p]=(max(-2,center[0]-20),max(-2,center[1]-12),min(w+2,center[0]+20),min(h+2,center[1]+12))
        else:
            pp=max(patches[p],key=lambda z:z['pin_count']);bb=pp['bbox_um'];zoom[p]=(max(-2,bb[0]-4),max(-2,bb[1]-4),min(w+2,bb[2]+4),min(h+2,bb[3]+4))
        z=zoom[p];ax.add_patch(Rectangle(z[:2],z[2]-z[0],z[3]-z[1],fill=False,ls='--',ec='#304d70',lw=1,zorder=7))
        ax.set_title(f'{p}. {legacy.PLAN[p]}',loc='left',fontsize=12,weight='bold');m=metrics[p]
        ax.text(0,-.17,f'移动 {m["moved"]:,} / 保留 {m["fixed"]:,}\n同层最小 NN：M5 {m["min_nn_per_layer_um"]["metal5"]:.3f} / M6 {m["min_nn_per_layer_um"]["metal6"]:.3f} μm',transform=ax.transAxes,fontsize=9,color='#56677d')
    fig.text(.04,.035,'圆=M5，方=M6；显示标记放大，不代表 pin/通孔尺寸。底图是实际实例 bbox 栅格投影，不能推断上方金属可用。\nB/C 为 proposed；已做实际金属、PG、OBS 的局部矩形筛查，完整接入、RC/STA/DRC 分阶段另报。',fontsize=10,color='#56677d')
    for ext in ['png','svg']:fig.savefig(ROOT/f'{case}_comparison.{ext}',dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(19.5,6.9));fig.subplots_adjust(left=.045,right=.985,top=.79,bottom=.29,wspace=.2)
    fig.text(.04,.94,f'{TITLES[case]} | 密集区与实际占用局部放大',fontsize=22,weight='bold')
    fig.text(.04,.88,'独立取窗、不同局部尺度，单位 μm；蓝灰 M5、紫灰 M6、土黄 M7 PG 均来自数据库，不是新接入线。',fontsize=10,color='#56677d')
    for ax,(p,xy) in zip(axes,plans.items()):
        z=zoom[p];legacy.draw_base(ax,bg,dims,macros)
        for l,color in [('metal5','#93b1c5'),('metal6','#c4accf'),('metal7','#d29f58')]:
            a,_,kinds,_=index.layers[l];sel=(a[:,0]<z[2])&(a[:,2]>z[0])&(a[:,1]<z[3])&(a[:,3]>z[1])
            if l=='metal7':sel&=np.char.startswith(kinds,'pg')
            for bb in a[sel]:ax.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fc=color,ec=color,lw=.2,alpha=.35,zorder=2))
        legacy.points(ax,df,xy);ax.set_xlim(z[0],z[2]);ax.set_ylim(z[1],z[3]);ax.set_title(f'{p}. {legacy.PLAN[p]}',loc='left',fontsize=11)
        ids=np.where((xy[:,0]>=z[0])&(xy[:,0]<=z[2])&(xy[:,1]>=z[1])&(xy[:,1]<=z[3]))[0]
        if len(ids):
            i=ids[len(ids)//2];ax.annotate(df.loc[i,'pin'],xy[i],xytext=(4,16),textcoords='offset points',fontsize=8,arrowprops={'arrowstyle':'-','lw':.5})
        fig.text(ax.get_position().x0,.14,f'窗口 {z[2]-z[0]:.2f} × {z[3]-z[1]:.2f} μm；{len(ids)} 个接点\n标记不是实际通孔；逐 pin 矩形/风险见 CSV',fontsize=9,color='#56677d')
    fig.text(.04,.035,'局部接点可能与已有金属/PG 或 OBS 冲突，需要重新接入与完整规则检查。保持原 pin 层，不统一提升至 M11/M12。',fontsize=10,color='#56677d')
    for ext in ['png','svg']:fig.savefig(ROOT/f'{case}_zoom.{ext}',dpi=180)
    plt.close(fig)

def run(root,cases):
    global ROOT;ROOT=Path(root).resolve();legacy.ROOT=ROOT
    legacy.constant_zero=lambda c,r: c=='vector' and ((r.semantic_bus=='vec_wr_wdata' and r.semantic_bit>=256) or (r.semantic_bus=='vec_wr_wstrb' and r.semantic_bit>=32))
    raw=json.loads(gzip.decompress((REPO/'docs/experiments/issue-119-pin-xy/data/source_pin_data.json.gz').read_bytes()))
    original=pd.DataFrame(raw['rows'],columns=raw['columns'])
    for col in [c for c in original.columns if c.endswith('_um')]:original[col]=original[col].astype(float)
    mapping=json.loads((ROOT/'inventory/pin_logical_mapping.json').read_text(encoding='utf-8'))
    for case in cases:
        print('LOAD',case,flush=True);df,pg,anchors,directs,dims,macros,tech=load_new(case,mapping[case],original)
        chunks=[]
        for chunk in pd.read_csv(ROOT/'physical'/case/'shapes.tsv.gz',sep='\t',chunksize=250000):
            chunks.append(chunk[chunk.layer.isin([f'metal{k}' for k in range(4,11)]+[f'via{k}' for k in range(4,10)])])
        shape=pd.concat(chunks,ignore_index=True);del chunks
        ob=ROOT/'physical'/case/'obstructions.tsv.gz'
        if ob.exists():
            obs=pd.read_csv(ob,sep='\t');shape=pd.concat([shape,obs[['layer','x0','y0','x1','y1','net_id','kind']]],ignore_index=True)
        index=legacy.ShapeIndex(shape);print('LAYOUT',case,len(df),'pins',len(shape),'screened shapes',flush=True)
        plans,patches,gg,reasons=propose(case,df,anchors,dims,macros,index,tech)
        print('EVALUATE',case,flush=True);mm,table=legacy.evaluate(case,df,plans,patches,anchors,directs,dims,macros,index,tech)
        for p,m in mm.items():m['allowed_signal_top_routing_level']=8 if case.endswith('_aux') else 10;m['toM10_sensitivity_legal_for_block']=not case.endswith('_aux')
        table['retention_or_movement_reason']=[reasons[r.plan][i%len(df)] for i,r in table.iterrows()]
        table.to_csv(ROOT/f'{case}_pin_coordinates.csv',index=False,encoding='utf-8-sig',float_format='%.6f')
        checks=legacy.validate(case,df,pg,plans,patches,dims,macros,table)
        jsave(ROOT/f'{case}_metrics.json',mm);jsave(ROOT/f'{case}_patches.json',patches);jsave(ROOT/f'{case}_validation.json',checks)
        pd.DataFrame([{'plan':p,'group':gn,'pin':df.loc[i,'pin'],'semantic':sem} for p,groupset in gg.items() for gn,ids,sem in groupset for i in ids]).to_csv(ROOT/f'{case}_groups.csv',index=False,encoding='utf-8-sig')
        pg.to_csv(ROOT/f'{case}_pg_source.csv',index=False,encoding='utf-8-sig')
        print('PLOT',case,flush=True);plot(case,df,plans,patches,mm,anchors,dims,macros,index)
        print('COMPLETE_CANDIDATES',case,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--cases',nargs='+',default=['mxu','vector','opentpu_aux','llaccel_aux']);a=p.parse_args();run(a.root,a.cases)
