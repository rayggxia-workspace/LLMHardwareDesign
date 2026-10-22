# 从候选宏视图接入真实端点的合同

2026-10-22（UTC+08:00），Issue13/16／Liangruizhi。Issue13只读核对Issue7材料及指定视图；Issue16随后冻结三份普通LEF并导出原始几何，见[实测记录](experiments/issue-16-macro-endpoints.md)。两任务均没有运行EDA或干预作业；Issue13消融仍使用独立合成库存，没有以真实视图校准其结果。

## 已核实的输入位置与资格

来源：[PR10阶段验收](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/2b76f692830a2bdfc157cefb21c3bc1bc91fc409/docs/experiments/issue-7-parallel-blocks-acceptance.md)及[视图诊断](https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/2b76f692830a2bdfc157cefb21c3bc1bc91fc409/project/experiments/parallel_blocks/results/parallel-blocks-wave2-16-diagnostic.json)。9份完成布线终态中ACT20、修复ACT10、MXU20、GEMM20通过该工具门槛，但完整硬宏资格仍为false。根17合并块CAP_MARGIN30/40在开始本任务时无已入库终态，不能预判。

按REMOTE_RULES使用本用户既有SSH入口，只读确认三组普通LEF、typ Liberty、detailed LEF可读。共同前缀为 `/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/parallel-blocks-wave2-06/`；相对stem如下，每组有`.lef`、`_typ.lib`、`.detailed.lef`：

| 候选 | 相对stem | 尺寸µm | signal输入／输出 | signal pin层数 |
|---|---|---|---|---|
| ACT20 | act-cap20/flow/results/nangate45/parallel_opentpu_act/base/llhd_opentpu_act | 326.205×326.205 | 220／640 | M5=120，M6=740 |
| MXU20 | mxu-cap20/flow/results/nangate45/parallel_opentpu_mxu/base/llhd_opentpu_mxu | 1100.455×1100.455 | 1529／643 | M5=1111，M6=1061 |
| GEMM20 | gemm-cap20/flow/results/nangate45/parallel_llaccel_gemm/base/gemm_engine | 1157.32×1157.32 | 3080／673 | M5=1166，M6=2587 |

普通LEF版本5.8、DATABASE MICRONS 2000，每个signal pin有一个RECT；普通LEF分别132447、338311、623710字节。Issue16已于08:40UTC冻结这三份普通LEF的原字节／SHA-256及6791PIN、6956PIN RECT和30OBS RECT，原始PG/PORT结构保留；版本若在下轮变化须另建输入版本。详细OBS文件仍仅查过可读与大小，未读取大体积内容或计算哈希，不因本合同扩大例行检查范围。

三组Liberty声明time_unit=1ns、capacitive_load_unit=(1,fF)，但缺minimum_period/min_period，完整arc、外部driver/load、PG与等价尚未闭合。MXU输出max_capacitance仅575/643、GEMM366/673有字段；零cap不能视为免费端点。synthetic SRAM、LEC_CHECK=0仍是来源边界。

## 下一任务必须冻结的记录

| 类别 | 必需字段与拒绝条件 |
|---|---|
| 来源 | Issue/PR及实际代码commit、运行attempt、导出脚本commit、精确文件路径、输入字节数/SHA-256、配置/工具版本、提取时间。未冻结输入不称可复现校准 |
| 几何 | macro名称、单位/DBU、origin/size、安装位置与orientation；每pin原名、方向、use、全部port/layer/rect。不能把一个RECT自动等同一个合法via位置 |
| 端点映射 | RTL端口/bit到LEF pin和Lib pin的明确关系、时钟/PG/未用pin分类；缺失、重复、多RECT、转义名称或多bit缩并必须显式报告 |
| 工艺访问 | 候选via/metal层、方向、线宽/间距、enclosure、端点接入与OBS检查。不能靠移动pin、切线、临时buffer或不同宏视图修好后仍称同底座 |
| 电气 | 输入cap、输出max_cap/transition及其覆盖状态，边界driver/load，时钟周期/arc及缺失标记。无模型填待核实，不能把缺字段或零值改成无限能力 |
| 等价与资格 | 源RTL到物理等价、PG连接、内部时钟和minimum_period等资格状态；明确局部工具通过不代表完整硬宏合格 |
| 成果 | 轻量端点表/审计结果/索引及SHA-256；大OBS/数据库保留获授权共享位置。不在Git仓库复制大数据库或他人凭据 |

## 与实验衔接

Issue16已建立可重放的普通LEF输入与原始几何库存，PR18待审查。下一步核对真实ACT—MXU逐bit连接合同、宏安装位置、朝向与各端允许层。接入前保持两套证据尺度：几何端点存在可用于访问研究，时序/功耗有效性仍需资格与边界模型。

若接入层、OBS、driver/load或宏资格仍缺失，可以研究明确标注的几何必要条件，不能宣称工艺合法、物理H2或PPA优势。下一轮端点感知映射须固定每例K个mapping与路由预算，另列预处理成本；不要在本次已观察图上声称新盲测。
