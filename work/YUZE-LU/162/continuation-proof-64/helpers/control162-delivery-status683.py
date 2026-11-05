from pathlib import Path
import json,hashlib,subprocess,shlex,time,datetime
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control';out=r/'work/YUZE-LU/162/publication-runtime-680-682';assert not out.exists()
q="from pathlib import Path;import json,base64; p=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/r256-current-pool-cpu-observation-682/receipt.json');d=json.loads(p.read_text());assert d['passed'] and d['actual_processes']==80;print(base64.b64encode(p.read_bytes()).decode())"
import base64
raw=base64.b64decode(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=20));out.mkdir();(out/'cpu-observation-682.json').write_bytes(raw)
files=['cpu-observation-682.json'];items={'publication-679.json':h/'control162-git-data-publish-679/receipt.json','issue-680-verified.json':h/'control162-online680-issue-verified.json','pr-680-request.json':h/'control162-online680-pr-request.json','pr-680-verified.json':h/'control162-online680-pr-verified.json','helper683.py':Path(__file__),'helper682.py':h/'control162-utilization682.py','helper681.py':h/'control162-verify681.py'}
snap=sorted((h/'control162-watch662').glob('*.json'))[-1];items['selected-runtime-snapshot.json']=snap
for name,p in items.items():(out/name).write_bytes(p.read_bytes());files.append(name)
index=dict(time=time.time(),whole_system_qualified=False,scope='Exact publication/readbacks and2second OS CPU observation; selected runtime snapshot only. No physical acceptance inferred.',rows=[dict(relative=n,bytes=(out/n).stat().st_size,sha256=hashlib.sha256((out/n).read_bytes()).hexdigest())for n in files]);(out/'index.json').write_bytes((json.dumps(index,indent=2)+'\n').encode())
p=r/'.gitattributes';p.write_bytes(p.read_bytes()+b'\nwork/YUZE-LU/162/publication-runtime-680-682/** -text\n')
now=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
s=f'''# 当前交付入口：23类单块合格，当前453组合仍待最终物理验收

更新：{now}。单块以[current363规范索引](../work/YUZE-LU/162/block-delivery-r256-current363/index.json)的23类/138个最终文件为准，保留S1350内部驱动和R256；本地接收/版图证据沿各叶的源索引查询。当前453仅重接267个未使用Link8输入，其345个物理宿主、23类固定宏与有效接线保持，见[453状态归属绑定](../work/YUZE-LU/162/state-ownership-candidate453-binding.json)。各块的合格结果不授予整套组合资格。

当前完整路由和所有后继验收进度以[Checkpoint63](../work/YUZE-LU/162/continuation-checkpoint-63.md)与[CONTROL_V1](CONTROL_V1.md)为准；当前仍没有完整零冲突M11/M12路由、最终几何/PG、三档分布RC下300MHz和联合交付通过。[实际发布/在线读回与CPU采样](../work/YUZE-LU/162/publication-runtime-680-682/index.json)绑定提交22b1e110ca9e82147df64d32ea37929ccc18ade0的远程发布，以及Issue680/PR681逐字读回。682只在2秒采样中观察80个指定本人路由进程，共79.56核，不代表所有576核的长期利用率。八父节点、c64 4×16/c96 6×16独立任务动态补位继续，不合并。

以下保留历史阶段记录；其旧图、旧复位版本、旧轨迹或排队状态不得替代上述当前入口。

'''
p=r/'docs/CONTROL_V1_BLOCK_DELIVERY.md';p.write_bytes((s+p.read_text(encoding='utf-8')).encode())
s=f'''# 当前真实程序证据：453接线、473事件与480独立审计

更新：{now}。当前采用453图/345物理实例/23类完整最终PG单元，独立源绑定见[472实际审计](../work/YUZE-LU/162/continuation-proof-54/r256-padding-final-function-audit-472/receipt.json)。[当前13文件交付索引](../work/YUZE-LU/162/program-event-delivery-padding453-current536/index.json)绑定473实际三初态事件执行与480独立重放/六项篡改拒绝：每次8程序、680884检查、217396周期、CPU张量搬运0，9318外部握手/主机程序事件、18调用、14案例。事件标记范围与原编译资产绑定限制见该索引及[Checkpoint57](../work/YUZE-LU/162/continuation-checkpoint-57.md)。不是逐周期波形，也不是八个完整模型的端到端执行。

下表八程序的功能及预期数值不变；其早期359/392和422链接仅保留历史，当前验收采用上述472/473/480绑定，不从旧图继承。所有状态宿主见[当前453归属绑定](../work/YUZE-LU/162/state-ownership-candidate453-binding.json)。程序通过不替代仍在执行的M11/M12、几何/PG/三档RC/300MHz/联合物理验收；最新进度见[Checkpoint63](../work/YUZE-LU/162/continuation-checkpoint-63.md)。

'''
assert (r/'work/YUZE-LU/162/continuation-proof-54/r256-padding-final-function-audit-472/receipt.json').is_file()
p=r/'docs/CONTROL_V1_REAL_PROGRAMS.md';p.write_bytes((s+p.read_text(encoding='utf-8')).encode());print(json.dumps(dict(files=len(files),physical_system_passed=False)))
