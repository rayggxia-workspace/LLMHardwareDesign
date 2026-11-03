# H1 v0.1 辅助资料与静态证据

Issue151 / PR152，Melodydt，2026-11-03T17:46:36.965252+08:00，Asia/Shanghai。
正式报告：[H1_WORK_REPORT](../../../../docs/H1_WORK_REPORT.md)；[图规格](../../../../docs/H1_GRAPH_CONTROL_SPEC.md)。

研究输入08451c3a563cdb331a3516d83cbf9647cd0554b1，实际检查源码 4b8e5e17cc65db8105dce43d52e93220af6942a9，5源文件Git blob/内容读回见source-commit-receipt.json。
IR版本h1.graph.0.1、目标h1.target.0.1；Python工具版本、4输入及checker SHA、全部生成件SHA见evidence/report.json。

evidence含每图program/lowered/tables/image/schedule，参数只是符号引用，native数值和MEM不在本轮执行范围；review保留三类发现、r01审查期望诊断修正及r02真实通过，不构成外部PR批准。
当前三图4路径/28正式拒绝+11独立probe通过；逻辑镜像1184/2016/1808B，edge峰2/2/3槽，5856B共同容量候选。
final-checks.json为最终静态/范围检查；local-PDF-index.json为同一本地PDF覆盖后的真实QA索引。没有PDF上传，未新建PDF版本。

复现：python -B -X utf8 scripts/check_h1_graphs.py --root . --source-commit 4b8e5e17cc65db8105dce43d52e93220af6942a9
独立审查：python -B -X utf8 work/Melodydt/151/h1/review/independent_h1_review.py --help
参数提供者、返回信用和helper为明确抽象前提，不能当已有RTL。未知物理位单元、面积、读周期、MEM供给标为待核实；无仿真、数值或后端实验。
PR待外部审查，Issue不done；登记pending、看板unverified/同步pending，处理人待指定。
