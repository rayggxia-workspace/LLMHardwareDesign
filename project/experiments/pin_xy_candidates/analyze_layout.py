"""Geometry proposals and read-only ODB rectangle screening; never edits a database.

Dependencies: numpy pandas scipy matplotlib. Run from any working directory.
Coordinates/rectangle dimensions in CSV are micrometres. Markers are display symbols.
"""
from pathlib import Path
from collections import Counter,defaultdict
import json, math, re, hashlib, sys, csv
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
from matplotlib.collections import LineCollection

ROOT=Path(__file__).resolve().parent
COLORS={'clock':'#111827','act_link':'#009e73','act_scale':'#aa9900','act_write':'#cc79a7',
        'status':'#65758a','command':'#e69f00','read_a':'#0072b2','read_b':'#56b4e9','write':'#d55e00'}
LABELS={'clock':'时钟 / 复位','act_link':'ACT <-> MXU','act_scale':'ACT scale 写入','act_write':'ACT 数据写入',
        'status':'状态 / 预取','command':'命令 / 指令','read_a':'Read A','read_b':'Read W','write':'Memory write'}
TITLES={'act':'openTPU ACT','gemm':'llaccel GEMM'}
PLAN={'A':'原始四边 · actual','B':'贴边多排 / 错位 · proposed','C':'内部二维 + 边缘保留 · proposed'}
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'],
                     'font.size':10,'axes.labelcolor':'#17283c','text.color':'#17283c','axes.edgecolor':'#52667d',
                     'svg.fonttype':'none','figure.facecolor':'white','axes.facecolor':'white'})

def savejson(name,d): (ROOT/name).write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
def norm(s): return str(s).replace('\\','')
def bit(pin):
    m=re.search(r'\[(\d+)\]$',pin);return int(m[1]) if m else -1
def constant_zero(case,r):
    # Exact RTL assignments in the source snapshot: high 256 data and high 32 strobe bits.
    return case=='gemm' and ((r.bus=='gemm_wr_wdata' and bit(r.pin)>=256) or (r.bus=='gemm_wr_wstrb' and bit(r.pin)>=32))
def physical(case,name): return pd.read_csv(ROOT/'physical'/case/(name+'.tsv.gz'),sep='\t')

class ShapeIndex:
    """Exact rectangle queries with an auxiliary spatial hash; no occupancy raster test."""
    def __init__(self,df,step=12.):
        self.layers={}; self.step=step
        for layer,g in df.groupby('layer'):
            if layer not in [f'metal{i}' for i in range(4,11)]+[f'via{i}' for i in range(4,10)]:continue
            a=g[['x0','y0','x1','y1']].to_numpy(float)/2000
            nets=g.net_id.to_numpy(int);kinds=g.kind.to_numpy(str); bins=defaultdict(list)
            for idx,(x0,y0,x1,y1) in enumerate(a):
                for ix in range(math.floor(x0/step),math.floor(x1/step)+1):
                    for iy in range(math.floor(y0/step),math.floor(y1/step)+1):bins[ix,iy].append(idx)
            self.layers[layer]=(a,nets,kinds,bins)
    def query(self,layer,box,exclude=-1):
        if layer not in self.layers:return []
        a,net,kind,bins=self.layers[layer];x0,y0,x1,y1=box;s=self.step
        ids=set()
        for ix in range(math.floor(x0/s),math.floor(x1/s)+1):
            for iy in range(math.floor(y0/s),math.floor(y1/s)+1):ids.update(bins.get((ix,iy),()))
        if not ids:return []
        ids=np.fromiter(ids,int);r=a[ids]
        keep=(net[ids]!=exclude)&(r[:,0]<x1-1e-9)&(r[:,2]>x0+1e-9)&(r[:,1]<y1-1e-9)&(r[:,3]>y0+1e-9)
        return [(int(i),kind[i]) for i in ids[keep]]
    def hits(self,layer,x,y,hx,hy,space=0,exclude=-1):
        return self.query(layer,(x-hx-space,y-hy-space,x+hx+space,y+hy+space),exclude)

def load(case):
    data=json.loads((ROOT/'source_pin_data.json').read_text(encoding='utf-8'))
    rows=[dict(zip(data['columns'],r)) for r in data['rows'] if r[0]==case]
    df=pd.DataFrame(rows)
    for c in [x for x in df.columns if x.endswith('_um')]:df[c]=df[c].astype(float)
    df['pin']=df.pin.map(norm);df['bus']=df.bus.map(norm)
    sig=df[~df['use'].isin(['POWER','GROUND'])].copy().reset_index(drop=True)
    pg=df[df['use'].isin(['POWER','GROUND'])].copy()
    b=physical(case,'bterms');b.pin=b.pin.map(norm);b.net=b.net.map(norm)
    for _,r in sig.iterrows():
        q=b[b.pin==r.pin];assert len(q)==1,(case,r.pin,len(q));q=q.iloc[0]
        assert q.layer==r.layer and q.direction==r.direction
        assert np.allclose(q[['x0','y0','x1','y1']].to_numpy(float)/2000,r[['x0_um','y0_um','x1_um','y1_um']].to_numpy(float),atol=1e-8)
    lookup=b.drop_duplicates('pin').set_index('pin')
    sig['net_id']=[int(lookup.loc[p].net_id) for p in sig.pin]
    sig['net']=[lookup.loc[p].net for p in sig.pin]
    direct=physical(case,'endpoints');direct.pin=direct.pin.map(norm)
    anc=physical(case,'anchors');anc.pin=anc.pin.map(norm)
    anchors={};directs={}
    for table,target in [(anc,anchors),(direct,directs)]:
        for p,g in table.groupby('pin'):target[p]=g[['x','y']].to_numpy(float)/2000
    meta=json.loads((ROOT/f'{case}.meta.json').read_text(encoding='utf-8'))
    dims=np.array(meta['die_dbu'],float)/meta['units_per_micron']
    macros=[np.array(m['bbox_dbu'],float)/2000 for m in meta['macros']]
    tech=physical(case,'tech').set_index('layer')
    return sig,pg,anchors,directs,anc,dims,macros,tech

def groups_for(case,df,edge_local=False):
    """Byte-enable association is RTL-backed; other chunks are layout assumptions."""
    groups=[];used=set();byname={r.pin:i for i,r in df.iterrows()}
    if case=='act':
        for k in range(4):
            names=[f'w_data[{8*k+j}]' for j in range(8)]+[f'we[{k}]']
            ids=[byname[n] for n in names];groups.append((f'w_byte{k}',ids,'RTL: w_data[8k+:8] 与 we[k]'));used.update(ids)
    else:
        for k in range(64):
            names=[f'gemm_wr_wdata[{8*k+j}]' for j in range(8)]+[f'gemm_wr_wstrb[{k}]']
            ids=[byname[n] for n in names];groups.append((f'wr_byte{k:02}',ids,'字节接口: data[8k+:8] 与 strobe[k]'));used.update(ids)
    bycols=['bus','edge'] if edge_local else ['bus']
    for key,g in df.groupby(bycols,sort=False):
        bus=key[0] if isinstance(key,tuple) else key
        ids=sorted([i for i in g.index if i not in used],key=lambda i:bit(df.loc[i,'pin']))
        if edge_local:
            edge=g.iloc[0].edge
            ids.sort(key=lambda i:df.loc[i,'y_um' if edge in 'WE' else 'x_um'])
        # No artificial lane or bank semantics: consecutive-index drawing bundles.
        chunk=32 if len(ids)>32 else 16
        for k in range(0,len(ids),chunk):
            sub=ids[k:k+chunk]
            name=f'{bus}__{edge}_{k//chunk:02}' if edge_local else f'{bus}__{k//chunk:02}'
            sem='同总线、同原边的坐标近邻绘图束；非硬件 lane/bank' if edge_local else '连续位号绘图束；非已确认 lane/bank'
            groups.append((name,sub,sem))
    assert sorted(i for _,ids,_ in groups for i in ids)==list(range(len(df)))
    return groups

def bbox(points,half=.07):
    a=np.asarray(points);return np.r_[a.min(0)-half,a.max(0)+half]
def intersects(a,b,gap=0):return a[0]-gap<b[2] and a[2]+gap>b[0] and a[1]-gap<b[3] and a[3]+gap>b[1]
def footprint(n,pitch):
    nx=min(8,max(1,math.ceil(n/4)));xy=np.array([(j%nx*pitch+(j//nx%2)*pitch/2,j//nx*pitch) for j in range(n)])
    return xy-(xy.min(0)+xy.max(0))/2

def propose(case,df,groups,anchors,dims,macros,index,tech):
    w,h=dims[2:];original=df[['x_um','y_um']].to_numpy(float);result={'A':original.copy()};patches={}
    for plan in ['B','C']:
        activegroups=groups_for(case,df,True) if plan=='B' else groups
        xy=original.copy();occupied=[];spec=[]
        # C keeps clock, small control buses and unknown-endpoint bits at original coordinates.
        movable=set()
        for gn,ids,sem in activegroups:
            for i in ids:
                r=df.loc[i]
                if r.interface=='clock':continue
                if constant_zero(case,r):continue
                if plan=='B':movable.add(i)
                elif r.pin in anchors and (len(df[df.bus==r.bus])>=64 or gn.startswith(('w_byte','wr_byte'))):movable.add(i)
        fixed=[i for i in range(len(df)) if i not in movable]
        fixedxy=original[fixed]
        for gn,allids,sem in activegroups:
            ids=[i for i in allids if i in movable]
            if not ids:continue
            pitch=1.12 if plan=='B' else 2.24;off=footprint(len(ids),pitch)
            source_center=np.median(original[ids],axis=0)
            aa=[anchors[df.loc[i,'pin']] for i in ids if df.loc[i,'pin'] in anchors]
            target=np.median(np.vstack(aa),axis=0) if aa else source_center
            options=[]
            if plan=='B':
                edges=Counter(df.loc[ids,'edge']);preferred=edges.most_common(1)[0][0]
                # Four rows fit below the ACT macro boundary (starts at y=5.775 um).
                for edge in [preferred]+[e for e in 'SWNE' if e!=preferred]:
                    length=w if edge in 'SN' else h
                    tangent=source_center[0] if edge in 'SN' else source_center[1]
                    for t in np.arange(8.96,length-8.96,1.12):
                        pts=off.copy();pts[:,1]+=2.80
                        pts[:,0]+=t
                        if edge=='N':pts[:,1]=h-pts[:,1]
                        elif edge=='W':pts=pts[:,[1,0]]
                        elif edge=='E':pts=pts[:,[1,0]];pts[:,0]=w-pts[:,0]
                        score=abs(t-tangent)+(0 if edge==preferred else length)
                        options.append((score,pts,edge))
            else:
                # Search a 2D lattice over the covered block; no light-background inference.
                for x in np.arange(15.68,w-12,8.96):
                    for y in np.arange(15.68,h-12,8.96):
                        center=np.array([x,y]);score=np.abs(center-target).sum()+.08*np.abs(center-source_center).sum()
                        options.append((float(score),off+center,'interior'))
            options.sort(key=lambda t:t[0]);best=None
            # A small shortlist checks actual signal-layer rectangles. It is a soft cost,
            # never a claim that the chosen patch passes routing/DRC.
            legal=[]
            for base,pts,edge in options:
                bb=bbox(pts)
                if bb[0]<0 or bb[1]<0 or bb[2]>w or bb[3]>h:continue
                if any(intersects(bb,m,.56) for m in macros):continue
                if any(intersects(bb,q,.56) for q in occupied):continue
                if len(fixedxy) and np.any((fixedxy[:,0]>bb[0]-.56)&(fixedxy[:,0]<bb[2]+.56)&(fixedxy[:,1]>bb[1]-.56)&(fixedxy[:,1]<bb[3]+.56)):continue
                legal.append((base,pts,edge))
                if len(legal)>=12:break
            assert legal,(case,plan,gn)
            for base,pts,edge in legal:
                collisions=0
                for i,(x,y) in zip(ids,pts):
                    r=df.loc[i];space=float(tech.loc[r.layer,'spacing'])/2000
                    collisions+=bool(index.hits(r.layer,x,y,.07,.07,space,int(r.net_id)))
                value=base+collisions*(1 if plan=='B' else 3)
                if best is None or value<best[0]:best=(value,pts,edge,collisions)
            _,pts,edge,hits=best;xy[ids]=pts;bb=bbox(pts);occupied.append(bb)
            spec.append({'group':gn,'ids':ids,'semantic':sem,'bbox_um':bb.tolist(),'placement_region':edge,
                         'pitch_um':pitch,'pin_count':len(ids),'screen_cost_pin_hits':hits})
        result[plan]=np.round(xy,6);patches[plan]=spec
    return result,patches

def via_envelope(vias,start,target):
    """Canonical single-cut via masters from this exact DB. All conditions are assumptions."""
    env={}
    if target<start:start,target=target,start
    for k in range(start,target):
        vv=vias[vias.via==f'via{k}_0'];assert len(vv)>0,k
        for _,r in vv.iterrows():
            ex=max(abs(r.x0),abs(r.x1))/2000;ey=max(abs(r.y0),abs(r.y1))/2000
            old=env.get(r.layer,(0,0));env[r.layer]=(max(ex,old[0]),max(ey,old[1]))
    return env

def evaluate(case,df,plans,patches,anchors,directs,dims,macros,index,tech):
    metrics={};rows=[];vias=physical(case,'vias')
    envcache={(start,target):via_envelope(vias,start,target) for start in (5,6) for target in (6,8,10)}
    for plan,xy in plans.items():
        n=len(df);dist=cKDTree(xy).query(xy,k=2)[0][:,1]
        moved=np.abs(xy-plans['A']).sum(1)>1e-6
        layer_min={}
        for layer,g in df.groupby('layer'):
            pts=xy[g.index];dd=cKDTree(pts).query(pts,k=2)[0][:,1];layer_min[layer]=float(dd.min())
        near=np.minimum.reduce([xy[:,0],xy[:,1],dims[2]-xy[:,0],dims[3]-xy[:,1]])
        per=[];l1all=[];dall=[]
        stats=Counter();win=20.
        # Sliding axis-aligned 20um squares evaluated at pin coordinates and all four orientations.
        bins=defaultdict(list)
        for i,(x,y) in enumerate(xy):bins[math.floor(x/win),math.floor(y/win)].append(i)
        maxwin=0
        for x,y in xy:
            for sx,sy in [(0,0),(-1,0),(0,-1),(-1,-1)]:
                x0=x+sx*win;y0=y+sy*win;ids=[]
                for ix in range(math.floor(x0/win),math.floor((x0+win)/win)+1):
                    for iy in range(math.floor(y0/win),math.floor((y0+win)/win)+1):ids.extend(bins.get((ix,iy),()))
                pp=xy[ids];num=int(np.sum((pp[:,0]>=x0-1e-8)&(pp[:,0]<=x0+win+1e-8)&(pp[:,1]>=y0-1e-8)&(pp[:,1]<=y0+win+1e-8)))
                maxwin=max(maxwin,num)
        for i,r in df.iterrows():
            x,y=xy[i];half=((r.x1_um-r.x0_um)/2,(r.y1_um-r.y0_um)/2)
            space=tech.loc[r.layer,'spacing']/2000;net=int(r.net_id)
            hits=index.hits(r.layer,x,y,*half,exclude=net)
            guardhits=index.hits(r.layer,x,y,*half,space,net)
            macrohit=any(intersects([x-half[0],y-half[1],x+half[0],y+half[1]],m) for m in macros)
            m={'case':case,'plan':plan,'pin':r.pin,'bus':r.bus,'interface':r.interface,'direction':r.direction,'use':r['use'],
               'net_id':net,'net':r.net,'layer':r.layer,'original_edge':r.edge,'original_x_um':float(r.x_um),'original_y_um':float(r.y_um),
               'x_um':float(x),'y_um':float(y),'x0_um':float(x-half[0]),'y0_um':float(y-half[1]),'x1_um':float(x+half[0]),'y1_um':float(y+half[1]),
               'moved':bool(moved[i]),'target_layer':'UNKNOWN (unchanged; not reassigned)','external_target':'UNKNOWN (unchanged)',
               'known_constant_zero_from_RTL':constant_zero(case,r),
               'pin_layer_overlap':bool(hits),'pin_layer_basic_spacing_risk':bool(guardhits),'macro_bbox_overlap':macrohit,
               'direct_endpoint_count':len(directs.get(r.pin,[])),'traced_endpoint_count':len(anchors.get(r.pin,[]))}
            for label,target in [('toM6',6),('toM8',8),('toM10',10)]:
                start=int(r.layer.replace('metal',''));env=envcache[start,target] or {r.layer:half}
                hlist=[]
                for l,(hx,hy) in env.items():
                    hlist.extend(index.hits(l,x,y,hx,hy,tech.loc[l,'spacing']/2000,net))
                m[label+'_existing_shape_risk']=bool(hlist)
                if hlist:stats[label+'_risk_pins']+=1
            if r.pin in anchors:
                aa=anchors[r.pin];l1=float(np.min(np.abs(aa-[x,y]).sum(1)));m['nearest_traced_endpoint_L1_um']=l1;l1all.append(l1)
            else:m['nearest_traced_endpoint_L1_um']=''
            if r.pin in directs:
                dd=float(np.min(np.abs(directs[r.pin]-[x,y]).sum(1)));m['nearest_direct_endpoint_L1_um']=dd;dall.append(dd)
            else:m['nearest_direct_endpoint_L1_um']=''
            stats['pin_overlap']+=bool(hits);stats['pin_spacing']+=bool(guardhits)
            stats['pin_pg_overlap']+=any(k.startswith('pg') for _,k in hits)
            stats['macro_bbox_overlap']+=macrohit
            per.append(m);rows.append(m)
        # Candidate/candidate via envelopes; same-net shapes may legally overlap and are excluded.
        pairrisk={}
        for label,target in [('toM6',6),('toM8',8),('toM10',10)]:
            envs=[];maxradius=0
            for i,r in df.iterrows():
                env=envcache[int(r.layer[-1]),target] or {r.layer:(.07,.07)}
                envs.append(env)
                for l,(hx,hy) in env.items():maxradius=max(maxradius,2*max(hx,hy)+tech.loc[l,'spacing']/2000)
            count=0;newcount=0
            for i,j in cKDTree(xy).query_pairs(math.sqrt(2)*maxradius+1e-8):
                if df.loc[i,'net_id']==df.loc[j,'net_id']:continue
                common=set(envs[i])&set(envs[j]);dx,dy=np.abs(xy[i]-xy[j]);risk=False
                for l in common:
                    hx,hy=envs[i][l];qx,qy=envs[j][l];sp=tech.loc[l,'spacing']/2000
                    if dx<hx+qx+sp-1e-8 and dy<hy+qy+sp-1e-8:risk=True;break
                count+=risk
                newcount+=risk and (moved[i] or moved[j])
            pairrisk[label+'_candidate_pairs']=count
            pairrisk[label+'_involving_moved_pairs']=int(newcount)
        bb=bbox(xy);local_area=sum((p['bbox_um'][2]-p['bbox_um'][0])*(p['bbox_um'][3]-p['bbox_um'][1]) for p in patches.get(plan,[]))
        metrics[plan]={'n':n,'moved':int(moved.sum()),'fixed':int((~moved).sum()),'layers':dict(Counter(df.layer)),
                       'functions':dict(Counter(df.interface)),'directions':dict(Counter(df.direction)),
                       'min_nn_um':float(dist.min()),'median_nn_um':float(np.median(dist)),'min_nn_per_layer_um':layer_min,
                       'max_pin_count_20um_square_sampled':maxwin,'density_sampled_max_pins_per_um2':maxwin/400,
                       'within_10um_of_boundary':int((near<=10).sum()),'pin_envelope_um':bb.tolist(),
                       'sum_nonoverlap_patch_envelopes_um2':float(local_area),'patches':len(patches.get(plan,[])),
                       'traced_endpoint_known_pins':len(l1all),'nearest_traced_L1_sum_um':float(sum(l1all)),
                       'nearest_direct_L1_sum_um':float(sum(dall)),'xy_movement_L1_sum_um':float(np.abs(xy-plans['A']).sum()),
                       **dict(stats),**pairrisk}
    table=pd.DataFrame(rows);table.to_csv(ROOT/f'{case}_pin_coordinates.csv',index=False,encoding='utf-8-sig',float_format='%.6f')
    return metrics,table

def background(case,dims):
    cells=physical(case,'cells');res=900;w,h=dims[2:];img=np.ones((res,res,4))
    palette={'CORE_SPACER':'#f1f3f6','CORE_WELLTAP':'#d9b9c8','BLOCK':'#d9dee5','CORE':'#c4cdd9'}
    from matplotlib.colors import to_rgba
    for kind in ['CORE_SPACER','CORE_WELLTAP','CORE','BLOCK']:
        a=cells[cells.type==kind][['x0','y0','x1','y1']].to_numpy(float)/2000
        for x0,y0,x1,y1 in a:
            ix0=max(0,int(x0/w*res));ix1=min(res,max(ix0+1,math.ceil(x1/w*res)))
            iy0=max(0,int(y0/h*res));iy1=min(res,max(iy0+1,math.ceil(y1/h*res)))
            img[iy0:iy1,ix0:ix1]=to_rgba(palette[kind])
    return img

def draw_base(ax,bg,dims,macros):
    w,h=dims[2:];ax.imshow(bg,origin='lower',extent=[0,w,0,h],interpolation='nearest',alpha=.62,zorder=0)
    for m in macros:ax.add_patch(Rectangle(m[:2],m[2]-m[0],m[3]-m[1],fc='#d9dee5',ec='#8391a3',lw=.6,zorder=1))
    ax.add_patch(Rectangle((0,0),w,h,fill=False,ec='#263d58',lw=1.1,zorder=2))
    ax.set_aspect('equal');ax.set_xlim(-w*.025,w*1.025);ax.set_ylim(-h*.025,h*1.025)
    ax.set_xlabel('X (μm)');ax.set_ylabel('Y (μm)');ax.tick_params(labelsize=9)
    ax.grid(color='#d8e1eb',ls='--',lw=.4,alpha=.45)
    for s in ax.spines.values():s.set_visible(False)

def points(ax,df,xy,small=False):
    for (cat,layer),g in df.groupby(['interface','layer']):
        ax.scatter(xy[g.index,0],xy[g.index,1],s=(7 if small else 8),marker='o' if layer=='metal5' else 's',
                   c=COLORS[cat],linewidths=0,zorder=4,alpha=.92)

def plot(case,df,pg,plans,patches,metrics,anchors,dims,macros,index):
    bg=background(case,dims);w,h=dims[2:]
    fig,axes=plt.subplots(1,3,figsize=(19.5,8.8));fig.subplots_adjust(left=.045,right=.985,top=.79,bottom=.25,wspace=.19)
    fig.text(.04,.95,f'{TITLES[case]} | pin 平面位置对照',fontsize=23,weight='bold')
    fig.text(.04,.9,f'{len(df):,} 信号 pin · {w:g} × {h:g} μm · M5 {sum(df.layer=="metal5"):,} / M6 {sum(df.layer=="metal6"):,} · 金属层、网络与方向保持',fontsize=11,color='#56677d')
    legends=[Line2D([0],[0],marker='o',ls='',color=COLORS[k],label=f'{LABELS[k]} ({n:,})',markersize=5) for k,n in Counter(df.interface).items()]
    fig.legend(handles=legends,loc='upper left',bbox_to_anchor=(.037,.875),ncol=min(6,len(legends)),frameon=False,fontsize=9)
    zooms={}
    for ax,(p,xy) in zip(axes,plans.items()):
        draw_base(ax,bg,dims,macros);points(ax,df,xy)
        for pp in patches.get(p,[]):
            bb=pp['bbox_um'];ax.add_patch(Rectangle(bb[:2],bb[2]-bb[0],bb[3]-bb[1],fill=False,ec='#8198ad',lw=.32,alpha=.65,zorder=3))
        if p=='A':
            if case=='act':z=(110,0,145,14)
            else:z=(300,0,355,20)
        else:
            # One actual bundle, never crop away points in the overview.
            pp=max(patches[p],key=lambda q:q['pin_count']);bb=pp['bbox_um'];pad=3 if p=='B' else 5
            z=(max(-2,bb[0]-pad),max(-2,bb[1]-pad),min(w+2,bb[2]+pad),min(h+2,bb[3]+pad))
        zooms[p]=z
        ax.add_patch(Rectangle(z[:2],z[2]-z[0],z[3]-z[1],fill=False,ec='#304d70',lw=1,ls='--',zorder=7))
        ax.set_title(f'{p}. {PLAN[p]}',fontsize=12,loc='left',pad=13,weight='bold')
        m=metrics[p];ax.text(.01,-.16,f'移动 {m["moved"]:,} / 保留 {m["fixed"]:,}；同层最小间距\nM5 {m["min_nn_per_layer_um"]["metal5"]:.3f} / M6 {m["min_nn_per_layer_um"]["metal6"]:.3f} μm',transform=ax.transAxes,fontsize=9,color='#56677d')
    fig.text(.04,.035,'圆 = M5，方 = M6；标记放大，不代表 pin / 通孔尺寸。灰底为实际实例 bbox 栅格投影，不能据此判断金属可用。\nB/C 为候选；已筛查已有金属矩形与 PDN，尚未验证完整接入布线和 DRC。虚线框对应局部放大图。',fontsize=10,color='#56677d',linespacing=1.6)
    fig.savefig(ROOT/f'{case}_comparison.png',dpi=180);fig.savefig(ROOT/f'{case}_comparison.svg');plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(19.5,6.9));fig.subplots_adjust(left=.045,right=.985,top=.79,bottom=.29,wspace=.2)
    fig.text(.04,.94,f'{TITLES[case]} | 密集区局部放大',fontsize=22,weight='bold')
    fig.text(.04,.88,'各方案独立取窗，局部窗口尺度不同；总览三图保持同尺度。背景实线为数据库金属矩形边界；不表示新接入路径。',fontsize=10,color='#56677d')
    for ax,(p,xy) in zip(axes,plans.items()):
        z=zooms[p];draw_base(ax,bg,dims,macros)
        # Existing M5/M6 and M7 PDN geometry: exact rectangles, not schematic paths.
        for l,color in [('metal5','#93b1c5'),('metal6','#c4accf'),('metal7','#d29f58')]:
            a,_,kinds,_=index.layers[l];sel=(a[:,0]<z[2])&(a[:,2]>z[0])&(a[:,1]<z[3])&(a[:,3]>z[1])
            if l=='metal7':sel&=np.char.startswith(kinds,'pg')
            for b in a[sel]:ax.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],fc=color,ec=color,lw=.2,alpha=.35,zorder=2))
        points(ax,df,xy);ax.set_xlim(z[0],z[2]);ax.set_ylim(z[1],z[3]);ax.set_title(f'{p}. {PLAN[p]}',loc='left',fontsize=12)
        inside=np.where((xy[:,0]>=z[0])&(xy[:,0]<=z[2])&(xy[:,1]>=z[1])&(xy[:,1]<=z[3]))[0]
        if len(inside):
            i=inside[len(inside)//2];ax.annotate(df.loc[i,'pin'],xy[i],xytext=(6,15),textcoords='offset points',fontsize=8,
                                            arrowprops=dict(arrowstyle='-',lw=.5,color='#304d70'))
        fig.text(ax.get_position().x0,.14,f'窗口 {z[2]-z[0]:.2f} × {z[3]-z[1]:.2f} μm；{len(inside)} 个信号接点\n彩点为中心示意；点击 HTML 查询逐 pin 矩形',fontsize=9,color='#56677d')
    fig.text(.04,.035,'蓝灰：已有 M5；紫灰：已有 M6；土黄：已有 M7 PG。候选点与旧布线重叠或接近时需要重接 / 绕让，不能视为可直接落点。\n图中没有绘制新通孔尺寸或伪造新线路；具体层级未知时分别按 M6 / M8 / M10 做假设敏感性筛查。',fontsize=10,color='#56677d',linespacing=1.6)
    fig.savefig(ROOT/f'{case}_zoom.png',dpi=180);fig.savefig(ROOT/f'{case}_zoom.svg');plt.close(fig)
    # Show real traced endpoints and geometric lines only, in a separate explicitly labelled panel.
    fig,axes=plt.subplots(1,3,figsize=(18,6.8));fig.subplots_adjust(left=.05,right=.985,top=.79,bottom=.2,wspace=.2)
    fig.text(.04,.94,f'{TITLES[case]} | 接点与实际逻辑端点的几何关系',fontsize=20,weight='bold')
    fig.text(.04,.885,'每个功能类别抽样 2 位；叉号为越过 BUF/INV 后的实际 ITerm 平均几何坐标。虚线是 L1 距离示意，不是布线路径。',fontsize=10,color='#56677d')
    sample=[]
    for cat,g in df.groupby('interface'):
        ids=[i for i in g.index if df.loc[i,'pin'] in anchors]
        if ids:sample.extend([ids[len(ids)//3],ids[2*len(ids)//3]])
    for ax,(p,xy) in zip(axes,plans.items()):
        draw_base(ax,bg,dims,macros);points(ax,df,xy,True)
        for i in sorted(set(sample)):
            r=df.loc[i];aa=anchors[r.pin];q=aa[np.argmin(np.abs(aa-xy[i]).sum(1))];x,y=xy[i];color=COLORS[r.interface]
            ax.plot([x,q[0],q[0]],[y,y,q[1]],color=color,lw=.8,ls='--',alpha=.8,zorder=5)
            ax.scatter(*q,marker='x',s=28,c=color,lw=1,zorder=6)
        ax.set_title(f'{p}. {PLAN[p]}',loc='left',fontsize=11)
    fig.text(.04,.045,'仅用于解释接点选择；buffer 追踪最多 12 级，不移动单元。无 ITerm 的引脚不参与距离求和。\n端点距离和 XY 移动距离均为几何指标，不是路由总线长、提取 RC 或时序改善。',fontsize=10,color='#56677d')
    fig.savefig(ROOT/f'{case}_endpoints.png',dpi=170);fig.savefig(ROOT/f'{case}_endpoints.svg');plt.close(fig)

def validate(case,df,pg,plans,patches,dims,macros,table):
    checks={};n=len(df)
    for p,xy in plans.items():
        t=table[table.plan==p];assert len(t)==n and t.pin.nunique()==n
        for col in ['pin','net','net_id','layer','direction','use','bus','interface']:
            assert list(t[col])==list(df[col]),(case,p,col)
        assert len(np.unique(xy,axis=0))==n,(case,p,'duplicate XY')
        assert np.all(t[['x0_um','y0_um']].to_numpy(float)>=-1e-7)
        assert np.all(t.x1_um<=dims[2]+1e-7) and np.all(t.y1_um<=dims[3]+1e-7)
        assert not t.macro_bbox_overlap.any(),(case,p,'macro overlap')
        for a,b in [('x1_um','x0_um'),('y1_um','y0_um')]:assert np.allclose(t[a]-t[b],df[a]-df[b])
        checks[p]={'signal_count':n,'unique_pin_names':n,'unique_xy':n,'missing':0,'extra':0,'layer_changes':0,
                   'net_changes':0,'direction_changes':0,'out_of_boundary_rectangles':0,'macro_bbox_overlap':0,
                   'rectangle_size_changes':0,'pg_shapes_retained':len(pg),'external_target_layers':'unknown, not reassigned'}
    return checks

def main():
    metrics={};checks={};alltables=[];allpatch={};endpoint_summary={}
    for case in ['act','gemm']:
        print('LOAD',case,flush=True)
        df,pg,anchors,directs,anc,dims,macros,tech=load(case)
        shape=physical(case,'shapes');index=ShapeIndex(shape)
        groups=groups_for(case,df)
        print('LAYOUT',case,len(shape),'shapes',flush=True)
        plans,patch=propose(case,df,groups,anchors,dims,macros,index,tech)
        mm,table=evaluate(case,df,plans,patch,anchors,directs,dims,macros,index,tech)
        checks[case]=validate(case,df,pg,plans,patch,dims,macros,table)
        print('PLOT',case,flush=True);plot(case,df,pg,plans,patch,mm,anchors,dims,macros,index)
        metrics[case]=mm;allpatch[case]=patch;alltables.append(table)
        pd.DataFrame([{'plan':p,'group':g,'pin':df.loc[i,'pin'],'semantic':sem} for p,gg in [('A',groups),('B',groups_for(case,df,True)),('C',groups)] for g,ids,sem in gg for i in ids]).to_csv(ROOT/f'{case}_groups.csv',index=False,encoding='utf-8-sig')
        # PG remains an explicit separate full inventory in every plan.
        pd.concat([pg.assign(plan=p) for p in 'ABC']).to_csv(ROOT/f'{case}_pg_coordinates.csv',index=False,encoding='utf-8-sig')
        endpoint_summary[case]={'signal_pins':len(df),'direct_known':len(directs),'traced_known':len(anchors),
                                'missing_traced':[p for p in df.pin if p not in anchors],
                                'max_buffer_depth':int(anc.depth.max()),'traced_iterms':len(anc)}
    pd.concat(alltables).to_csv(ROOT/'all_pin_coordinates.csv',index=False,encoding='utf-8-sig',float_format='%.6f')
    savejson('metrics.json',metrics);savejson('validation.json',{'passed':True,'cases':checks,'scope':'geometry/inventory only; not a DRC pass'})
    savejson('proposed_patches.json',allpatch);savejson('endpoint_coverage.json',endpoint_summary)
    from build_report import build
    build(metrics,allpatch,endpoint_summary)
    print('COMPLETE',ROOT,flush=True)

if __name__=='__main__':main()
