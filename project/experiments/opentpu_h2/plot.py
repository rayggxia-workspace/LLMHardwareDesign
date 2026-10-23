"""Static research figure from verified selected evidence; explicit pending DRC scope."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
source = HERE / 'results/selected-evidence.json'
data = json.loads(source.read_text(encoding='utf-8'))
assert data['freeze']['passed'] and data['proofs']['full-hierarchy-quality.json']['passed']
plt.rcParams.update({'font.family': 'Microsoft YaHei', 'axes.unicode_minus': False,
                     'svg.fonttype': 'none', 'svg.hashsalt': hashlib.sha256(source.read_bytes()).hexdigest(), 'font.size': 11})
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.5), gridspec_kw={'width_ratios': [1.15, 1]})
fig.suptitle('openTPU H2 首个同功能切片：冻结库存，只重连既有接入点', fontsize=16, y=.99)
colors = ['#536c7c', '#12a18d']
costs = [data['costs'][name] for name in ['h1', 'h2']]
ax = axes[0]
for i, cost in enumerate(costs):
    fixed = cost['fixed']['wire_um']/1e6
    upper = cost['custom']['wire_um']/1e6
    ax.barh(i, fixed, color=colors[0], label='冻结低层／时钟' if i==0 else None)
    ax.barh(i, upper, left=fixed, color=colors[1], label='M8–M10 可改信号' if i==0 else None)
    ax.text(fixed/2, i, f'{fixed:.4f}', ha='center', va='center', color='white')
    ax.text(fixed+upper+.04, i, f'{fixed+upper:.6f}', va='center', fontsize=10)
ax.set(yticks=[0, 1], yticklabels=['H1 拆分基线', 'H2 回装'], xlabel='父层普通信号中心线（百万 µm）', xlim=(0, 3.95))
ax.invert_yaxis()
ax.legend(loc='upper left', bbox_to_anchor=(0, -.22), frameon=False, ncol=2, fontsize=10)
ax.set_title('原父层约 92.50% 线长已经预埋', fontsize=12)
ax = axes[1]
for i, cost in enumerate(costs):
    values = [cost['custom']['by_layer_um'][str(layer)]/1000 for layer in [8,9,10]]
    ax.bar([v+i*.34-.17 for v in range(3)], values, width=.32, color=colors[i], label=['H1', 'H2'][i])
    for x, value in enumerate(values):
        ax.text(x+i*.34-.17, value+2.4, f'{value:.2f}', ha='center', fontsize=9)
ax.set(xticks=range(3), xticklabels=['M8', 'M9', 'M10'], ylabel='可改父层线长（千 µm）', ylim=(0, 230))
ax.set_title('仅改变 M8–M10、V8/V9', fontsize=12)
ax.legend(frameon=False)
for ax in axes:
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis='x' if ax is axes[0] else 'y', alpha=.15)
    ax.set_axisbelow(True)
fig.text(.02, .015, '9,609 个有源支持、2,006 个 V7 接入固定；回装 RC／PG／电气／完整 STA 通过。独立完整父层 DRC 待定；尚无多计算图复用结论。', fontsize=10)
fig.subplots_adjust(left=.1, right=.98, top=.79, bottom=.26, wspace=.3)
out = REPO/'docs/experiments/assets'
out.mkdir(exist_ok=True)
files=[]
for suffix in ['png','svg']:
    path=out/('issue-31-h2-resource-wires.'+suffix)
    fig.savefig(path,dpi=170,facecolor='white',metadata={'Date':None} if suffix=='svg' else None)
    if suffix=='svg':
        path.write_bytes(b'\n'.join(line.rstrip() for line in path.read_bytes().splitlines())+b'\n')
    files.append(dict(path=path.relative_to(REPO).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
manifest=dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),outputs=files,
              generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              scope='Observed single instance and exact DEF centerlines; standalone full-parent DRC pending')
(HERE/'results/plot-manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode())
print(json.dumps(manifest,indent=2))
