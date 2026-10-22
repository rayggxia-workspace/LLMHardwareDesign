# state_ports/graph.py 独立只读审查

2026-10-22。最终审查快照 SHA-256：bafb9f56df9e17f9bbf69591d75eaea535048fa76c9067c416032f4b87accef0。版本检查修复、尚未加入 staging 字段的中间快照为 47e4569bc2a781583396bca50f359df90f9f924863e9fcf733070ae244dfa492；先前发现对应快照为 770dc45dd09b95895b9421f133c48b5147b819d367cb2d263b25622d5b45d139。三个源快照均保存在本独立目录。

审查范围：graph.py 的依赖、固定地址、状态版本、scratch 容量、资源输入校验，以及 verify_access_order 的独立防线。没有修改主树、执行模型算术或调用优化调度器。

## 当前结论

**最终 PASS：未发现尚未修复的必须改项。** 正常生成的 96 个图未发现遗漏 RAW/WAR/WAW 依赖、错误流量/MAC 公式或免费引擎 scratch。原 67 项非法配置输入全部拒绝，新增 staging 字段的 5 个非法值和 1 个不足一 beat 的容量也全部拒绝，共 73 项；7 个独立 checker 变异全部拒绝。以下保留先前漏洞、修复内容与真实复核证据；这些漏洞不等同于当时正常生成图已产生错误数据。

### 已解决 P2：读取越过最近写入版本的有效范围仍被接受

使用 q=2、keys=5、head_dim=4、key_tile=4、max_query_tile=4；K 槽容量为 64 B，尾 tile 的 t1.loadK 只写 16 B。把 t1.qk.rK 的访问字节改为 64 B，仍处于 K 的物理 slot 内；verify_access_order 返回空错误列表。把 t1.loadK 缩为 4 B、保持正常 16 B 读取，也被接受。

原检查仅判断 read bytes ≤ slot bytes，并把每一次部分 write 当作新 whole-buffer version。最终版新增 version_bytes，验证 read bytes 不超过最近 write bytes；两个上述负例均被 read exceeds initialized version 拒绝。此修复适用于当前所有访问从 object slot 起点开始的合同；将来允许子区间写入时需跟踪区间/版本。

### 已解决 P2：非法 bank 与 direction 可自洽绕过独立校验

将 Q slot 的 bank 及所有 Q access.bank 一起改为 2，校验器仅循环 bank 0/1，且 object/access 一致，最终返回空错误列表。将 entry.Q 的 direction 改成 X，校验器走非 R 分支，把它当 W，也返回空错误列表。

最终版先校验 slot bank ∈ {0,1}、slot 地址/尺寸合法、direction ∈ {R,W}；两个负例均被拒绝。生成入口也已拒绝不合法 placement。这里修复的是独立图结果校验对派生记录的盲目信任。

## 已修复并实际复核的先前问题

- 吞吐、带宽、tile、workload 和容量原先允许负值/NaN 或 bool 等，负 duration 会被 max(1,duration) 压成 1 slot。当前入口已要求严格正整数，setup 要求非负整数；非法 disabled link 和 bool placement 也拒绝。67 个变异输入实际全部拒绝。
- bank_bytes_per_cycle 已重命名为 bank_port_bytes_per_cycle，消除了 2RW 每端口分别获得该吞吐却被误认为 bank 总带宽的歧义。不同端口合同属于不同硬件敏感性条件，不能混入同资源划分收益。
- 当前 checker 拒绝错误 access bank、错误 offset、越物理 slot、越最近版本有效范围、非法 slot bank 和非法 direction，7 个变异实际全部拒绝。

## 独立正常图检查

脚本 audit_graph.py 读取主树源字节，在本独立目录冻结 SHA 命名快照后加载；不复用生产调度器。96 个组合 = 3 种端口模式 × 8 个状态放置 × 4 个 workload，包含单 tile、多 tile、非整尾块与不同 q/d。

最终实际完成 27,073 项断言（原 26,977 项，加每个正常图的 staging inventory 检查共 96 项）：

- 2,208 条 RAW、1,248 条 WAR、1,248 条 WAW 关系从独立对象写/读序列推导，再检查其是否已被任务 DAG 的传递闭包覆盖。
- 每个正常读均落在最近 write 有效范围内；固定 bank 地址不重叠且符合容量。
- M/V 每个 operation 的全部输入+输出总字节不超过 scratch_reserved_bytes；下一 operation 的读取在上一 operation 完成所有写回之后，避免 scratch 提前复用。
- 独立重算 2*q*n*d MAC；若 t=ceil(n/key_tile)，D/M/V 总访问字节分别为 4*(2*q*d+2*n*d)、4*(2*t*q*d+2*n*d+2*q*n)、4*(3*q*d+3*q+2*q*n+t*(3*q*d+6*q))。
- 串行拓扑合法 witness 被生产版本检查接受；这只证明正常实例存在一种可行执行次序，不是优化 makespan。
- 每个正常图返回 M/V/D 各 64 B staging，共 192 B 固定辅助资源。它不随 placement、port mode 或 workload 改变；入口要求 staging 容量为严格正整数且至少可容纳声明的一 link beat。

执行命令：D:/APP/Python/python.exe -B D:/Projects/Codex/state-port-study-20261022/interface-audit/audit_graph.py

最终机器结果：graph-audit-results.json，SHA-256 22d2e4a1ea7d5534964af8bfb2ecd7cf9a99ced3f8373cac2ec07d9ef72fe375。中间结果保留为 graph-audit-pre-staging-results.json，SHA-256 7af9ea2a0e5bb8f60e5b98bb0149701c70c5f105e95027789e6e754449c26778。

先前漏洞证据：graph-audit-initial-results.json，SHA-256 1d013ae597037446a09dd759e4520801a32ae66a794f029c540782d305af1079。为保留可复现来源，已用独立脚本的 --source 参数对归档的旧源快照重跑，重新得到相同 4 个漏检与相同结果 SHA；没有回滚主树。该轮脚本保留为 audit_graph_pre_staging.py，最终脚本为 audit_graph.py。

## README 合同审查

当前 README 对 FP32、非全模型、未标定服务周期、同资源 placement 配对、静态禁边单调性、四种启发式不是全局最优、不同端口合同不是等面积替代等边界描述准确。bank_port_bytes_per_cycle 明确为每端口吞吐，2RW 可以两端口并行，endpoint 仍限制一个 burst，表述与代码一致。

文档建议均已解决并读回核对：README 现在将每 endpoint 64 B staging 写为模型假设，明确 192 B 总计、无 RTL FIFO 深度充分性证明；graph 已返回对应固定 inventory。原“implementable schedule class”已收紧为“restricted abstract schedule class”。当前图仍不模拟 pipeline FIFO 占用，本次审查不反推 RTL 可实现性。

## 解释边界

verify_access_order 不使用 DAG deps，因此能够发现调度时间违反 RAW/WAR/WAW，是有价值的第二道防线。但它仍信任 accesses 的 object 和生成顺序作为预期版本；它不能独立证明 QK 选对语义操作数/tile，不能验证在线 softmax FP32 算术。

whole-object address lock、完整 burst 原子资源占用、同引擎事务串行至写回、静态保留最大 scratch，使这里成为明确受限且保守的 task-level 服务图。没有逐 beat FIFO 占用、RF 内部端口、阵列供数波形或中途 backpressure 模型。通过本审查不表示真实 SRAM/RTL 已证明无死锁，也不代表物理时钟、面积、功耗或最优划分。
