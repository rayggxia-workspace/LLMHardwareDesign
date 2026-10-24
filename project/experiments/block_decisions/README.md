# Issue64：Block v2决策实验与独立接收

负责人Liangruizhi；Issue64/PR65；base PR62@30fcd63。正式[方案](../../../docs/BLOCK_PARTITION_V2.md)、[报告](../../../docs/experiments/issue-64-block-v2.md)、[成果索引](results/issue-64/index.json)。复用实际张量，不下载权重/重复完整推理；Phi封存不调参。CPU服务/软件整数不作为目标RTL、PPA或全模型质量。

## 范围和冻结版本

| 程序 | 冻结源码commit | 已执行 |
| --- | --- | --- |
| output.py | 46c0b46e46f786c785489ce8b316bc0a72fd3d28 |180固定A/W/acc×6输出合同，90048/49两轮 |
| attention.py及server_models/bounds.py |3a6416dffe932ea47e2e0141c7ff1006e7769b7e|真实完整GQA的56整数概率/受检PV32条件，90050/51 |
| receive_attention.py |24336c45e2e1622fd86de29a9a788a9e032d42d4|独立重算一整轮并核第二轮全文件一致，90055 |
| service.py及rq_ports/model.py |24336c45e2e1622fd86de29a9a788a9e032d42d4|576有界调度/96配对两轮，90056/57 |
| collect.py |c0038171976e9155241962a8f326ad38d53a097a|90058归档，精确SHA见索引 |

A只变最终Y，Y16保持原精确上下端点；整数delta不读评价FP，按16输出tile/row生成。现有数据已经观察过，是诊断，非新独立模型质量。B在显式FP输入桥/离线scale编译后执行整数QK/score/LUT/U64 sum-div/P15/PV32；其余模型仍有FP。C不计算实际数值，portable PV64/O16的条件服务与B的PV32接受分开；pack/transpose、宽scale/div、ROM单口、buffer/总线/credit均计入。只省内部header的组织不等于物理合宏已实现。

## 检查

使用已有NumPy Python，先执行管理检查，再业务检查。不安装新环境。服务器原执行Python3.12.7/NumPy2.2.6；本机接收NumPy2.5.4。

    python -B scripts/check_project.py
    python -B scripts/check_research.py
    python -B -m unittest discover -s project/experiments/block_decisions -p 'test_*.py' -v
    python -B project/experiments/block_decisions/receive_attention.py --self-test
    python -B work/Liangruizhi/64/audit_service.py --self-test

## 无权重精选接收

在D盘新任务目录，设置进程TEMP/TMP到该目录。精选ZIP已在results/issue-64/，不能解到已有目录；先核外SHA、安全成员、每成员SHA与原Git源，再独立数值/服务重放。需要Git可访问上述历史commit；若浅clone缺源，先取得对应任务历史，不能跳过源核验。

    python -B work/Liangruizhi/64/verify_delivery.py --archive project/experiments/block_decisions/results/issue-64/selected-evidence01.zip --sha256 2feae3548b4343a92975480778686e6fc14909c017d260e5419410d0994a86ab --repo . --extract <D盘新解压目录> --out <D盘新intake.json>
    python -B work/Liangruizhi/64/replay_selected_attention.py --input <解压目录> --out <D盘新attention.json>
    python -B work/Liangruizhi/64/audit_service.py --input <解压目录> --out <D盘新service.json>

精选B只有2个实际NPZ，覆盖61440 PV、381440 QK/score/exp/P15与两LUT6146项，不能对它运行要求全56 NPZ的full receiver。全56接收90055回执在work64/attention-independent.json，完整数据在授权服务器full ZIP。A两轮输出完整入精选，但独立上游Llama匹配还需原capture02/numeric04；当前本机D:/Projects/Codex/llama-downscale-20261023或full ZIP的llama/包含该输入。

    python -B work/Liangruizhi/64/audit_output.py --input <精选解压目录> --repo . --llama <capture02和numeric04的父目录> --out <D盘新output-audit目录>

work64/audit_output.py不导入producer，Fraction/动态delta/指标/包/原Llama输入均独立接收；完整A/W/上游partials不在本轮接收重新证明。scope见报告及回执。

## 服务器重放入口

以下只在docs/REMOTE_RULES.md授权本人目录，经Slurm lrz-*提交，原输入只读，输出必须新目录。冻结binding内含源SHA/commit；先后核源，不拿当前HEAD改写历史实验版本。完整实际命令、Slurm jobID及失败在work64/*submit*.json、execution-ledger.log和ZIP日志。

    python phase1/output.py --root <Issue61原目录> --llama <Issue64>/llama --binding phase1/binding.json --out <新A目录>
    python phase2/project/experiments/block_decisions/attention.py --root <Issue61原目录> --binding phase2/binding.json --out <新B目录>
    python phase3/receive_attention.py --root <Issue64目录> --code-root <Issue64>/phase2/project/experiments --out <新接收目录>
    python phase4/project/experiments/block_decisions/service.py --binding phase4/binding.json --out <新C目录>

C两种策略各自优化、不是全局最优；Gemma T≤1024未越window。90052/53/54为启动器引用错误，Python前失败；修复后同源90055/56/57完成，失败原日志仍保留。后续仅做真实消费者scale、连续R整数合同/公平归属、适用RTL布局/SFU资格；不重复本批A/B/C，不接管Issue55/63。
