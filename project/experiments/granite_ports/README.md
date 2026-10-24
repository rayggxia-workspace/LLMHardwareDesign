# Granite 有限端口、缓冲与受限宽算术

Issue76 / PR77。实际实验状态以 docs/experiments/issue-76-granite-ports.md 和 results/issue-76/index.json 为准；源码或协议本身不是实验通过证据。

先读 PROTOCOL.md、SERVICE.md、MICRO.md、AUDIT.md。固定 Issue74 两层 R16 evaluation72 的原整数函数，只有 merge 窗口128/256/1536、M/V驻留和无功能标签变化。所有真实数组、pack、RTL校准、完整服务和独立接收只在本人授权CPU服务器 Slurm 运行；PC只源码、小合成和JSON/字节接收，TEMP/TMP指定D盘当前任务目录。

## 检查与恢复

先运行 python -B scripts/check_project.py；在已有NumPy环境运行 python -B -m unittest discover -s project/experiments/granite_ports -p 'test_*.py'。它们不是实际模型或硬件验收。

完整原始命令、模型revision、环境、source commit/SHA、Slurm ID及新out在 work/Liangruizhi/76；恢复必须使用索引所指的冻结phase源码，不以最新HEAD替换旧绑定，所有输出拒覆盖。

- tool_probe.py：已有EDA/CPU环境探测，不安装软件。
- service.py pack：真实W8静态布局，保留原代码和scale，只有一个硬件部署副本。
- run_server.py：S8/byte微程序、因果RTL核心重放和单ROM接口校准。完整wide/address FSM与frame实现仍软件。
- receive_micro76.py：独立live-store、原码、边界/全控制域、实际ROM请求及费用资格；旧少key/语义拒绝不可用于正式服务。
- diagnose_rq_shifts.py：只读旧原结果的完整移位区间，不改变精度或量化。
- service.py run / receive_service.py service：完整expert→merge→残差/nextnorm的条件有限服务与独立端口/生命周期/FIFO/费用核查，含实际重SHA负例。
- compare_service76.py --root SERVER_ROOT --receipt-root FORMAL_RECEIPTS --suffix 03 --source-commit ORIGINAL_COMMIT --out NEW：完整24条件、6驻留对、12标签、4窗口对照，只接受同一费用版和正式接收根。

新版RQ控制通过已校准18key中的cmp/sub/max/sub逐output实现非负guard和min(raw_shift,128)，guard flags有真实存取和候选controller test成本；原移位、译码移位及等价证明独立记录。不得仅扩大微核shift范围，或拿旧L13/02与新版03拼排名。

精选包字节核验复用 closure/verify_delivery.py，原Git源字节核验 work/Liangruizhi/76/verify_sources.py（显式 --expected-phases）。仅核字节，不替代服务器完整算术/日历接收。权重与大归档留授权服务器，仓库放位置/大小/SHA及适量元数据。

完整消费者是显式currentnorm/router cut到nextnorm，并非整模型E2E、真实cached decode质量或目标时钟。RTL byte动作/同步ROM仿真、候选dispatch/服务slot、尚未实现的完整FSM/RF/STA/PPA分别报告。不得将标量carry成本无条件除8，或把巨大的BUS-attached frame基线当最佳硬件。
