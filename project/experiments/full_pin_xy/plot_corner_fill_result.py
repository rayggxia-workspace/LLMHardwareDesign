"""Draw measured M5 before/after geometry, never candidate pin markers."""
from pathlib import Path
from collections import Counter
import csv,gzip,hashlib,json,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def run(repo):
    repo=Path(repo);out=repo/'docs/experiments/issue-126-resume-20261030';source=out/'ll-corner-fill'
    q=json.loads((source/'execution.json').read_text());plan=json.loads((source/'local_geometry_and_patch_proof.json').read_text())
    assert q.get('completed_utc') and not q.get('actual_failure') and q['fresh_DRC_count']==0
    assert q['all_original_WIRE_VIA_exact_plus_requested_patch_rectangles']
    old=source/'source_before6.drc.gz'
    if not old.exists():
        original=repo/'docs/experiments/issue-126-full-pin/data/deadline_receipts/llsys100-gap-heal-r02/independent.drc.gz'
        old.write_bytes(gzip.compress(gzip.decompress(original.read_bytes()),mtime=0))
    raw=gzip.decompress(old.read_bytes());expected=next(v for p,v in q['source_SHA'].items() if p.endswith('/llsys_same_net_gap_heal/r02/independent.drc'))
    assert hashlib.sha256(raw).hexdigest()==expected
    markers=[(n,tuple(map(float,[a,b,c,d]))) for n,a,b,c,d in re.findall(r'srcs: net:(\S+)\s+bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer metal5',raw.decode())]
    assert len(markers)==6
    with gzip.open(source/'target_access.tsv.gz','rt') as f:
        after=[(r['net'],tuple(int(r[k]) for k in ['x0','y0','x1','y1']),r['kind']) for r in csv.DictReader(f,delimiter='\t') if r['layer']=='metal5']
    extra=Counter((r['net'],tuple(r['box_DBU']),'WIRE') for r in plan['actual_new_default_width_WIRE_strips'])
    before=[];remaining=extra.copy()
    for row in after:
        if remaining[row]:remaining[row]-=1
        else:before.append(row)
    assert not +remaining and len(after)-len(before)==9
    plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'svg.hashsalt':'p126-measured-corner-fill'})
    fig,axes=plt.subplots(2,3,figsize=(14,9.8));fig.subplots_adjust(left=.07,right=.97,top=.84,bottom=.22,hspace=.40,wspace=.30)
    fig.text(.05,.955,'LL SYSTEM | 真实 M5 接入：6 条间距违规 → 0',fontsize=20,weight='bold',color='#17283c')
    fig.text(.05,.907,'实际数据库局部补平；13,507 个信号 pin 保留。局部间距已修复，父层接入与速度仍有失败。',fontsize=10.5,color='#56677d')
    cases=[('bit_7059','bank_rdata[1561]'),('bit_1382043','gemm_w_rdata[421]'),('bit_1383573','gemm_w_rdata[1951]')]
    for col,(net,meaning) in enumerate(cases):
        region=next(r for r in plan['regions'] if r['net']==net)['actual_fill_envelope_DBU'];cx=(region[0]+region[2])/4000.;cy=(region[1]+region[3])/4000.
        for row,geometries in enumerate([before,after]):
            ax=axes[row,col]
            for n,box,kind in geometries:
                if n!=net:continue
                a,b,c,d=[v/2000. for v in box]
                if c<cx-.9 or a>cx+.9 or d<cy-.9 or b>cy+.9:continue
                ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#2a87a8',edgecolor='#2a87a8',alpha=.62,lw=.4))
            if not row:
                for n,(a,b,c,d) in markers:
                    if n==net:ax.add_patch(Rectangle((a,b),c-a,d-b,fill=False,edgecolor='#c24f46',lw=1.4,zorder=7))
            else:
                for p in plan['actual_new_default_width_WIRE_strips']:
                    if p['net']!=net:continue
                    a,b,c,d=[v/2000. for v in p['box_DBU']]
                    ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#b7dfc4',edgecolor='#377a50',hatch='///',alpha=.85,lw=.6,zorder=6))
            ax.set_xlim(cx-.9,cx+.9);ax.set_ylim(cy-.9,cy+.9);ax.set_aspect('equal');ax.grid(alpha=.13);ax.set_axisbelow(True)
            ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=8);ax.set_xlabel('x (μm)',fontsize=9);ax.set_ylabel('y (μm)',fontsize=9)
            ax.set_title(('实际旧源：此网 2 项间距违规' if not row else '实际新源：独立 native 检查 0 项')+'\n'+net+' / '+meaning,fontsize=9.5,color='#17283c')
    fig.legend([Rectangle((0,0),1,1,color='#2a87a8'),Rectangle((0,0),1,1,facecolor='#b7dfc4',edgecolor='#377a50',hatch='///'),Rectangle((0,0),1,1,fill=False,edgecolor='#c24f46')],
               ['实际同网 M5 金属','实际新增 9 条原宽 M5 WIRE（每网 3 条）','旧源实际违规范围'],loc='lower left',bbox_to_anchor=(.05,.14),ncol=3,frameon=False,fontsize=9)
    fig.text(.05,.045,'每列前后均为相同 1.8 × 1.8 μm 窗口；金属按真实尺寸绘制，红框不是 pin 或通孔尺寸。仅展示三网 M5，未绘区域不能视为空白。\n9 条填补线均符合 0.005 μm 制造网格；其中 6 条不在首选轨道中心。未改 pin、via、原规则、单元、供电或外框。\n叶内 pin_access 命令返回 0，所列几何保持/双电源连通通过；父层 bit_1016 接入失败。max −3.909006 ns、removal −0.587521 ns。\n所报 hold −0.340494 ns；完整规则/GDS/两种系统功能未通过，不声称速度或面积改善。源驱动 84a3cce；ODB SHA256 1bd4aa52…53057b。',fontsize=8.8,color='#56677d',linespacing=1.5)
    assets=out/'assets';assets.mkdir(exist_ok=True);fig.savefig(assets/'ll-corner-fill-6-to-0.png',dpi=170)
    fig.savefig(assets/'ll-corner-fill-6-to-0.svg',metadata={'Date':None});plt.close(fig)
    svg=assets/'ll-corner-fill-6-to-0.svg';svg.write_bytes(('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n').encode('utf-8'))
    record={'scope':'ACTUAL_DB_METAL_MEASURED_BEFORE_AFTER_NOT_CANDIDATE','source_receipt_SHA256':hashlib.sha256((source/'execution.json').read_bytes()).hexdigest(),
            'source_ODB_SHA256':q['files']['routed.odb']['sha256'],'old_native_DRC':6,'new_native_DRC':0,'whole_qualification':False,
            'before_geometry_derivation':'Exact source-bound after WIRE/VIA geometry minus the 9 proved actual additions; all original shapes preserved by completed certificate.',
            'old_marker_source_SHA256':expected,'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in assets.iterdir()}}
    (out/'figure_provenance.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':run(Path(__file__).resolve().parents[3])
