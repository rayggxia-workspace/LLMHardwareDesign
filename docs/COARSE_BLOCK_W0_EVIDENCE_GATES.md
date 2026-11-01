# W0／主线一：证据门与下一W1最小准入合同

Issue151 / PR152；parent `bd7cb2f3060c61e5d28a2ece0653dd9336a024af`；保留叶源`707878621b2add4ed218b8c43df2e95c9a56e2ba`。本轮观察PR144 head `d1f26884b13f8d0466bbaefe2fc6322a14c66df9`，14/14核心文件与707逐字节相同；这是来源观察，不是整分支升级或物理资格转移。本轮仅W0合同和证据整理；没有新RTL、仿真、SystemC、服务器/EDA或ref-project修改。文档与合同按原Issue/PR交付，上传及审查状态以本轮回执为准。

## 1. 当前真实证据，及其不能证明的范围

本目录生成器读取P1验证矩阵、P2状态、原始run-receipt及两份simulation日志，核对**33个原requirement ID、13项P2 requirement、19个唯一CASE_PASS**。19例同时与状态表/receipt/原始日志一致，来源说明从P2独立报告逐项提取，不把W0静态复核说成重跑RTL。

历史P2真实结果：S helper 6场景/141周期；固定MST 13场景/1101周期。五个正常批次各16笔S请求/ACK、7个M命令/响应、A/B各一拍、loader一次done、T四字和RELEASE。全局Sreq113/Sack112差一是abort丢弃的一个未消费ACK；不能说正常路径丢ACK，也不能写成全局无条件守恒。N/E/G/R只有编译门，没有由这19例取得功能组合资格。

P2仍未整体验收。已测只是S8×S8、row1/tile1/K8/N8、bank0/factor1/left0、四包raw S64；启动许可门停顿不等于已呈现native valid而cmd_ready低的全部情形。P1有限Python参考、当前静态检查、真实RTL功能、形式活性、整模型数值质量及物理接收分别记录，不能互相替代。

## 2. P2剩余门：13个ID全部保留且打开

JSON逐项保留原check、P2已测case、原remaining文字；每门附未来测试名称、预计输入、可判定预期、未来W包及证据层。全部未来测试均`NOT_EXECUTED_FUTURE_REQUIREMENT`，共20项，不是20次已执行仿真。

| 原ID | 主要剩余测试与输入 | 预期判定／后续归属 |
|---|---|---|
| MST-01 | 多rows/tiles/lastK/N的S8独立dot oracle | 逐行/列真实sum与op3顺序；W1后续native/kernel harness。首个W1仍固定shape，不擅加运行shape配置 |
| MST-02 | S8/S16、signed scale、left、clear/append、多K、op6/reset scale | 数学segment-scaled sum；op6保scale/reset恢复1；溢出不能包装成成功；W1 |
| MST-03 | 先seed旧行，再混合一行overflow/一行成功，含末列才溢出 | 失败整行保旧、成功整行提交、fault_rows准确；不能整命令rollback或blind append重试；W1 |
| MST-04 | op5 RNE/tie/负数/shift/clip与载体布局；op12有限owner | 四S32 carrier与逻辑宽度区分；S40诊断只有有效slot，不是可恢复merged；W1/W3 |
| MST-05 | 普通S读写与wide同拍、独立响应停顿；same-S overlap copy | wide真实bank优先、写ACK echo及保持；memmove/无held-response等待环；W1/W6 |
| MST-06 | 各geometry/fmt/half/bank、边界/未对齐/越界、A/B独立停顿、reuse_b | 完整拍数/布局、done后置；reuse身份由外侧证明，不虚构native版本检查；W1/W6 |
| MST-07 | 真实valid在ready低时保持；多边随机有界停顿 | 字段稳定、逐任务accept/retire守恒；记录seed/停顿上限/环境假设；W1/W2/W6 |
| MST-08 | 每关键生命周期reset/abort；另立无reset drain取消合同 | RAM/外部前缀不回滚；loader等既接收义务真实排空；两种机制不混称；W1/W6 |
| MST-09 | T长度1/2/4/383/384及首/中/末字停顿 | 填满→SEALED/commit、读启动、末take后release，fragment非全job；W1/W2/W6 |
| MST-10 | T非法size/index、early控制、revoke/commit竞争 | 仅真实size/index诊断置粘性error，其余早控制可能只不握手；无commit_error；W1/W6 |
| MST-11 | 不同bank/fmt/scale、selected-bank锁/另一bank装载与连续新数据 | 不拿旧响应/有效位完成新任务；W1/W3 |
| CTRL-01 | 固定程序、完整输入/参数capture、SERVICE接受与WAIT完成 | 功能义务保留；旧64bit/4或8字/十64B实现表示待审查取舍，不强行搬回W1；W1 |
| CTRL-02 | 单前台输入完整性/复用；将来tag/credit或明确无tag证明 | 不允许旧/半包/旧响应完成新生命周期；有seq时排空不回绕，无tag时须证明串行/协调reset等价安全；W1/W2/W6 |

其余20个P1 requirement保留原ID、目标阶段、当前未通过/待审状态和W包归属，未因本轮范围小而删掉。通用CTRL的具体位宽/十接收bank只是旧候选表示；既不能为让检查通过悄悄删有效义务，也不能未审查就把较大通用ABI恢复为最低硬件。W0将这两项表示差异明确留给独立设计审查，不能据此自动把原P2 gate标PASS。

## 3. W0自己的退出清单

1. parent/叶源、上游观察点、P1历史与P2当前源区分明确，相关源材料SHA可追溯。
2. 33原ID全部保留；13项P2剩余门有未来测试、输入与可判定预期。
3. 19个历史case与receipt/status/log一致，真实scope及正常/abort计数差异明确。
4. 管理、静态、Python、RTL、活性、质量、物理证据不替代。
5. CTRL旧通用表示与当前固定程序之间的取舍有显式待审处理，不伪造已验收。
6. W1最小入口/输入stored ACK/唯一S owner/输出及reset合同可实施，未知项仍是gap。
7. 根任务完成要求的独立设计审查、PR及协作交付证据；本子包不代替它标验收。
8. W0材料完成不等P2/full profiles完成，也不等W1已开始。

当前状态为**产物prepared、pending review**。本轮W0自身通过静态一致性检查也只支持“材料可审查”，不能单方面满足第7项、关闭Issue或提升P2阶段状态。根任务后续实际验证/上传/登记以`w0-checks`和PR回执为准；生成文件的待审状态不意味着根整合流程始终未执行，外部独立PR审查是否完成须有另行证据。

## 4. 下一W1可先实现的最小入口：固定程序/shape/地址，只改tensor数据

建议第一个W1切片为`W1_FIXED_DOT8_VARIABLE_TENSOR`，不是全部W1冻结。固定S8×S8、row1/tile1/K8/N8、bank0、factor1/left0，固定op6→op4/1→loader→op10/0x9884→op3四包→S→T4字。没有运行时地址、shape、opcode或scale配置，也不启动装控制程序。

入口按序8拍128bit，可用`in_valid/in_ready/in_data[127:0]`，拍号由本地0..7计数，不暴露任意S地址：

| 拍 | 实际写入S | 内容 |
|---|---|---|
| 0 | 448 | 低64为8个signed S8 A；高64由硬件强制0 |
| 1..3 | 449..451 | 整字由硬件强制0，不能依赖旧RAM |
| 4..7 | 452..455 | 共64个S8 B，n-major地址`8*n+k` |

有效数据A8B+B64B=72B，传输8×16=128B，56B padding须**实际写零并等ACK**。padding源值可以忽略并canonicalize，不把非零padding编造成native S错误。只有一拍入口事务在途；本地同一S helper完成写及ACK后再推进，其他并行入口优化另验。

`input_stored`完整标记只能在当前frame8拍均被接受、8笔真实S写ACK均已消费且无pending输入后置位；未到齐不允许loader/EXEC，也不允许start_ready。它保持绑定本frame直到done消费/reset/abort，不能被下一task沿用。S原生没有初始化有效性，reset不清RAM；这个新标记和region生存期必须由岛壳实现。

**必须移除/替换原P2 literal S_INIT的写行为**：入口已经在RUN前存好，RUN内该服务只能检查INPUT_STORED等已接收条件，不能再次把函数常量写回448..455覆盖用户数据。这是冻结前新RTL设计变更，仍为永久固定程序，不是运行时加载程序。

当前frame完整后才接受start；early pulse不排队，保持valid的源可在ready后握手一次。RUN及pending DONE期间不再接受覆盖frame的数据。M ACK/EXEC status过滤，只有op3数据写S456..459并逐字等ACK，随后读S填T。T固定owner0/generation1/words4，真实read take四次后RELEASE；完成/错误保持到done_ready，末字不是释放或整个任务完成。

计数边界要更新：**入口frame8写ACK＋RUN4结果写ACK＋RUN4读ACK=总16笔S事务，但从start到done的RUN区间只有8笔。** M仍为7命令/响应，T仍四字及release。不能直接沿用P2从start开始统计16笔S的scoreboard。

### reset/abort与新frame

- hard reset清frame标记/计数、叶和helper生命周期及完成；RAM不回滚，不凭空补done。
- start前的部分frame或已存好未start frame遇abort：丢弃frame标记，无已接受task就不造task completion；新输入须从第0拍重来。
- RUN abort沿用协调复位并产生一次保留error完成；已写S与外部已消费前缀不回滚。不是无reset drain取消。
- 已有DONE遇abort保持原完成结果，done_ready可以消费一次；之后必须收全新8拍及ACK，不能带旧input_stored进入下一任务。

## 5. W1未来独立期望和退出门

JSON含5套明确标为**未RTL执行**的dot8向量：P2 literal、全零、全`-128×-128`、全`-128×127`、非均匀不同列。独立整数公式为`dot[n]=Σ signedS8(A[k])*signedS8(B[8*n+k])`，raw精确范围`[-130048,131072]`，每128bit低/高64为相邻两列。两个极值分别全列131072、全列-130048；无需浮点/舍入，当前固定profile不可能数学S64溢出。

未来W1最少6类RTL测试：不完整frame/ACK停顿不能start；5向量实际输出且无literal覆盖；预填脏padding后确认56B真写零；两个不同frame不继承完整标记；入口/输出/DONE反压及分阶段计数；输入写前后、RUN与DONE的reset/abort及新frame恢复。期望不能从DUT结果反推；现有P2向量通过也不代表新增变量入口通过。

可变shape/地址/格式/scale、通用packet/handle/epoch、多任务队列、无reset取消、一般fragment/forkjoin、N/E/G/R、MEM/NUM、完整profile及PPA都仍是后续gap；本轮不擅加这些运行配置，也不声称全局回滚。W1最小入口只有tensor数据变化，它为共同岛壳的后续扩展提供独立可验证第一刀。

## 6. 复核命令及本轮边界

本目录`build_w0_evidence_gates.py`只读取固定输入材料并生成JSON；`check_w0_evidence_gates.py`只核对trace、scope、位数/计数和Python整数期望，不调用仿真器。当前管理结构检查PASS、47项静态trace/期望检查PASS，均仅为本轮实际静态检查；Python3.7、UTF8/LF。管理检查不能替代这些合同检查，这些检查也不能替代RTL。整合后可用checker的`--directory`指定JSON目录、`--report`指定正式说明文件。

```powershell
python -B -X utf8 work/Melodydt/151/build_w0_evidence_gates.py --root . --output-dir <independent-dir>
python -B -X utf8 work/Melodydt/151/check_w0_evidence_gates.py --root . --directory work/Melodydt/151 --report docs/COARSE_BLOCK_W0_EVIDENCE_GATES.md --receipt work/Melodydt/151/w0-gates-checks.json
```

正式整合/在线状态以本轮PR回执为准，独立审查和实际业务验收另行完成；不以W0交付关闭P2、W1或全模型任务。
