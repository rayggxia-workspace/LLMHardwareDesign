"""Build the standalone module/interface report from read-only measured artifacts.

Writes only 模块与接口报告.html and outputs/module-interface-report-20261020.
No changes to the two main reports or their input datasets.
"""
from pathlib import Path
import ast, collections, csv, gzip, hashlib, html, json, re, math, subprocess, sys
from bs4 import BeautifulSoup
from urllib.parse import quote, urlsplit, unquote
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
H=ROOT/'outputs/bus-comparison-20261020'
FULL=H/'opentpu-tmem-fullpath'
REPORT=ROOT/'模块与接口报告.html'
LL=OUT/'llaccel'
# One report entry point; llaccel scripts emit assets/sections, not a standalone page.
subprocess.run([sys.executable,str(LL/'build_llaccel_section.py')],check=True)
subprocess.run([sys.executable,str(LL/'build_llaccel_diagrams.py')],check=True)
LD=json.loads((LL/'summary.json').read_text(encoding='utf8'))
LP=json.loads((LL/'declared_ports.json').read_text(encoding='utf8'))
def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def gz(p):return json.load(gzip.open(p,'rt',encoding='utf8'))
GEM=load(H/'gemmini-blackbox/summary.json')
MXU=load(H/'opentpu-mxu-blackbox/summary.json')
TV=load(H/'opentpu-tmem-vpu/summary.json')
FD=gz(FULL/'fullpath-physical.json.gz')
FS=load(FULL/'summary.json')
ACT=load(OUT/'act-interface.json')
MP=gz(H/'mxu-interface-physical.json.gz')
TP=gz(H/'tmem-vpu-interface-physical.json.gz')
NET={n['id']:n for n in FD['nets']}
SETS=collections.defaultdict(set)
for n in NET.values():
    for g in n['groups']:SETS[g].add(n['id'])
LAYERS=[f'metal{i}' for i in range(2,11)]
COLORS=['#2563a6','#36a3bc','#48a47b','#e5a124','#d65a48','#9872b6','#845940','#d369a3','#656b75']
plt.rcParams.update({'font.family':'Microsoft YaHei','axes.unicode_minus':False,'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white','savefig.facecolor':'white'})

def esc(x):return html.escape(str(x))
def rel(p):return Path(p).relative_to(ROOT).as_posix()
def link(p,label):return f'<a href="{esc(rel(p))}">{esc(label)}</a>'
def table(headers,rows):
    return '<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
FIGURES=[]
def fig(p,caption,title=None):
    p=Path(p);assert p.exists(),p;FIGURES.append(p)
    return (f'<div class="visible-chart">'+(f'<h3>{esc(title)}</h3>' if title else '')+
            f'<figure><a href="{esc(rel(p))}" target="_blank"><img loading="lazy" src="{esc(rel(p))}" alt="{esc(caption)}"></a><figcaption>{caption} 点击图像查看原尺寸。</figcaption></figure></div>')
def detail(title,body):return f'<details><summary>{esc(title)}</summary><div class="detail-body">{body}</div></details>'
def lit(script,name):
    for x in ast.parse(script.read_text(encoding='utf8')).body:
        if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in x.targets):return ast.literal_eval(x.value)
    raise KeyError(name)

def stat(ns):
    ns=list(ns);ls=collections.Counter()
    for n in ns:ls.update(n['layers'])
    total=sum(ls.values());v=[(n.get('length_dbu') or 0)/2000 for n in ns]
    return dict(nets=len(ns),length_um=total/2000,mean_net_um=sum(v)/len(v) if v else 0,min_net_um=min(v,default=0),max_net_um=max(v,default=0),
                layers_um={l:ls[l]/2000 for l in LAYERS},pct={l:100*ls[l]/total if total else 0 for l in LAYERS},
                high_pct=100*(total-ls['metal2']-ls['metal3'])/total if total else 0)
S={k:stat(NET[i] for i in ids) for k,ids in SETS.items()}
VIF={pn:stat(n for n in TP['nets'] if any(k.startswith('VPU:'+pn+'[') for k in n['keys'])) for pn in ('ta_data','tb_data','tw_data')}
PAIRS=[('MXU 写结果 → TMEM SRAM','MXU_WRITE_FULL',S['MXU_WRITE_INTERFACE']),
       ('TMEM SRAM → MXU 旧值','MXU_READ_FULL',S['MXU_READ_INTERFACE']),
       ('TMEM SRAM → VPU 操作数 A','R3_FULL',VIF['ta_data']),
       ('TMEM SRAM → VPU 操作数 B','R4_FULL',VIF['tb_data']),
       ('VPU 结果 → TMEM SRAM','W3_FULL',VIF['tw_data'])]
for k,v in FS['stats'].items():
    assert abs(S[k]['length_um']-v['length_um'])<1e-7
assert MP['net_sha256']==TP['nets_sha256']==FD['net_sha256']
assert GEM['logical_bits']==dict(INPUT=124,OUTPUT=233,TOTAL=357)
assert (ACT['input_bits'],ACT['output_bits'])==(220,640)
assert TV['validation'] and all(TV['validation'].values())
assert FD['validation']['unsupported_tmem_pins']=={}
assert not FD['validation']['layer_sum_errors']
for label,k,_ in PAIRS:
    pre=k.removesuffix('_FULL');path=FD['paths'][pre]
    assert path.get('anchors_reaching_sram',path.get('anchors_from_sram'))==path['anchors']
assert SETS['MXU_WRITE_FULL']==SETS['W1_FULL'] and SETS['MXU_READ_FULL']==SETS['R0_FULL']

def save(fig,name):
    for suffix in ('png','svg'):fig.savefig(OUT/(name+'.'+suffix),dpi=180,bbox_inches='tight')
    plt.close(fig)

labels=[p[0] for p in PAIRS]+['ACT_RAM SRAM → MXU 激活数据','ACT_RAM SRAM → MXU 尺度记录']
keys=[p[1] for p in PAIRS]+['ACT_DATA','ACT_SCALE']
f,ax=plt.subplots(figsize=(14,7));left=[0.]*len(keys)
for layer,col in zip(LAYERS,COLORS):
    vs=[S[k]['pct'][layer] for k in keys]
    ax.barh(range(len(keys)),vs,left=left,height=.65,color=col,label=layer.replace('metal','M'))
    for j,(v,l) in enumerate(zip(vs,left)):
        if v>=10:ax.text(l+v/2,j,f'{v:.1f}%',ha='center',va='center',fontsize=10,color='#172536' if layer=='metal5' else 'white')
    left=[a+b for a,b in zip(left,vs)]
ax.set_yticks(range(len(keys)),labels);ax.invert_yaxis();ax.set_xlim(0,100)
ax.set_xlabel('每条数据通路内部，按实际线长计算的金属层占比（%）')
ax.set_title('追踪到 SRAM 宏引脚：七组数据连接的金属层分布',fontsize=18,loc='left',pad=47,weight='bold')
ax.legend(ncol=9,loc='lower left',bbox_to_anchor=(0,1.01),frameon=False)
ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
for j,k in enumerate(keys):ax.text(101,j,f"{S[k]['length_um']/1000:.2f} mm",va='center',fontsize=10)
ax.text(101,-.7,'线长合计',fontsize=10)
f.text(.015,-.035,'TMEM 路径穿过选择器和数据寄存器；ACT 路径为宏读出到 MXU 的电气连接。不同路径可共用物理 net，不能直接相加。',fontsize=10,color='#57677b')
save(f,'01-complete-data-layers')

f,ax=plt.subplots(figsize=(13.5,6.5));yy=list(range(len(PAIRS)))
for offset,color,kind in [(-.18,'#92b4d0','接口电连接'),(.18,'#176b89','补全至 SRAM')]:
    vs=[p[2]['high_pct'] if kind=='接口电连接' else S[p[1]]['high_pct'] for p in PAIRS]
    ax.barh([y+offset for y in yy],vs,height=.31,color=color,label=kind)
    for y,v in zip(yy,vs):ax.text(v+1,y+offset,f'{v:.2f}%',va='center',fontsize=10)
ax.set_yticks(yy,[p[0] for p in PAIRS]);ax.invert_yaxis();ax.set_xlim(0,105)
ax.set_xlabel('M4 及以上的线长占比（%）');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
ax.set_title('同一个功能方向，统计到哪里会改变对金属层的判断',fontsize=18,loc='left',pad=32,weight='bold')
ax.legend(ncol=2,loc='lower left',bbox_to_anchor=(0,1),frameon=False)
f.text(.02,-.04,'两组统计有涵盖关系，不是新增带宽或两套独立线路。VPU 原接口网包含同信号分发支路；完整路径只继续保留能通到 SRAM 的数据支路。',fontsize=10,color='#57677b')
save(f,'02-interface-vs-complete')

# SVG diagrams remain crisp and editable; all dimensions below are schematic.
class SVG:
    def __init__(self,w,h,title):
        self.w=w;self.h=h;self.a=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">',
         '<style>text{font-family:"Microsoft YaHei","Segoe UI",sans-serif;fill:#203042} .sub{fill:#586b80}</style>',
         f'<rect width="{w}" height="{h}" fill="white"/>']
    def text(self,x,y,lines,size=20,color='#203042',anchor='start',bold=False,gap=None):
        if isinstance(lines,str):lines=[lines]
        gap=gap or size*1.6
        for j,t in enumerate(lines):self.a.append(f'<text x="{x}" y="{y+j*gap}" font-size="{size}" text-anchor="{anchor}" style="fill:{color};font-weight:{700 if bold else 400}">{esc(t)}</text>')
    def rect(self,x,y,w,h,color='#f2f5f9',edge='#d4dfeb',r=12,dash=False):self.a.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{color}" stroke="{edge}" stroke-width="2"'+(' stroke-dasharray="8 5"' if dash else '')+'/>')
    def path(self,d,color='#427a9b',dash=False,arrow=True):
        self.a.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="3"'+(' stroke-dasharray="8 5"' if dash else '')+'/>')
        if arrow:
            pts=[(float(x),float(y)) for x,y in re.findall(r'[ML]\s*([-+\d.]+)\s+([-+\d.]+)',d)]
            (x0,y0),(x,y)=pts[-2:];length=math.hypot(x-x0,y-y0);ux=(x-x0)/length;uy=(y-y0)/length
            points=[(x,y),(x-13*ux+5*uy,y-13*uy-5*ux),(x-13*ux-5*uy,y-13*uy+5*ux)]
            self.a.append('<polygon points="'+' '.join(f'{a:g},{b:g}' for a,b in points)+f'" fill="{color}"/>')
    def write(self,name):
        p=OUT/name;p.write_text(''.join(self.a)+ '</svg>',encoding='utf8');return p

s=SVG(1440,850,'openTPU small 典型数据流和控制关系')
s.text(40,42,'openTPU small：计算、共享存储与量化输入怎样连接',28,bold=True)
s.rect(40,80,650,105,'#f2eef8','#cfc4e4',dash=True)
s.text(65,115,'SEQUENCER：调度和依赖控制',22,color='#6d5298',bold=True)
s.text(65,150,'向 MXU / VPU / QUANT 发命令；图中主体箭头只画数据流',19)
s.rect(1000,80,380,110,'#eef3fa','#c0d2e8')
s.text(1190,115,'共享存储读取通道',21,anchor='middle',bold=True)
s.text(1190,150,'A：尺度 256 bit · B：权重块 256 bit',18,anchor='middle')
s.path('M 1240 190 L 1240 300',color='#457cb5')
s.text(1260,250,'数据输入',18,color='#457cb5')
for x,w,t,ls,bg,edge in [(40,285,'TMEM',['FP32 共享工作存储','多个计算与搬运单元访问'],'#fff2e8','#dd8b5d'),(450,220,'QUANT',['量化与尺度生成','FP32 → INT8 + 记录'],'#f2f8e8','#9bb85c'),(790,230,'ACT_RAM',['存 INT8 激活与 scale','为 MXU 提供输入'],'#f0eef9','#9a91c6'),(1130,250,'MXU',['矩阵运算','结果写回 TMEM'],'#eaf6ef','#74ac8e')]:
    s.rect(x,300,w,180,bg,edge);s.text(x+w/2,342,t,27,anchor='middle',bold=True);s.text(x+w/2,390,ls,18,anchor='middle')
s.path('M325 380 L450 380',color='#c66d3b');s.text(388,345,['读取','FP32'],17,anchor='middle',color='#a75e34')
s.path('M670 380 L790 380',color='#769e38');s.text(730,345,['量化数据','＋ scale'],17,anchor='middle',color='#648b2d')
s.path('M1020 380 L1130 380',color='#7165a6');s.text(1075,337,['512 bit','＋128 bit'],17,anchor='middle',color='#7165a6')
s.path('M1240 480 L1240 555 L305 555 L305 480',color='#ca6a35')
s.text(805,540,'MXU 结果写回：t_wdata 声明 128 bit；也可读取 TMEM 旧值参与累加',18,anchor='middle',color='#a55d32')
s.rect(40,665,285,140,'#faeeed','#cb827d');s.text(182,704,'VPU',27,anchor='middle',bold=True);s.text(182,745,['FP32 向量运算','从 TMEM 取数、写回 TMEM'],18,anchor='middle')
s.path('M120 480 L120 665',color='#407caa');s.text(145,594,['A/B 操作数','各 128 bit'],17,color='#407caa')
s.path('M270 665 L270 480',color='#c66d3b');s.text(290,624,['结果数据','128 bit'],17,color='#a55e34')
s.rect(450,665,930,140,'#f6f8fb','#dbe3ec',dash=True)
s.text(480,705,'这是一条典型处理链，不是所有任务必须执行的固定顺序。',21,bold=True)
s.text(480,745,['VPU 也能处理预处理、归约等任务；TMEM 还服务其他访问方。','ACT_RAM 的 ACT 指激活数据存储，并不在其中计算激活函数。'],19)
FLOW=s.write('03-system-dataflow.svg')

s=SVG(1440,680,'ACT_RAM 与 TMEM 的逻辑容量和 SRAM 映射')
s.text(40,42,'ACT_RAM 与 TMEM：都包含 SRAM 宏，职责和组织不同',28,bold=True)
s.rect(35,85,585,540,'#f7f5fc','#c5bddf');s.rect(655,85,750,540,'#fff8f2','#e4b28f')
s.text(65,130,'ACT_RAM：量化激活输入缓冲',25,color='#635496',bold=True)
s.text(65,170,['2 KiB INT8 数据 + 512 B 尺度记录','2 行 × 32 块 × 每块 32 字节'],21)
for row in range(2):
    y=275+row*120;s.text(65,y-15,f'激活行 {row}',19,color='#635496',bold=True)
    for x,w,lab in [(65,150,'数据 32×128'),(230,150,'数据 32×128'),(395,180,'scale 32×64')]:
        s.rect(x,y,w,65,'#e2dcf3','#a99bcf',r=6);s.text(x+w/2,y+39,lab,18,anchor='middle')
s.text(65,555,['合计：4 块数据宏 + 2 块 scale 宏','两个数据宏并成每行 256 bit，scale 每行 64 bit'],19,color='#635496')
s.text(685,130,'TMEM：FP32 共享工作存储',25,color='#ab5d2d',bold=True)
s.text(685,170,['逻辑容量 64 KiB = 16,384 × 32 bit','3 份一致副本；每份 4 bank，共 12 块宏'],21)
for row in range(3):
    y=265+row*83;s.text(685,y+38,f'副本 {row+1}',18,color='#a35b31')
    for b in range(4):
        x=790+b*145;s.rect(x,y,130,60,'#f8ddc7','#d49a73',r=6);s.text(x+65,y+25,f'Bank {b}',17,anchor='middle');s.text(x+65,y+48,'4096×32',16,anchor='middle')
s.text(685,555,['物理存储位合计 192 KiB，但逻辑可用容量仍为 64 KiB。','副本帮助安排读访问；写入需更新全部副本。'],19,color='#a35b31')
s.text(40,660,'宏内的存储阵列固定在宏块内部；选择器、流水寄存器、保持／旁路逻辑是宏外的标准单元。图中排布是结构示意。',19,color='#5a6b7f')
MEMORY=s.write('04-memory-organization.svg')

s=SVG(1440,710,'ACT_RAM 的逻辑输入输出和位宽')
s.text(35,43,'openTPU small：ACT_RAM 的逻辑接口',28,bold=True)
s.text(35,80,'原始展开网表：输入 220 bit / 输出 640 bit；下图为逻辑分组，不代表所有声明位都有保留布线。',20,color='#607087')
s.rect(585,135,285,485,'#efedf8','#b7afd1')
s.text(727,190,'ACT_RAM',31,anchor='middle',bold=True)
s.text(727,250,['2 行激活输入缓冲','INT8 数据 + scale','6 块 SRAM 宏','外加写入流水逻辑'],23,anchor='middle',gap=48)
s.text(727,525,['不计算 ReLU / GELU','不存一般 FP32 中间结果'],19,anchor='middle',color='#675c86')
left=[(140,'量化器 → 写数据','w_data 32 + we 4 = 36 bit','每次最多写 4 个连续 INT8 字节'),
      (245,'量化器 → 行号／索引／复制','w_row 8 + w_idx 32 + w_dup 1 + w_off 8 = 49 bit','定位要写入的位置；支持复制写'),
      (350,'量化器 → 尺度记录','s_data 64 + swe 1 + s_row 8 + s_blk 16 = 89 bit','64 bit 记录 = FP32 Sa + 四个 8 bit 子块偏移'),
      (455,'MXU 相关读控制 → ACT_RAM','块号／分组／读使能 44 + r_use 1 = 45 bit','r_use 表示本次读数据被消费；主要用于仿真检查'),
      (560,'基础控制 → ACT_RAM','clk = 1 bit','与数据路径分开；220 = 36 + 49 + 89 + 45 + 1')]
for y,t,b,sub in left:
    s.rect(30,y,505,86,'#f5f7fa','#e0e6ef',r=7);s.text(48,y+25,t,19,color='#67569c',bold=True);s.text(48,y+51,b,18,bold=True);s.text(48,y+75,sub,16,color='#68798c');s.path(f'M535 {y+43} L585 {y+43}',color='#8878b4')
for y,t,b,sub in [(210,'ACT_RAM → MXU 激活数据','r_data = 512 bit','2 行 × 32 字节 × 8 bit'),(395,'ACT_RAM → MXU 尺度记录','r_scale = 128 bit','2 行 × 64 bit')]:
    s.rect(925,y,480,132,'#f0edf8','#d4cbe8',r=7);s.text(945,y+36,t,21,color='#67569c',bold=True);s.text(945,y+76,b,25,bold=True);s.text(945,y+109,sub,19,color='#68798c');s.path(f'M870 {y+66} L925 {y+66}',color='#8878b4')
s.text(35,690,'读出数据和尺度已从 SRAM 宏引脚追到 MXU；量化器写入方向的完整多级路径未在本次重新逐段统计。',19,color='#596b80')
ACTFIG=s.write('05-act-interface.svg')

s=SVG(1440,600,'逻辑接口、宏连接段、完整数据通路的统计范围')
s.text(35,45,'一条数据通路，三个需要区分的统计范围',28,bold=True)
for x,w,t,ls,bg in [(40,240,'MXU / VPU',['计算结果输出逻辑'],'#eaf3f8'),(450,270,'TMEM 接口逻辑',['选择器 / 数据寄存器'],'#fff2e8'),(875,250,'TMEM 后续逻辑',['选择、流水及分发'],'#fff2e8'),(1230,175,'SRAM 宏',['固定的存储块'],'#f6dfcc')]:
    s.rect(x,180,w,140,bg,'#cbd7e4');s.text(x+w/2,225,t,24,anchor='middle',bold=True);s.text(x+w/2,270,ls,18,anchor='middle')
s.path('M280 250 L450 250','#2686a1');s.text(365,218,'接口段',20,color='#2686a1',anchor='middle')
s.path('M720 250 L875 250','#a57c54');s.text(797,218,'内部连接',19,color='#8d6b4c',anchor='middle')
s.path('M1125 250 L1230 250','#cc7c28');s.text(1177,147,['可含','BUF/INV'],17,color='#a46726',anchor='middle')
s.path('M1125 350 L1230 350','#cc7c28',arrow=False);s.text(1177,385,'SRAM 宏连接段',21,color='#a46726',anchor='middle')
s.path('M40 440 L1230 440','#1e6f87',arrow=False);s.text(635,480,'完整数据通路：继续穿过 TMEM 选择器和数据寄存器，一直追到 SRAM 宏引脚',23,color='#1e6f87',anchor='middle',bold=True)
s.text(35,550,['中间若经过逻辑门／寄存器，数据继续传递，但已是多条不同的物理 net；同一 net 本身也可经过多个金属层。','本文“完整”只针对指定读写数据两端，不包含宏内部金属，也不自动包含地址、请求、使能、时钟和电源。'],19,color='#5b6d80')
SCOPE=s.write('06-routing-scope.svg')

# Logical port details reuse definitions without executing earlier build scripts.
MM=lit(H/'build_mxu_blackbox.py','meaning')
VM=lit(H/'build_tmem_vpu_report.py','MEAN_V')
TM=lit(H/'build_tmem_vpu_report.py','MEAN_T')
AM={
 'clk':'ACT_RAM 时钟。','we':'4 个字节写使能，各对应一个 INT8 输入。','w_row':'要写入的激活行号。','w_idx':'行内字节位置。','w_data':'4 个连续 INT8 字节。',
 'w_dup':'同时复制写到另一行的控制。','w_off':'复制目的行相对当前行的偏移。','swe':'允许写入尺度记录。','s_row':'尺度记录对应的激活行。','s_blk':'尺度记录对应的块。','s_data':'Sa FP32 与四个 8 bit 子块偏移，共 64 bit。',
 'ren':'两列各一位读推进使能。','r_use':'本次读取的数据已被消费；RTL 用于仿真一致性检查，不能默认存在专用物理网。','r_blk':'读取块号。','r_blk2':'配对读取使用的第二块号。','r_hi':'各列选择普通或配对块号。','r_grp':'激活行组索引；当前 ROWS=MCOLS。','r_data':'两行各 256 bit，合计 512 bit 激活数据。','r_scale':'两行各 64 bit，合计 128 bit 尺度记录。'}
def port_table(unit):
    rows=[]
    if unit=='MXU':
        bits=list(csv.DictReader((H/'opentpu-mxu-blackbox/port-bits.csv').open(encoding='utf-8-sig')))
        grouped=collections.defaultdict(list)
        for p in bits:grouped[p['port']].append(p)
        for pn,ps in grouped.items():
            n=sum(p['physical_status']=='routed_anchor_found' for p in ps)
            extra='时钟／复位单列' if pn in ('clk','rst') else f'已定位 {n}/{len(ps)} bit；未定位不等于不存在'
            rows.append([f'<code>{esc(pn)}</code>','输入' if ps[0]['direction']=='input' else '输出',len(ps),esc(MM[pn]),extra])
    elif unit in ('VPU','TMEM'):
        means=VM if unit=='VPU' else TM
        for pn,v in TV['ports'][unit].items():
            st=v['status'];n=st.get('routed',0)
            extra='本配置未启用／固定输出' if st.get('inactive') else '时钟／复位／调试单列' if st.get('base') else f'已定位 {n}/{v["width"]} bit'
            meaning=means.get(pn,'流式引擎接口；当前 HAS_DSTEP=0，未启用。')
            rows.append([f'<code>{esc(pn)}</code>','输入' if v['direction']=='input' else '输出',v['width'],esc(meaning),extra])
    else:
        for p in ACT['ports']:
            status='512/512 bit 读出已定位' if p['name']=='r_data' else '128/128 bit 读出已定位' if p['name']=='r_scale' else '本节仅核对声明；不假定逐位物理保留'
            rows.append([f'<code>{esc(p["name"])}</code>','输入' if p['direction']=='input' else '输出',p['width'],esc(AM[p['name']]),status])
    return table(['命名端口','相对本模块方向','声明 bit','含义','物理定位／配置状态'],rows)

gemrows=[]
for g in GEM['groups']:
    pins='、'.join(f'{l}：{v} bit' for l,v in sorted(g['pin_layer_counts'].items()))
    gemrows.append([esc(g['title']),'输入' if g['direction']=='INPUT' else '输出',g['bits'],pins])
functional=[('MXU','COMMAND','命令与任务控制'),('MXU','ACT','ACT 数据、尺度及读控制'),('MXU','SCALE_A','A 存储口：尺度读取'),('MXU','WEIGHT_B','B 存储口：权重读取'),('MXU','TMEM','TMEM 数据、地址及使能接口'),('MXU','PROFILE','内部仍使用的状态／统计'),
            ('VPU','A_DATA','操作数 A 数据'),('VPU','B_DATA','操作数 B 数据'),('VPU','RESULT_DATA','结果写回数据'),('VPU','A_ADDR','A 路读地址'),('VPU','B_ADDR','B 路读地址'),('VPU','RESULT_ADDR','写地址'),('VPU','READ_REQ','读请求／使能'),('VPU','WRITE_REQ','写请求／使能'),('VPU','ACCESS','访问许可及分发'),('VPU','CMD','命令参数'),('VPU','TASK','命令接收／完成')]
funrows=[]
for unit,key,label in functional:
    st=MXU['groups'][key] if unit=='MXU' else TV['function_layers']['VPU'][key]
    ls=st['layers'];total=sum(ls.values());dominant=sorted(ls,key=ls.get,reverse=True)[:3]
    funrows.append([unit,esc(label),st['nets'],f'{total/2000/1000:.3f}','、'.join(l.replace('metal','M')+f' {100*ls[l]/total:.1f}%' for l in dominant)])

fullrows=[];summaryrows=[]
for label,k,ifs in PAIRS:
    st=S[k];dom=sorted(st['pct'],key=st['pct'].get,reverse=True)[:3]
    fullrows.append([esc(label),st['nets'],f'{st["length_um"]/1000:.3f}',f'{st["mean_net_um"]:.2f}',f'{st["min_net_um"]:.2f}～{st["max_net_um"]:.2f}','、'.join(l.replace('metal','M')+f' {st["pct"][l]:.1f}%' for l in dom)])
    summaryrows.append([esc(label),f'{ifs["high_pct"]:.2f}%',f'<strong>{st["high_pct"]:.2f}%</strong>'])

CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f3f6fa;color:#203042;font:16px/1.75 "Microsoft YaHei",system-ui,sans-serif}main{max-width:1440px;margin:auto;padding:36px 32px 70px;min-width:0}header,section,footer{background:#fff;border:1px solid #dce4ee;border-radius:12px;padding:28px;margin:0 0 26px;min-width:0}h1{font-size:34px;line-height:1.35;margin:8px 0 14px}h2{font-size:27px;margin:0 0 14px;line-height:1.45}h3{font-size:21px;line-height:1.5;margin:26px 0 12px}p{margin:12px 0}a{color:#1266ad;text-decoration:none}a:hover{text-decoration:underline}nav{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}nav a{background:#eef3f8;padding:7px 13px;border-radius:6px}.eyebrow{color:#176c83;font-size:13px;letter-spacing:1px;font-weight:700}.lead{font-size:19px;color:#1e6077}.small,figcaption{font-size:14px;color:#5b6d80}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0}.metric{padding:16px;background:#f3f7fa;border:1px solid #e0e7ee;border-radius:9px}.metric strong{font-size:25px;display:block;color:#155d76}.metric span{font-size:13px;color:#5c6d7e}.takeaway{background:#edf6f8;border-left:4px solid #1b849c;padding:15px 20px;margin:18px 0;border-radius:4px}.note{background:#fff8e9;border-left:4px solid #dfa036;padding:14px 19px;margin:18px 0;border-radius:4px}.case-conclusions ul{margin:10px 0;padding-left:24px}.case-conclusions li{margin:7px 0}figure{margin:18px 0 8px}img{display:block;width:100%;max-width:100%;height:auto}figcaption{margin-top:10px;line-height:1.65}.visible-chart{margin:24px 0}.table-scroll{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;margin:16px 0}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:10px 12px;border-bottom:1px solid #e3e9ef;text-align:left;vertical-align:top}th{background:#eef3f8;white-space:nowrap}td{font-variant-numeric:tabular-nums}tr:hover td{background:#f8fafc}code{font-family:Consolas,monospace;font-size:13px;overflow-wrap:anywhere}details{margin:20px 0;padding:14px 18px;background:#f7f9fc;border:1px solid #e0e7ee;border-radius:8px}summary{cursor:pointer;color:#1266ad;font-weight:700;line-height:1.65}.detail-body{padding-top:10px}.pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.pair>*{min-width:0}[id]{scroll-margin-top:20px}.links{display:flex;flex-wrap:wrap;gap:8px 20px}.back{position:fixed;right:18px;bottom:18px;background:#155f77;color:#fff;border-radius:24px;padding:8px 15px;box-shadow:0 2px 8px #10203020}h1,h2,h3,summary{overflow-wrap:anywhere}.flow-label{font-size:19px;font-weight:600;color:#235c73}.status{font-size:13px;background:#eef3f8;border-radius:4px;padding:2px 7px;white-space:nowrap}@media(max-width:900px){.pair{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}main{padding:18px}}@media(max-width:760px){main{padding:12px}header,section,footer{padding:18px}h1{font-size:28px}h2{font-size:24px}.lead{font-size:17px}table{min-width:650px}.metrics{gap:8px}.metric{padding:12px}.metric strong{font-size:22px}}@media print{body{background:white}main{max-width:none;padding:0}section{break-before:page}img{break-inside:avoid}nav,.back{display:none}.table-scroll{overflow:visible}}'''
sections=[]
sections.append(f'''<section id="scope"><h2>1. 先确定：在比较哪个层级的模块？</h2>
<p>“对外接口”始终相对所画的模块而言。Gemmini 本次物理设计的顶层是 <code>MeshWithDelays</code>；openTPU 的 MXU、VPU、TMEM、ACT_RAM，以及 llaccel 的 GEMM、VECTOR 都是各自核心内部的逻辑模块。内部模块没有与黑箱示意框重合的固定物理引脚边界。</p>
{table(['对象','当前分析范围','与其他对象的关系'],[
 ['Gemmini 4×4','MeshWithDelays：4×4 INT8 阵列及数据对齐、控制和标签逻辑','更接近 openTPU 的阵列核心层级；不是完整 Gemmini 系统'],
 ['openTPU MXU','命令保存、取数／FIFO、整数乘加阵列、结果 FIFO、FP32 后处理','本次黑箱范围比阵列本身更大，不能直接用端口 bit 数判优劣'],
 ['openTPU VPU','FP32 向量运算、复合函数与归约','经 TMEM 读写，与 MXU 没有一条取代 TMEM 的专用结果直连总线'],
 ['openTPU TMEM','共享 SRAM、读写选择、数据寄存、保持和旁路逻辑','服务 MXU、VPU、DMA、QUANT、COLL 等多个访问方'],
 ['openTPU ACT_RAM','量化激活和尺度记录的专用输入缓冲','由量化器写入，主要供 MXU 读取'],
 ['openTPU QUANT / SEQUENCER / DMA','本报告解释它们在数据流中的职责','未为这些模块新增完整逐端口、逐路径布线统计'],
 ['llaccel GEMM / VECTOR','矩阵与向量引擎；共享 SRAM crossbar','功能上可对应 MXU / VPU，但算术格式、接口组织和追踪端点不同'],
 ['llaccel SRAM crossbar','按 bank 仲裁、地址分发与数据选路','仅是连接逻辑，不能直接等同于包含 SRAM 宏的 TMEM'],
 ['llaccel SRAM bank 存储体','位于 llaccel_core 之外','当前 ODB 只到 bank 引脚，不包含 SRAM 宏的位置及其内部金属']])}
<div class="note">Gemmini 使用 ASAP7，openTPU small 与 llaccel core 使用 Nangate45；工艺与追踪范围都需要先对齐。本报告对比接口组织、连接范围及各组内部的层分布，不用绝对线长或同名金属层直接比较性能。按功能归组的“总线”也不自动表示某一种标准总线协议。</div>
</section>''')
sections.append(f'''<section id="system"><h2>2. openTPU：一份数据怎样在模块之间流转？</h2>
<div class="case-conclusions"><ul><li><strong>MXU 做矩阵运算，VPU 做一般 FP32 向量运算。</strong>VPU 可以处理 MXU 的结果，也可以独立执行预处理、逐元素运算和归约。</li><li><strong>TMEM 是共享工作存储。</strong>计算结果可以先保存，再由 VPU、量化器或其他单元读取；它不是仅服务 MXU 的辅助部件。</li><li><strong>ACT_RAM 保存下一次 MXU 所需的量化输入。</strong>“激活数据”与“激活函数”是不同概念。</li></ul></div>
{fig(FLOW,'典型数据流示意，框的位置不是实际 placement；箭头位宽为相应模块的声明接口宽度。')}
<p>例如，MXU 将 FP32 结果写入 TMEM 后，VPU 可以读取它来加偏置、残差相加、缩放或执行激活相关运算，再将结果写回；量化器也可以读取 TMEM，将数据转为 INT8 和尺度记录写入 ACT_RAM，供后续矩阵任务复用。具体经过哪些步骤由指令和任务决定。</p>
{detail('展开：VPU 的激活函数、TMEM 的绑定关系，以及 A/B 命名', '''<p>VPU 的基本操作包含加、减、乘、最大／最小、复制，以及 EXP2、RECIP、RSQRT、LOG2 和多种归约。ReLU 可以用 MAX(x,0) 实现；更复杂的函数可以通过运算序列和近似组合，不能把它们都解释为一个独立的“激活函数硬块”。本报告未通过整模型执行来证明某个具体网络一定使用了某组指令。</p><p>VPU 与 TMEM 的数据交换关系很强，但不是硬宏层面的物理绑定，也不意味着 TMEM 专属于 VPU。MXU 的 A/B 是共享存储读取通道名，VPU 的 A/B 是两个操作数接口名，Gemmini 的 A/B 是矩阵输入名；三处命名不能直接一一对应。</p>''')}
</section>''')
sections.append(f'''<section id="gemmini"><h2>3. Gemmini 4×4：阵列黑箱需要哪些接口？</h2>
<p class="lead">4×4 说的是计算阵列规模；32 bit、128 bit 说的是一拍接口能承载多少位数据。</p>
{fig(H/'gemmini-blackbox/01-gemmini-blackbox.png','原始 RTL 与物理边界引脚逐位核对：124 bit 输入、233 bit 输出，共 357 bit，不含电源地。图中是设计接口，不是芯片封装焊盘。')}
{table(['容易混淆的数字','这里的含义'],[
 ['A / B / D 各 32 bit','每路为 4 个 8 bit 数。4×4 矩阵不是一次由这 32 bit 全部传完；数据按行／节拍进入阵列。'],
 ['D 输入','预装初值／累加项，可以把运算意图理解为 C=A×B+D；不是又增加一次矩阵乘法。实际装载和传播由控制方式决定。'],
 ['结果 128 bit','一组 4 个 32 bit 结果。输入 8 bit 与结果 32 bit 使用不同位宽，以容纳乘加结果。'],
 ['结果行数＋任务标签 11 bit','3 bit 行数信息＋8 bit 标签。标签用于把结果与请求对应，不是计算数据。8 bit 可编码 256 个值，不代表 256 个任务同时执行。'],
 ['进行中的任务标签 88 bit','11 个标签槽位，各 8 bit；不是 88 个任务，也不是 88 个使能。槽位数量与流水／跟踪接口有关，不能由 4×4 的 PE 数直接推出。']])}
<p>接口通过 valid/ready 协调数据和请求输入，没有单独的全局 enable；结果端有 valid 和 last，当前接口没有 resp_ready。行数、标签、计算方式、握手与时钟复位都应与数值数据分开理解。</p>
{fig(H/'gemmini-blackbox/02-boundary-net-layers.png','左图统计各组有多少 bit 的边界连接网经过某层，跨层重复出现是正常的；右图是这些边界网在各层的实际线长。这些网只统计到第一段电气连接，未跨越后续单元继续追踪。')}
<div class="takeaway"><strong>引脚层不等于线路只走这一层：</strong>357 个信号引脚中，304 个位于 M4、53 个位于 M5；而其连接网可以经过 M2～M5。比如 A 的 32 个引脚都在 M4，其网络仍使用 M3 和部分 M2。</div>
{detail('完整接口分组与引脚层表',table(['接口功能组','相对 Gemmini 方向','bit','物理边界引脚所在层'],gemrows)+f'<p>{link(H/"gemmini-blackbox/port-bits.csv","逐 bit 引脚与连接层 CSV")} · {link(H/"gemmini-blackbox/summary.json","原始接口核对结果")}</p>')}
</section>''')
sections.append(f'''<section id="mxu"><h2>4. openTPU MXU：一个矩阵任务的取数与回写接口</h2>
<div class="case-conclusions"><ul><li>声明输入 <strong>1,529 bit</strong>、输出 <strong>643 bit</strong>，共 37 个命名端口；这是当前分层网表的逻辑宽度。</li><li>ACT_RAM 返回激活 <strong>512 bit</strong> 和尺度记录 <strong>128 bit</strong>；A 口读取权重尺度，B 口读取权重块，各有 256 bit 返回数据。</li><li>结果写回 TMEM；TMEM 数据接口声明为 4×32 bit，不代表 small 的单条 FP32 后处理通路每拍产生 4 个独立结果。</li></ul></div>
{fig(H/'opentpu-mxu-blackbox/01-mxu-blackbox.png','箭头方向均相对 u_slice/u_mxu。框图为逻辑关系，位宽为声明值；此 MXU 包含 FIFO 和 FP32 后处理，范围比 Gemmini 阵列黑箱更大。')}
<p><strong>cmd 240 bit 是一份命令记录：</strong>操作码 8 bit、标志 8 bit、七个 32 bit 字段，用来传递地址、维度、步长和运算参数。start、go、rdy、done 才是单独的任务协调信号；字段位宽不能直接当成使能数量。</p>
{fig(H/'opentpu-mxu-blackbox/02-interface-metal-layers.png','本图只统计逻辑接口电连接及其 BUF/INV 延伸，不跨 MUX、运算单元或寄存器。图中 TMEM 一行还包含地址和使能；其层占比不能代表第 8 节补全后的 SRAM 数据通路。')}
<p>在这一接口范围内，ACT 相关连接以 M6 为主，权重 B 口分散在 M3、M5 等层；命令与任务控制主要在 M2～M4。共享存储的同信号分支还可能通向 DMA、调度等单元，不能将整组长度归为 MXU 独占。</p>
<p class="small">共 2,172 个声明 bit，其中 1,773 bit 找到可靠物理对应，397 bit 未找到保留名称，时钟／复位 2 bit 单列。139 bit 状态／性能输出中，有内部仍在使用的 computing 1 bit 和 pf_level 7 bit 被定位；不能把顶层未接出的统计端口一概理解为全部没有内部线路。</p>
{detail('展开 MXU 全部 37 个命名端口：位宽、含义与物理定位',port_table('MXU'))}
</section>''')
sections.append(f'''<section id="vpu"><h2>5. VPU：两个操作数输入，一路结果写回</h2>
<p>VPU 主要通过 TMEM 取得 A/B 两路 FP32 操作数并写回结果。当前 small 为 4 条常规 lane，复合函数长通路为 1 条；声明的两路输入和结果数据都是 128 bit。</p>
{fig(H/'opentpu-tmem-vpu/01-vpu-interfaces.png','图中展示非流式逻辑接口：输入 501 bit、输出 560 bit，含状态／性能统计声明。完整模板另有 453 bit 流式接口，在本配置未启用。')}
{fig(H/'opentpu-tmem-vpu/03-vpu-function-layers.png','VPU 各接口功能的电连接层分布；A/B/结果三行仍未穿过 TMEM 选择逻辑到 SRAM。地址、请求、命令与访问许可均单独分类。')}
<div class="note"><strong>1 bit 控制也可能对应很多布线：</strong>gnt 是一位访问许可，它的缓冲／反相分发网络包含 803 条物理 net，线长合计约 139.36 mm，占这份 VPU 接口提取线长约 59.5%。这表示信号需要分发给许多接收点，不是 803 个独立控制位，也不是一条线有 139 mm 长。</div>
<p class="small">完整模板有 33 个命名端口，输入 791 bit、输出 723 bit；其中未启用流式输入 290 bit、输出 163 bit。剩下 1,061 bit 非流式声明中，618 bit 已定位、441 bit 未找到可靠保留名称、时钟复位 2 bit 单列。未定位项可能涉及未用字段、别名和优化，不能全部当成断线。</p>
{detail('展开 VPU 全部 33 个命名端口',port_table('VPU'))}
</section>''')
sections.append(f'''<section id="memory"><h2>6. TMEM 与 ACT_RAM：存什么、怎样组织、怎样访问？</h2>
{fig(MEMORY,'容量根据 small 配置与 SRAM 映射组织计算。复制存储位用于实现访问组织，不增加独立的逻辑地址容量；图示不是实际 placement。')}
{table(['观察点','ACT_RAM','TMEM'],[
 ['主要职责','保存量化后的 MXU 激活输入','保存多个单元共享的 FP32 工作数据和计算结果'],
 ['写入／访问方','量化器写入，MXU 读取；含复制写等控制','MXU、VPU、DMA、QUANT、COLL 等共享访问'],
 ['数据形式','INT8 数据＋64 bit 尺度记录（每行每块）','32 bit 字，常用于 FP32 数据'],
 ['逻辑容量','2 KiB 数据＋512 B 尺度记录＝2.5 KiB','64 KiB；物理 3 份一致副本合计 192 KiB'],
 ['SRAM 宏','4×32×128 数据宏＋2×32×64 scale 宏','12×4096×32 宏，3 份副本×4 bank'],
 ['宏外逻辑','写入流水、字节定位、行／块选择等','读写选择、流水、保持、旁路等'],
 ['能否视为一个硬宏','不能；它是包含多块硬宏的逻辑模块','不能；大 SRAM 宏只占该逻辑模块的一部分']])}
<h3>6.1 TMEM 的多端口是逻辑访问接口</h3>
{fig(H/'opentpu-tmem-vpu/02-tmem-interfaces.png','TMEM 声明 8 个读端口、4 个写端口，每端口 4 lane。端口集合并不保证全部能够同时无冲突访问，实际受 bank、复制组织和仲裁约束。')}
{table(['方向','接口序号与使用方','每个端口的声明数据／地址宽度'],[
 ['读','0 MXU；1 DMA；2 QUANT；3 VPU A；4 VPU B；5 QUANT_3；6 QUANT_2；7 COLL','数据 128 bit＋地址 128 bit；请求／使能各 4 bit'],
 ['写','0 DMA；1 MXU；2 COLL；3 VPU','数据 128 bit＋地址 128 bit；请求／使能各 4 bit，另有按访问方的写许可']])}
{detail('展开 TMEM 全部 16 个命名端口与定位状态',port_table('TMEM'))}
<h3>6.2 ACT_RAM 的读出很宽，量化写入较窄</h3>
{fig(ACTFIG,'ACT_RAM 的 19 个命名端口由原始分层 mapped.json 独立展开核对；输入 220 bit、输出 640 bit。数据写入宽度与读出宽度不相同。')}
<p>每个 64 bit 尺度记录包含一个 FP32 的 Sa 和四个 8 bit 子块偏移。ACT_RAM 本身不执行激活函数，也不替代 TMEM 保存一般 FP32 中间值。它把已量化数据留在片上，供 MXU 在后续权重计算中复用。</p>
{detail('展开 ACT_RAM 全部 19 个命名端口与当前统计范围',port_table('ACT'))}
</section>''')
sections.append(f'''<section id="placement"><h2>7. 实际布局：同一个模块为何会分散、交错？</h2>
<div class="takeaway"><strong>逻辑模块边界不等于物理区域边界。</strong>SRAM 硬宏尺寸固定，不能拆散；宏外标准单元可以分布在不同位置。跨模块的两个单元可能相邻，同一模块的两个单元也可能很远。</div>
{fig(ROOT/'outputs/completed-routing-20261018/opentpu_small/module_layout.png','总报告中的同一张真实单元布局图。细小色块是 cell，粗轮廓大块是 SRAM 等硬宏。颜色表示模块归属，不是互斥的布局围栏；图例计数不是完整模块数量。')}
{table(['实际位置核对','坐标范围 / μm','说明'],[
 ['TMEM 的 12 块 SRAM 宏','x≈5～641，y≈1065～2805','左侧大块，并不包含 TMEM 所有逻辑单元'],
 ['MXU 的 128 个写数据输出单元','x≈957～1024，y≈1239～1345','MXU 输出逻辑并非全在最右侧的主要计算区域'],
 ['TMEM 的 128 个写数据输入选择器','x≈953～1024，y≈1236～1345','与上述 MXU 输出单元交错摆放'],
 ['VPU 等大面积颜色区域','不等于该模块独占的物理边界','其中可以穿插其他模块的少量标准单元']])}
{fig(FULL/'03-tmem-data-placement.png','只显示被追踪的 TMEM 数据逻辑和 SRAM 宏，不显示 VPU 等背景。右下放大图直接展示 MXU 输出与 TMEM 选择器的单元中心位置；散点不是金属走线。')}
<p>同理，ACT_RAM 数据宏位于底部，而 MXU 激活接收单元沿一片区域展开。把“模块主体看起来靠近”当成所有端口都邻近会有误差。若要尝试优化，应重点看宏引脚与对应接收单元的位置、朝向和通道，再比较线长、时序及拥塞。</p>
{detail('Placement 类别、图间关系与推断边界', '''<p>本节总览图采用原始模块归属：ACT_RAM、COLLECTIVE、DMA、MXU、QUANTIZER、SEQUENCER、SLICE_TOP_LOGIC、TMEM、VPU；UNKNOWN 表示原归属未查清，PHYSICAL_ONLY 表示填充、阱接触等物理辅助单元。这里沿用同一张原图，不能把图例中的 cell 数解释为完整模块或 PE 数。</p><p>数据路径局部图只从真实引脚连接选出相关单元，并使用其实际坐标，没有按邻近关系猜测模块；这与总览图覆盖范围不同。示意框图的颜色用于区分功能组，金属层图另有独立的层颜色图例，不能跨图仅凭颜色判断对象相同。</p><p>当前结果能证明接口单元彼此邻近、SRAM 宏较远。它不能单独证明“布局工具为了靠近 MXU，主动牺牲了 TMEM 内部距离”。确认布局选择的原因，还需要对应流程约束、拥塞和时序证据。</p>''')}
</section>''')
sections.append(f'''<section id="routing"><h2>8. 金属层分布：先区分接口段，再看完整数据通路</h2>
{fig(SCOPE,'完整通路沿数据方向穿过 TMEM 的选择器和寄存器。SRAM 宏连接段包括单输入 BUF/INV 延伸，但不包含宏内部存储阵列的金属。')}
<p>“MXU 输出数据接口使用 M2/M3”在当前逻辑接口范围内是正确的；“MXU 到 TMEM SRAM 的整个访问通路主要走低层”则不成立。VPU↔TMEM 也有同样的范围差别。以下补全统计沿真实数据引脚穿过 TMEM 组合逻辑和寄存器，追到 SRAM 宏引脚。</p>
{fig(OUT/'02-interface-vs-complete.png','五个功能方向的范围对照；所有百分比按实际线长计算。接口网与完整路径有涵盖关系，不能相加。')}
{table(['数据方向','接口连接：M4 及以上','补全至 SRAM：M4 及以上'],summaryrows)}
{fig(OUT/'01-complete-data-layers.png','前五行是补全后的 TMEM 数据路径，后两行是 ACT_RAM 宏到 MXU 的数据／尺度电连接；各行独立归一到 100%，共享网络可能在不同行重复出现。')}
<p><strong>补全覆盖：</strong>MXU、VPU 写数据均追到 12 块 TMEM SRAM 的 384 个写数据引脚；MXU 旧值读取、VPU A、VPU B 各追到对应副本的 4 块 SRAM，共 128 个读数据引脚。MXU 当前实际保留的读接口为 64 bit，VPU A/B 各为 128 bit，均已找到从 SRAM 到达的路径。</p>
<h3>8.1 为什么接口看起来全在低层，完整通路却不同？</h3>
{fig(FULL/'02-path-length-breakdown.png','以 MXU 为例，短接口仅占完整写路径线长的 0.17%、读路径的 0.83%；长线主要在 SRAM 宏连接段。这里的 mm 为所有相关 net 的长度之和，不是一条信号的端到端距离。')}
<p>写入的 TMEM SRAM 宏连接段以 M5＋M6 为主，合计约 60.26%；读出宏连接段以 M5 为主，约 59.94%。ACT_RAM 激活数据电连接中，M6 约占 44.07%、M8 约占 15.67%，M2＋M3 仅约 5.80%。这些结果与宏引脚到分散标准单元之间存在长距离连接相符。</p>
<h3>8.2 “跨模块越多，层越高”为什么不总成立？</h3>
{table(['连接例子','逻辑关系','物理关系与本次结果'],[
 ['MXU 输出 → TMEM 输入选择器','跨越逻辑模块边界','单元紧邻，数据接口网全部使用 M2/M3'],
 ['TMEM 后续逻辑 → TMEM SRAM','位于同一个逻辑模块内部','相隔较远，宏连接段大量使用 M5/M6'],
 ['ACT_RAM SRAM → MXU 接收逻辑','跨逻辑模块，同时有较长物理跨度','大部分数据线长在 M4 及以上']])}
<p>在没有强制独立物理区域的软模块设计中，判断金属层时应优先看实际跨度、拥塞、扇出和时序需求。高层与低层的具体用途还受技术库、线宽、方向和路由约束影响；本报告给出实际层分布，不从最终布线反推唯一的放置或选层原因。</p>
{detail('完整通路线长、每 net 均值与范围',table(['数据通路','去重物理 net 数','线长合计 / mm','平均每 net / μm','每 net 最小～最大 / μm','主要金属层'],fullrows)+'''<p>均值、最小和最大针对单条物理 net，不是每一位数据从计算单元到 SRAM 的总传播距离。路径会穿过逻辑门和寄存器，不能把所有 net 按一条串行路径理解。</p>''')}
{detail('接口功能分组的原有统计表（与完整路径不能混加）',table(['模块','接口功能','物理 net 数','线长合计 / mm','主要金属层'],funrows)+'''<p>这张表只对应第 4、5 节的接口电连接提取。完整路径表针对数据负载；地址、使能、访问许可等仍保持接口范围，不冒充已经追到所有 SRAM 引脚的完整控制通路。</p>''')}
</section>''')
# Integrate llaccel content into this report, rebasing assets and unique anchors.
lf=BeautifulSoup(''.join(load(LL/'sections.json')['sections']),'html.parser')
for node in lf.select('[id]'):node['id']='ll-'+node['id']
for node in lf.select('[href],[src]'):
    for attr in ('href','src'):
        value=node.get(attr)
        if not value:continue
        u=urlsplit(value)
        if u.scheme or u.netloc:continue
        if not u.path:
            if u.fragment:node[attr]='#ll-'+u.fragment
            continue
        target=(LL/unquote(u.path)).resolve()
        node[attr]=rel(target)+('#ll-'+u.fragment if u.fragment else '')
lparts={node['id']:node for node in lf.select('section')}
def ll_inner(key):
    node=BeautifulSoup(str(lparts['ll-'+key]),'html.parser').section
    node.find('h2').decompose()
    for im in node.select('img'):FIGURES.append(ROOT/im['src'])
    return node.decode_contents()
overview=BeautifulSoup(str(lparts['ll-scope']),'html.parser').section
overview.h2.decompose();overview.figure.decompose()
sections.append(f'''<section id="llaccel-system"><h2>9. llaccel：计算引擎如何共用存储？</h2>
<p class="lead">GEMM 与 VECTOR 的数据读写经共享 crossbar 到达 bank；本次物理分析在核心 bank 引脚处结束。</p>
{fig(LL/'07-llaccel-system.svg','系统模块关系：实线表示数据访问，紫色虚线表示任务控制。DRAM 仲裁器同时服务取指、DMA 和 ATTENTION；当前详细数据路径统计覆盖 GEMM、VECTOR 的 SRAM 访问。')}
{overview.decode_contents()}
{fig(LL/'10-llaccel-memory-organization.svg','16 个 bank 的逻辑组织，以及请求地址如何拆成 bank 行地址和起始 bank 编号；外部存储框不表示实际宏位置。')}
</section>''')
portsbody=BeautifulSoup(ll_inner('ports'),'html.parser')
summary=portsbody.find('div',class_='table-scroll')
summary.replace_with(BeautifulSoup(detail('展开接口功能汇总表（示意图位宽的完整对照）',str(summary)),'html.parser'))
cards=portsbody.find('div',class_='pair')
cards.insert_after(BeautifulSoup(fig(LL/'08-llaccel-gemm-interface.svg','GEMM 的 RTL 黑箱接口：输入 3080 bit、输出 673 bit。权重读口为 2048 bit，A／参数读口为 512 bit；结果 512 bit 容器中当前最多使用 256 bit 有效数据。')+fig(LL/'09-llaccel-vector-interface.svg','VECTOR 的 RTL 黑箱接口：输入 1576 bit、输出 670 bit。两个操作数口各声明 512 bit，当前读拆分器使用低 256 bit；时钟复位、握手、完成状态和统计脉冲分别标明。'),'html.parser'))
sections.append('<section id="llaccel-ports"><h2>10. llaccel GEMM / VECTOR：黑箱接口示意</h2>'+str(portsbody)+'</section>')
sections.append('<section id="llaccel-routing"><h2>11. llaccel：数据状态到 bank 边界的金属分布</h2>'+ll_inner('paths')+'<h3>11.1 核心对外 bank 引脚：按功能区分</h3>'+ll_inner('bank')+'</section>')
sections.append('<section id="llaccel-placement"><h2>12. llaccel：访存通路中的单元实际在哪里？</h2>'+ll_inner('placement')+'</section>')
CSS+=' .card{border:1px solid #dce4ee;border-radius:9px;padding:18px}.card h3{margin:0 0 12px}.muted{color:#5b6d80;font-size:14px}.caution{background:#fff8e9}'

sections.append(f'''<section id="method"><h2>13. 怎样读这些统计，哪些内容已经确认？</h2>
{table(['需要分开的量','解释'],[
 ['命名端口数 / 声明 bit 数','一个命名端口可以是多位向量；宽度是接口声明，不等于有同样数量的独立物理网。'],
 ['逻辑 bit / 物理 net','一个 bit 经缓冲分发可对应多条 net；常量、别名、优化也可使声明位没有独立保留线路。'],
 ['引脚所在层 / 沿途金属层','引脚形状可以在某一层，连接网通过过孔进入其他层；两类统计不可混为一谈。'],
 ['单条 net / 功能通路的线长合计','通路可能包含多级逻辑、寄存器、分支及多份存储副本；总长不是一条线的距离，也不是时延。'],
 ['共享线路 / 独占线路','一条宏数据网可以服务多个访问方；同一物理 net 在一个统计组内只计一次，不同视图或访问方之间仍可能重合。']])}
<p>在 openTPU MXU 完整写路径中，可被其他写端口的数据到达的共享 net 占线长约 96.78%；完整读路径中，也能通向其他读端口的 net 占约 98.67%。llaccel 的 GEMM 与 VECTOR 写回也共享大量 bank 输出网络。这些结果说明长距离存储线路很大一部分是共享设施；结构可达不表示各端口同时传输。</p>
{table(['案例','当前数据追踪的起止边界','是否穿过数据寄存器','读图时的限制'],[
 ['Gemmini','顶层真实信号引脚及其电连接','不作为完整计算通路继续穿过','是 MeshWithDelays 接口，不能等同完整加速器'],
 ['openTPU','逻辑数据接口 ↔ TMEM SRAM 宏引脚','在 TMEM 内按 D→Q/QN 继续','有实际 SRAM 宏；不同访问方共享整网长度'],
 ['llaccel','具名数据寄存器 D/Q ↔ core 的 bank 引脚','不越过任何寄存器','无 SRAM 存储宏；GEMM A 路径包含首级乘法前的组合逻辑']])}
<p>llaccel 的寄存器端连线并非逐位恢复出的原始模块接口线。不能用它与 openTPU 的原始接口统计直接排名，也不能把本次 16-bank 引脚示意误认为 SRAM 宏的真实摆放。</p>
{table(['分析内容','状态与边界'],[
 ['Gemmini 的接口及引脚层','357 个信号 bit 已与原始 RTL、物理边界引脚核对；沿接口网统计，不延伸为整个阵列数据通路。'],
 ['MXU / VPU / TMEM 的逻辑接口','声明、未启用配置、物理定位分别记录；未找到可靠名称的位不补猜布线。'],
 ['ACT_RAM 的逻辑接口','19 个端口、220 输入／640 输出已由原始展开网表核对；512＋128 bit 读出连接已物理定位。'],
 ['MXU↔TMEM、VPU↔TMEM 数据路径','已穿过 TMEM 数据逻辑及寄存器，补全至 SRAM 数据引脚；写旁路另存，不混入 SRAM 存储读出路径。'],
 ['地址、使能、仲裁、状态路径','已有接口连接统计；未在本报告统一补全穿过所有 TMEM 逻辑的完整路径。'],
 ['量化器 → ACT_RAM 完整写路径','职责与声明已解释；跨多个写流水级至 SRAM 的线长未在本次重新逐段补算。'],
 ['llaccel GEMM / VECTOR 接口','RTL 声明位宽及功能已核对；大量原始接口线名消失，采用具名数据状态建立可靠物理端点。'],
 ['llaccel 六组 SRAM 读写通路','已追踪具名数据状态与 bank 引脚之间的组合连接；全部所选数据寄存器均与相应 bank 边界相连。'],
 ['llaccel ATTENTION / DMA / DRAM','已在系统关系图交代用途；本次没有为其新增完整逐功能数据路径布线统计。'],
 ['布局原因与优化收益','已有实际位置和层分布；布局工具的具体取舍、改放置后的收益，需要对应约束和受控重跑验证。']])}
{detail('展开：提取方法、共享分支、过孔与校验', '''<p>接口提取从原始分层网表端口的同线别名出发，在最终布线数据中查找，并只沿库模型确认的单输入 BUF/INV 延伸；不会把 MUX 或寄存器两侧当成同一根电线。共享控制信号的分发可能延伸到模块内部。</p><p>完整 TMEM 数据路径从指定数据接口到 SRAM 写数据引脚，或从 SRAM 读数据引脚到指定接收接口，求正向和反向结构可达集合的交集。组合逻辑根据输出函数依赖追踪；MUX 只沿 A/B 数据输入，不沿 S 控制；寄存器只沿 D→Q/QN，不沿时钟、复位。不会穿过存储状态或外部计算单元的运算逻辑。</p><p>一个 net 若包含通向其他负载的实际电气分支，其全部布线长度仍计入，不能在没有路径几何拆分依据时只截取某条逻辑支路。每组内部用最终 net ID 去重；不同接口、访问方和完整路径视图的长度不可直接相加。</p><p>长度为金属中心线在平面内的长度，不含过孔的垂直高度、宏内部金属和电源地。openTPU 使用 2000 DBU/μm；Gemmini 的提取按其原始工艺数据库比例换算。金属层占比按长度计算，不按信号位数计算。</p><p>通过检查：逐 net 各层线长之和等于总长；MXU 读写分段互斥且合成完整路径；MXU/VPU 指定数据接口全部接到相应 SRAM 数据引脚；无未支持的 TMEM 单元模型或多驱动引起的弧拒绝；同一案例各次提取的网络摘要一致。结构可达不等于特定周期活动、满足全部选择条件的时序仿真或跨综合阶段的形式等价证明。</p>''')}
</section>''')

downloads=[link(OUT/'complete-path-summary.csv','完整通路与层分布 CSV'),link(OUT/'interface-comparison.csv','接口／完整通路对照 CSV'),link(OUT/'report-data.json','汇总数据 JSON'),link(OUT/'manifest.json','数据来源与哈希'),link(OUT/'build_module_report.py','报告生成脚本'),link(FULL/'physical-nets.csv','完整追踪逐 net 明细'),link(FULL/'interface-endpoint-placement.json','接口单元实际坐标'),link(FULL/'fullpath-physical.json.gz','路径、引脚与逻辑弧审计数据')]
sources=[link(H/'opentpu-tmem-vpu/otpu_slice.sv','openTPU 父层连接'),link(H/'opentpu-mxu-blackbox/otpu_mxu.sv','MXU RTL'),link(H/'opentpu-tmem-vpu/otpu_vpu.sv','VPU RTL'),link(H/'opentpu-tmem-vpu/otpu_tmem.sv','TMEM RTL'),link(OUT/'sources/otpu_actram.sv','ACT_RAM RTL 快照'),link(H/'opentpu-tmem-vpu/config.mk','small 配置'),link(OUT/'act-interface.json','ACT_RAM 原始展开端口')]
sections.append(f'''<section id="evidence"><h2>14. 数据与复核材料</h2><p>正文保留所有关键图；完整端口表、较长统计表和方法说明在各节折叠区。三个案例在本页统一阅读，原始分析数据按案例保存。</p><h3>Gemmini / openTPU</h3><div class="links">{' '.join(downloads)}</div>{detail('Gemmini / openTPU：RTL、配置与原始接口记录','<div class="links">'+' '.join(sources)+'</div><p>ACT_RAM 源码快照取自已核对提交 f237dab2f196855a59a083b1454786df8f01291f；其实际展开端口另从该案例原始 mapped.json 提取。源码中历史 FPGA 布局／时序注释不作为当前 ASIC 路由原因的证据。</p><div class="links">'+link(H/'gemmini-blackbox/port-bits.csv','Gemmini 逐 bit 接口')+link(H/'opentpu-mxu-blackbox/port-bits.csv','MXU 逐 bit 定位')+link(H/'opentpu-tmem-vpu/port-bits.csv','VPU/TMEM 逐 bit 定位')+'</div>')}<h3>llaccel</h3>{ll_inner('evidence')}</section>''')

header=f'''<header id="top"><div class="eyebrow">GEMMINI 4×4 · OPENTPU SMALL · LLACCEL CORE · 2026-10-20</div><h1>模块、对外接口与金属互连</h1><p class="lead">从“计算什么、与谁交换数据”，读到“单元实际在哪里、每段连接走哪些金属层”。</p><p>{link(ROOT/'总报告.html','总报告')} · {link(ROOT/'线长报告.html','线长报告')} · 本页统一梳理 Gemmini、openTPU 与 llaccel 的模块接口及布线，不替代全项目统计。</p><div class="metrics"><div class="metric"><strong>357 bit</strong><span>Gemmini 已核对信号接口</span></div><div class="metric"><strong>512＋128 bit</strong><span>ACT_RAM 返回激活与尺度</span></div><div class="metric"><strong>16 个 bank</strong><span>llaccel 共享 SRAM 的接口组织</span></div><div class="metric"><strong>5＋6 组通路</strong><span>openTPU TMEM 与 llaccel 数据追踪</span></div></div><div class="takeaway"><strong>先看四点：</strong>比较前先对齐模块范围；软模块的标准单元可以交错摆放；寄存器端连线也可能使用高层金属；openTPU 可追到 SRAM 宏，当前 llaccel_core 则止于 bank 引脚。</div><nav>{''.join(f'<a href="#{i}">{t}</a>' for i,t in [('scope','分析范围'),('system','openTPU 数据流'),('gemmini','Gemmini'),('mxu','MXU'),('vpu','VPU'),('memory','TMEM / ACT_RAM'),('placement','openTPU 布局'),('routing','openTPU 布线'),('llaccel-system','llaccel 系统'),('llaccel-ports','GEMM / VECTOR 接口'),('llaccel-routing','llaccel 布线'),('llaccel-placement','llaccel 布局'),('method','统一统计口径'),('evidence','数据复核')])}</nav><p class="small">阅读方式：图直接展示、关键结论和关键表保留在正文；完整端口表与复核材料放折叠区。箭头标注的是当前实例的接口位宽，示意框图不表示实际物理边界。</p></header>'''
JS='''<script>(()=>{function reveal(){if(!location.hash)return;let e=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(!e)return;for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;requestAnimationFrame(()=>e.scrollIntoView({block:'start'}));}window.addEventListener('hashchange',reveal);window.addEventListener('DOMContentLoaded',reveal);})();</script>'''
doc='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>模块、对外接口与金属互连｜Gemmini · openTPU · llaccel</title><style>'+CSS+'</style></head><body><main>'+header+''.join(sections)+'<footer><p>本报告依据当前已完成案例的原始接口、最终路由网络、真实单元坐标及数据路径追踪整理。统计范围随表与图明确标注；跨视图的共享线路不重复解释为新增线路。</p></footer></main><a class="back" href="#top">返回目录 ↑</a>'+JS+'</body></html>'
REPORT.write_text(doc,encoding='utf8')

with (OUT/'complete-path-summary.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['path','group','physical_nets','total_um','mean_net_um','min_net_um','max_net_um','M4_plus_percent']+[l+'_um' for l in LAYERS])
    for label,k in zip(labels,keys):
        st=S[k];w.writerow([label,k,st['nets'],st['length_um'],st['mean_net_um'],st['min_net_um'],st['max_net_um'],st['high_pct']]+[st['layers_um'][l] for l in LAYERS])
with (OUT/'interface-comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['path','interface_M4_plus_percent','fullpath_M4_plus_percent','fullpath_group'])
    for label,k,ifs in PAIRS:w.writerow([label,ifs['high_pct'],S[k]['high_pct'],k])
reportdata=dict(fullpaths={k:S[k] for k in keys},interface_comparison=[dict(path=lab,group=k,interface=ifs,fullpath=S[k]) for lab,k,ifs in PAIRS],
                logical_bits={'Gemmini':GEM['logical_bits'],'MXU':{'input':1529,'output':643},'VPU_all':{'input':791,'output':723},'VPU_nonstream':{'input':501,'output':560},'TMEM':{'input':2151,'output':1056},'ACT_RAM':{'input':220,'output':640}},
                scope='Specified data paths only. Address/control complete-path traversal not claimed. Shared nets may overlap between paths; net centerline planar length, no macro interior or via vertical length.')
reportdata['llaccel']=dict(results=LD['results'],coverage=LD['coverage'],overlap=LD['overlap'],declared_ports=LP,method=LD['method'],odb_sha256=LD['source']['extraction']['odb_sha256'])
(OUT/'report-data.json').write_text(json.dumps(reportdata,ensure_ascii=False,indent=2),encoding='utf8')
inputs=[H/'gemmini-blackbox/summary.json',H/'opentpu-mxu-blackbox/summary.json',H/'opentpu-tmem-vpu/summary.json',H/'mxu-interface-physical.json.gz',H/'tmem-vpu-interface-physical.json.gz',FULL/'fullpath-physical.json.gz',FULL/'interface-endpoint-placement.json',OUT/'act-interface.json',OUT/'sources/otpu_actram.sv',H/'opentpu-tmem-vpu/config.mk']
inputs.extend([LL/'summary.json',LL/'declared_ports.json',LL/'endpoint_evidence.json',LL/'liberty_models.json',LL/'sram_xbar.sv'])
manifest=dict(report=rel(REPORT),created='2026-10-20',source_net_sha256=FD['net_sha256'],source_mapped_sha256=FD['mapped_sha256'],liberty_sha256=FD['liberty_sha256'],gemmini_odb_sha256=GEM['odb_sha256'],llaccel_odb_sha256=LD['source']['extraction']['odb_sha256'],
              inputs=[dict(path=rel(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in inputs],figures=[rel(p) for p in FIGURES],
              checks={'same_opentpu_final_net_dataset':True,'layer_sums_match_previous_audit':True,'specified_data_ports_reach_sram':True,'logical_width_checks':True,'llaccel_selected_data_states_reach_bank':all(c['state_cells']==c['state_cells_on_path'] for c in LD['coverage'].values())})
(OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(report=str(REPORT),sections=len(sections),figures=len(FIGURES),bytes=REPORT.stat().st_size,validation='passed'),ensure_ascii=False))
