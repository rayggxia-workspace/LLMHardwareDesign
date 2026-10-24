# Block v2 字段对照与离线接续合同

2026-10-24，Asia/Shanghai。交付状态 **local offline/pending**；本批没有对应新 Issue，不编造编号，不改 Issue #63 的通用适配器。本文比较字段能表达的内容，不把字段存在当作硬件能力实现。

2026-10-25发布追加：用户已授权以`huangpingyang04-lgtm`将该离线基准提交Draft PR；上句及原始source/run回执是10月24日快照。当前发布记录见[交接追加节](handoffs/2026-10-24-pending-block-v2-offline-prep.md)，固定来源和证据边界不变。

## 固定来源、取得方式和证据等级

旧估算器基线：`b06d85a801a87c07f9745ccae6950dc7e4cbd0d2`（PR #50）；旧候选快照仍为 PR #44 的 `3fa0b45070c7ce4587240589d48703d02a1b5246`，未覆盖。v2 基准固定为 [PR #73](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/73) 的 `88e9c4b2c3bb1b93b7155ba87ad11853e6c15512`，不从 main 推断未合并成果。

以下 D 级证据是从指定 commit 的 Git 对象读取的原字节文档，支持“文档提出的合同/报告的结果”，不是本次重新执行真实数值、服务或物理实验的证书。Git 采用已有 HTTPS partial clone，`git show <commit>:<path>` 获取指定小文件；没有下载归档或权重。线上 PR/Issue 匿名读取返回 404，GitHub 连接器无法完成身份查询，CLI `gh` 不在 PATH，**最新 head/合并/Issue #63 发布状态均 unverified**；未使用其他成员身份。下列实际 SHA 已本地核验。

| ID（下表引用） | 固定路径（v2 commit 同上） | SHA-256 |
| --- | --- | --- |
| S1 / D | `docs/BLOCK_PARTITION_V2.md`，重点 §3/4/12 | `aae18a910ad288cd52abdb290c77417fd75126656ce7823368fed8cf3857bdaf` |
| S2 / D | `docs/experiments/issue-72-numeric-closure.md` | `7e244fa8dbe11b9cd670abdf0896d7b43a8d52d1a805c99cb593117d4c2db522` |
| S3 / D | `docs/handoffs/2026-10-24-issue-72-numeric-closure.md` | `9192372682a5c2b9c3bdbcdd52c5d43881fe672c29e23ffbc2abb6f8091385f8` |
| S4 / D | `progress/Liangruizhi/STATUS.md`（只读） | `1473a4eaee8a05557df51fb56e458889a6a4a64b4d3ab35f8c43c7c23e706166` |

E1=`docs/LLM_RESOURCE_INPUT.md`；E2=`project/analysis/llm_resources/schema.json`；E3=`estimate.py`；E4=`profiles/block_candidate_v1.json`；E5=`test_estimate.py`（E3–E5 在 `project/analysis/llm_resources/` 下），均固定旧基线。E 类是实际本地代码/快照证据，仍不代表 RTL。逐文件 Git blob、SHA-256、commit、方法和原字节本地副本见 [sources/manifest.json](../project/analysis/block_v2_offline/sources/manifest.json)。T1/T2 指本批两个合成小图及独立 expected；证据等级仅为合成数学/协议。物理项没有本批证据，标 blocked/unverified。

兼容程度严格使用四级：**可直接复用**（已有字段可保存同一语义）、**可配置表达但需补充合同**（只能保存部分数量/注释，不能验证完整语义）、**需要新版本扩展**（应新增有类型的机器字段及执行约束）、**当前不可表达或缺证据**（没有该能力/资格来源）。未来建议的字段不是已接受的通用适配器规范。未知量用 `null` 并列原因；0 只表示已知没有该资源/流量。

## 1. 来源与版本

| v2 字段/语义 | 固定来源 | 旧估算器对应字段 | 兼容程度 | 建议表达方式 | 验证办法 | 缺失信息 |
| --- | --- | --- | --- | --- | --- | --- |
| contract_version | S1标题、§12；E2 | `schema_version=llm-resource-input/1`、候选`block-candidate/1` | 需要新版本扩展 | 独立v2合同；本批仅`block-v2-offline/1` | 拒绝把v2 JSON送入v1/改称v1 | 上游正式机器版本号未冻结 |
| source_commit | S1–S4；E3 `provenance()` | `model.source.revision`及Git provenance | 可配置表达但需补充合同 | 分开模型revision、合同commit、执行源、交付commit | 指定commit读blob并对SHA | 文档head不能替代各phase执行源 |
| path / SHA / Git blob | S1–S4；E3/E4 | provenance逐文件SHA、`PROFILE_COMMIT/BLOB/PATH` | 可直接复用 | 保留不可变源清单；新文件`delivery_commit=null` | 原字节SHA和Git对象对应 | 本地未提交成果尚无远端commit |
| 证据等级 / qualification | S1§1、S2结论；E1 status | `source.kind`、`unresolved`、无完整可行证书 | 需要新版本扩展 | 文档/合成/真实局部数学/条件服务/RTL/物理分层 | 每项结论指向对应等级 | 不能由“测试PASS”自动提升等级 |

## 2. Block 能力和服务

| v2 字段/语义 | 固定来源 | 旧估算器对应字段 | 兼容程度 | 建议表达方式 | 验证办法 | 缺失信息 |
| --- | --- | --- | --- | --- | --- | --- |
| M：S8 MAC、PARTIAL32/完整归约/可绕RQ | S1§3/4/12；E4 | M `native_mul8=256`、`rq_mul8=1` | 可配置表达但需补充合同 | 保留库存，另外声明typed输出/归约引擎及共享关系 | T1＋未来同函数服务轨迹 | 不能据256乘法器推出宽归约已实现 |
| V：norm/RoPE/激活/残差/scale转换 | S1§3/9/12；S2 | V 8个S8乘法器、16KiB | 需要新版本扩展 | op能力列表、完整hidden屏障、宽SFU/表端口 | T1仅残差；norm需单独证据 | 现有矩阵记账不执行这些算子 |
| A：概率/mask/Psum/PV完整闭包 | S1§3/6/7；S2 | A 8个S8乘法器/32KiB/20KiB ROM | 需要新版本扩展 | P15/KV/guard/共享M资源显式绑定 | Psum范围证书＋服务/ROM争用 | A逻辑闭包不等于第二矩阵阵列 |
| R：递推/conv/history/guard/提交 | S1§3/10/12；S2 | R库存及`recurrent_states`容量 | 需要新版本扩展 | 按状态事务及完整group屏障建模 | T2只验证加法协议 | 真实R整数算术/完整history不由本批实现 |
| S：生命周期存储slice | S1§3；E4 | `s_bank_count=8`、`s_bank_bytes=32768` | 可配置表达但需补充合同 | 每bank容量、owner、layout、1RW日历 | T2串行读/写；容量负例 | 实际可达端点、争用未校准 |
| D：DMA/描述符/完成/错误/版本控制 | S1§3；S2 | D 8KiB、RX/TX数 | 需要新版本扩展 | 有限描述符、异常/失效和发布协议 | 错owner/version拒绝；后续RTL | 队列深度/控制时序未知 |
| 库存数量与六逻辑模板 | S1§3/4/12；E3/E4 | `blocks[].instances`、S数量、`matrix_counts`扫描 | 可配置表达但需补充合同 | 固定制造实例与启用数量分开；A/R物理标签候选 | 库存和拓扑分开核对 | 六模板不代表六类物理硬宏冻结 |
| 算术能力、lane、宽乘/SFU | S1§3/12；S2宽度段 | `native_mul8`仅S8数量 | 需要新版本扩展 | width/op/II/共享资源矩阵；16×8需3、16×16需9基础积还含重组 | 算术分解＋真实微实现校准 | 8lane不代表8个ROM读或免费宽乘 |
| 频率 / 利用率 | S1§4；E2/E3 | `hardware.clock_hz/matrix_utilization`可空 | 可配置表达但需补充合同 | 未验频率保留null；合成配置标假设 | 旧线性下界；真实需STA | 不能把条件slots当芯片cycle |
| 服务率 / RQ II | S1§7/12；E2/E3/E4 | `rq_initiation_interval_cycles`、稳态proxy | 可配置表达但需补充合同 | 分别给每op的II、lane、资源共享/校准来源 | 同精度同资源服务对照 | 旧RQ II28敏感性不是实测或全链时延 |

## 3. 存储与端口

| v2 字段/语义 | 固定来源 | 旧估算器对应字段 | 兼容程度 | 建议表达方式 | 验证办法 | 缺失信息 |
| --- | --- | --- | --- | --- | --- | --- |
| 私有RAM及容量分区 | S1§3/9/10/12；E3/E4 | `private_bytes`、`mapping.matrix_tile` | 可配置表达但需补充合同 | 区分old/proposal/shadow/input/metadata与scratch | T1/T2区域求和、逐块容量反例 | 旧tile按W8A8+4B acc，不能泛化ACT16 |
| 共享bank容量 | S1§3/12；E2/E4 | `shared_reserve_bytes`、placement共享容量 | 可直接复用 | 单独记S库容量，保留其余驻留 | 旧回归禁止借RAM/ROM/FIFO补S | 新状态/其他流的活跃集合仍需给定 |
| ROM容量、LUT实际驻留 | S1§3/6/12；S2 | `rom_bytes`仅库存 | 可配置表达但需补充合同 | V8KiB/A20KiB与本批报告4,260,100B LUT分开 | LUT字节＋端口日历 | 不能把4.26MB表塞进旧ROM |
| FIFO容量/有效credit | S1§3/4；E4 | `endpoint_fifo_bytes`、RX/TX数量 | 可配置表达但需补充合同 | 每端点分配，记录max packet/credit及释放 | T1/T2 stop-and-wait只需128B/端点 | 深队列及并发死锁不覆盖 |
| S的128bit 1RW | S1§3；E4 `s_port`；E3 transport qualification | 候选字符串存在，未排程 | 需要新版本扩展 | 一个bank一次读或写，禁止同slot两动作 | T2 6个正常/7个重试bank访问索引 | 真实宏端口/读延迟未验 |
| 私有RAM/ROM真实端口 | S1§3/6/12；S2服务库存 | E4有容量、无所有端口模型 | 当前不可表达或缺证据 | 端口位宽/读写/仲裁/延迟单列null | 读写轨迹对实际宏合同 | 本批无宏实例/RTL资格 |
| lifetime与跨chunk驻留峰值 | S1§9–12；E2 recurrent额外字节 | 仅`extra_bytes_per_sequence`粗容量 | 需要新版本扩展 | 每区域生效/释放事件及overlap峰值 | T2静态保留R52/S44，不漏proposal/metadata | 全模型history、spills及共享竞争未知 |

## 4. 数值与归约

| v2 字段/语义 | 固定来源 | 旧估算器对应字段 | 兼容程度 | 建议表达方式 | 验证办法 | 缺失信息 |
| --- | --- | --- | --- | --- | --- | --- |
| dtype / ACT8与ACT16 | S1§3/4/12；E2 | 矩阵precision固定W8A8/INT32；KV可8/16 | 需要新版本扩展 | 边/节点独立dtype；ACT16降低成本另计 | 错dtype拒绝；不能改precision绕schema | ACT16算力、质量和布局未冻结 |
| logical_bits / storage_bits | S1§1/12；E2 transfers | `transfers[].logical_bits/storage_bits` | 可直接复用 | ≤64的容器字节账可复用；i33用i64 | 旧i33回归、T1 2×INT32=8B | 这两个字段不定义算术语义 |
| signedness、全码域范围 | S1§12；S2宽度勘误 | precision隐含S8，transfer无符号字段 | 需要新版本扩展 | 显式signed/unsigned、最负码边界、范围证书 | 正负边界与guard测试 | U128/S72不能塞入旧≤64字段 |
| unit / scale与合法加法 | S1§1/4/12；S2 | `quantization_contract`字符串，scale容量项 | 需要新版本扩展 | 有类型unit与版本；加法检查相同单位或显式转换 | T1拒绝group unit不匹配；T2拒绝unit | 字符串不能执行单位检查 |
| scale粒度 / row/head/output/K组 | S1§3/5/12；S2 grouped投影 | `accounting.weight_scale/kv_scale`为容量group | 可配置表达但需补充合同 | 容量可记；数值粒度及坐标另外类型化 | 对照分组scale/消费者单位 | 旧flat grouping不是实际逐行/组布局 |
| K分组计数/覆盖/唯一性 | S1§4/12；S2 | `matrix_tile.reduction`仅tile K | 需要新版本扩展 | group_id、范围、expected_groups/bitmap | T1漏组/重复组/范围负例 | 不能凭一个reduction字段证明全K完成 |
| partial / complete证书 | S1§3/4/12 | E2没有边类型 | 需要新版本扩展 | PARTIAL32与COMPLETE32/宽结果分别建边 | 等齐所有组后才使消费者可执行 | 跨tile/多输出真实证书未交付 |
| mixed-unit ALIGN_REDUCE | S1§4/12；S2 grouped投影 | E3没有对齐算子 | 需要新版本扩展 | group unit、目标unit、shift/宽乘/累加及范围guard | 未来Fraction oracle；本批只同unit | T1不能证明混合scale功能已实现 |
| 完整归约/bias后一次RQ | S1§4/12；S2 | 旧RQ仅输出数×II代理 | 需要新版本扩展 | 显式依赖和RQ次数，不按每partial RQ | T1合法[-2,3]，提前RQ[-2,4]被拒绝 | bias本批未加；多层图未覆盖 |
| RNE / 负数tie | S1§3/12；S2 | 无整数执行器 | 需要新版本扩展 | 明确round-to-nearest-even、除数及阶段 | T1 −3/2→−2、−5/2→−2；Fraction独立oracle | 真实宽RQ流水/吞吐未知 |
| SAT与overflow / exact store guard | S1§4/12；S2 | 无算术溢出判定 | 需要新版本扩展 | RQ处显式饱和；状态写回越界拒绝 | T1 SAT8边界；T2任一lane溢出整trial拒绝 | 拒绝不是模型rescale算法 |
| 通用宽位与受限软件能力 | S1§12；S2“必须计入的宽度和存储” | acc固定32、transfer最大64 | 当前不可表达或缺证据 | 区分required_bits、实现容器bits、guard域/回退 | 核最负码、完整N256界；本批不跑真实模型 | S32×C32读出通用72 signed bits；当前I64依guard；norm U128、RQ保守I128，均无RTL保证 |

## 5. 状态

| v2 字段/语义 | 固定来源 | 旧估算器对应字段 | 兼容程度 | 建议表达方式 | 验证办法 | 缺失信息 |
| --- | --- | --- | --- | --- | --- | --- |
| 唯一owner | S1§3/4/12；S2连续历史 | placement只有shared/external/unknown | 需要新版本扩展 | state_id→owner，写者唯一 | T2 R唯一owner，S请求冒充owner被拒 | 真实多head/key共享分区未覆盖 |
| alias / copy与只读快照 | S1§3/9/12；S2 | 无alias语义 | 需要新版本扩展 | copy必须容量/通信付费；S快照无写权 | T2复制不别名，返回值修改不污染R | 真实广播/缓存一致性未覆盖 |
| 初态 / 非零初态 | S1§3/9/12；S2 | recurrent元素计数不含初值 | 需要新版本扩展 | explicit initializer、epoch、setup账 | T2 s0=[1,-1]，初始两个副本单列 | 真实R/conv初始化合同未复现 |
| history / position | S1§9–12；S2“完整历史与失败恢复” | 无history/position协议 | 需要新版本扩展 | 与state/units共同保存/发布 | T2保存position=version；真实history不模拟 | 73,728B conv及完整多代历史仍待接入 |
| 生命周期 / chunk边界 | S1§10/12；S2 | recurrent容量与场景，未定义release | 需要新版本扩展 | commit为生效点，chunk不重置 | T2正常三步等于1步＋文件保存恢复＋2步 | checkpoint只支持此图成功prefix |
| state unit | S1§10/12；S2 | 无执行字段 | 需要新版本扩展 | unit随代持久化，不能只放可丢header | 错unit与重哈希checkpoint错误被拒 | 因果重标和单位变化不实现 |
| epoch | S1§10/12；S2 | 无状态代际字段 | 需要新版本扩展 | epoch关联单位/参数/profile | T2固定0，错epoch拒绝 | 本批没有epoch递增/rescale |
| version | S1§10/12；S2 | 无版本字段 | 需要新版本扩展 | expected_version与成功commit递增 | t2重试后v2，仅成功发布一次，旧请求拒绝 | 真实分布式去重/消息乱序未覆盖 |
| trial / shadow | S1§10/12；S2 | `extra_bytes_per_sequence`可粗容纳 | 可配置表达但需补充合同 | 容量可保留，私有性/版本语义需新字段 | T2 old4+proposal8+shadow4+input4+meta32=52B | 原位rollback未证明，不能省shadow |
| guard与整体原子commit | S1§4/12；S2 | 无事务执行/发布屏障 | 需要新版本扩展 | 整group检查→shadow→状态/版本共同发布 | T2 lane1越界时lane0也不发布 | Python概念原子事件不证明硬件原子性 |
| abort / retry / late failure | S1§10/12；S2；S3 | 无失败/重试流量 | 需要新版本扩展 | abort丢私有代，重试同token且另付传输 | t2提交前失败保留[3,0]/v1；7包重试账 | 完整消费者失败/队列/回滚协议仍待真实实现 |

## 6. 通信

| v2 字段/语义 | 固定来源 | 旧估算器对应字段 | 兼容程度 | 建议表达方式 | 验证办法 | 缺失信息 |
| --- | --- | --- | --- | --- | --- | --- |
| source / destination / 有向path | S1§3/4/12；E2/E4 | `transfers[].path`、`logical_bindings_hybrid` | 可配置表达但需补充合同 | typed边和实际实例id分开；只复用已存在路径 | 旧缺边拒绝；T1 M→V/T2 S↔R | 合成S不是旧S0–S7物理实例映射 |
| shape / layout / valid范围 | S1§1/3/12；E2 | transfers shape，未建layout/valid | 可配置表达但需补充合同 | shape可复用；layout/valid/transpose需扩展 | 错shape/layout拒绝；重排另付成本 | 本批固定小向量，无动态mask |
| 每步消息次数 | S1§1/12；E2 | `messages_per_step`可空 | 可直接复用 | 正常/失败/重试/初始setup分开 | T1两条；T2正常六条/重试七条 | 完整模型流量表没有由shape自动生成 |
| 单跳/跳数/转发 | S1§4；E3 transport | path长度−1逐跳记账 | 可直接复用 | 每跳header/payload/端点成本 | 旧多跳回归；本批hops=1 | 无真实可达或时序资格 |
| header与unit/epoch/version元数据 | S1§1/5/12；E2/E4 | `packet_header_bytes`、`metadata_bytes` | 可配置表达但需补充合同 | 小图预留64B header容纳；额外metadata不得漏计或重复算 | 合同拒绝改header；README列预留字段 | S2服务header32B与本批64B不同，禁止混套 |
| payload对齐/分片/容器 | S1§1/5/12；E3/E4 | `beat_bytes=64`、FIFO2KiB、`packet()` | 可直接复用 | 64B payload对齐、最大1984B payload；128bit每拍16B | 1984/1985分片边界；小图4B/8B均128B包 | 旧beat_bytes是对齐粒度，非128bit链路拍宽 |
| 带宽 / 链路拍数 | S1§7/12；E2/E3 | clock/fraction、edge/shared_TX下界 | 可配置表达但需补充合同 | 物理包字节÷16得理想服务拍；真实速率留null | T1 16拍；T2 48拍 | 不含计算/等待，不是端到端延迟 |
| 背压/credit与队列 | S1§3/4/12；E3 unresolved | 未做完整争用/死锁 | 需要新版本扩展 | 小图只stop-and-wait、单在途，无免费并行 | FIFO128B下界，S 1RW串行动作 | 任意路由/并发队列与deadlock不证明 |

## 7. 物理资格

| v2 字段/语义 | 固定来源 | 旧估算器对应字段 | 兼容程度 | 建议表达方式 | 验证办法 | 缺失信息 |
| --- | --- | --- | --- | --- | --- | --- |
| 已制造实例/宏view | S1§3/4/12；S3 | candidate库存是数量账 | 当前不可表达或缺证据 | `physical_instances=null; qualification=unverified` | 未来实例/网表/LEF/Lib一一绑定 | blocked：无本批v2冻结宏清单 |
| 真实端口/引脚/固定接入 | S1§4/12；E3 unresolved | 逻辑RX/TX计数、path | 当前不可表达或缺证据 | actual pin、access point、连接白名单单列 | 实例到pin/金属几何资格 | blocked：不能由候选path证明物理可连 |
| 冻结底座/禁止新增有源资源 | S1§4/12；S3 | 数量扫描不代表制造冻结 | 当前不可表达或缺证据 | 冻结库存hash、可选择端点及变更规则 | 冻结前后网表/库存/坐标核验 | blocked：本批无底座artifact |
| 限定金属层 / 技术过孔 | S1§4；S3 | 无层/过孔/RC模型 | 当前不可表达或缺证据 | 层集合、合法via/enclosure、track预算保留null | 真实工艺DRC/受限路由/RC/STA | blocked：技术/库/时钟/PG/DRC均未验 |
| 物理收益/PPA与端到端 | S1§4/12；S2结论 | 旧status明确无完整可行证书 | 当前不可表达或缺证据 | 明确`blocked/unverified`，不生成PPA PASS | 后续独立硬件/应用验收 | 本批没有EDA/RTL/完整模型执行 |

## 8. 计算边界与接续

| v2 字段/语义 | 固定来源 | 旧估算器对应字段 | 兼容程度 | 建议表达方式 | 验证办法 | 缺失信息 |
| --- | --- | --- | --- | --- | --- | --- |
| 当前可计算的数量 | E1–E5；T1/T2 | 容量/线性MAC/指定流量/库存下界 | 可直接复用 | 旧工具照常运行；小图另算明确数值/协议 | 31旧回归及本批独立known values | 旧工具本身未升级为v2 |
| 只能给下界/假设账 | S1§3/12；E3 | linear lower bound、unresolved、服务proxy | 可配置表达但需补充合同 | 每结果附假设、已计入/缺项和频率null | 明确缺项不当免费 | 任意新库存拓扑不能自动复制 |
| 当前尚不能表达/验收 | S1§4/12；S2/S3 | 未实现mixed scale/事务/真实宽算术/物理 | 需要新版本扩展 | 给Issue #63字段建议、失败语义和固定fixture | 先同函数同资源，再校准服务/RTL | 不接管或假装取得服务器适配器源码 |

本批验证器只消费 [两个固定小图](../project/analysis/block_v2_offline/README.md)。它有意拒绝提前RQ、更换unit/owner/epoch/依赖等改变合同的输入；合法的其他数值在Python API中可用于边界测试，CLI交付验证还校验固定fixture字节。广义ALIGN_REDUCE、真实rescale、完整history和动态MoE路由是后续版本的工作，不能用两个小图通过替代。
