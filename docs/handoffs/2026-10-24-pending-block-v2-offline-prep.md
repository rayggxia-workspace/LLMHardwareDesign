# Block v2 字段对照与两个合成图：独立离线交接

日期：2026-10-24，Asia/Shanghai（UTC+08:00）。规则：rayggxia-project-collab 1.0.0。本批状态 **local offline/pending**，没有对应新Issue，不编造编号；没有创建/修改Issue、PR、评论、标签或Projects，没有push/merge。用户本次离线指令优先于协作规则的通常线上流程。

**历史快照说明**：下述离线身份/HEAD/未提交/禁止发布等事实对应2026-10-24交付时刻。2026-10-25用户已新增发布授权并指定`huangpingyang04-lgtm`，最新发布事实见文末追加节；旧证据run01/run02及source manifest不回写为新状态。

## 路径、分支与成果身份

- 目标仓库：[rayggxia-workspace/LLMHardwareDesign](https://github.com/rayggxia-workspace/LLMHardwareDesign)，project_id=`llm-hardware-design`。
- 本地主仓库：`C:/Users/86188/Documents/ChatGPT/LLMHardwareDesign`，原main保留。
- 已交付估算器：`C:/Users/86188/Documents/ChatGPT/2026DAC/LLMHardwareDesign-resource-estimator`，原任务分支保留。
- 本批独立worktree：`C:/Users/86188/Documents/ChatGPT/2026DAC/LLMHardwareDesign-block-v2-offline-prep`。
- 临时本地分支：`codex/block-v2-offline-prep`，基线与当前HEAD均为`b06d85a801a87c07f9745ccae6950dc7e4cbd0d2`；新成果**未提交**，`delivery_commit=null`、`delivery_source_bound=false`。不能把本地文件标作已经绑定远端commit。
- 开始时目标目录/分支不存在，确认估算器干净及基线后以`git worktree add -b codex/block-v2-offline-prep <上述目录> <基线>`创建。没有reset/切换其他任务分支。
- 正式成果：[字段对照表](../BLOCK_V2_FIELD_MAPPING.md)、[两图README](../../project/analysis/block_v2_offline/README.md)、[输入合同](../../project/analysis/block_v2_offline/CONTRACT.md)、`fixtures/`四份独立JSON、`replay.py`、`test_replay.py`、`validate_delivery.py`。
- 辅助证据：`sources/manifest.json`及四份固定源原字节，`fixtures/sha256.json`，`evidence/run01/`首轮原stdout/stderr/回执。补齐文档和范围检查后的最终记录为[run02/validation.json](../../project/analysis/block_v2_offline/evidence/run02/validation.json)，逐项查看实际退出码与`all_required_local_checks_passed`。

## 实际来源与线上核验限制

本批固定读取v2 commit `88e9c4b2c3bb1b93b7155ba87ad11853e6c15512`，用户给定来源[PR #73](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/73)。不是仅阅读main，不悄悄换最新head。

| 实际源路径 | SHA-256 |
| --- | --- |
| `docs/BLOCK_PARTITION_V2.md` | `aae18a910ad288cd52abdb290c77417fd75126656ce7823368fed8cf3857bdaf` |
| `docs/experiments/issue-72-numeric-closure.md` | `7e244fa8dbe11b9cd670abdf0896d7b43a8d52d1a805c99cb593117d4c2db522` |
| `docs/handoffs/2026-10-24-issue-72-numeric-closure.md` | `9192372682a5c2b9c3bdbcdd52c5d43881fe672c29e23ffbc2abb6f8091385f8` |
| `progress/Liangruizhi/STATUS.md`（仅读原文，副本位于sources下） | `1473a4eaee8a05557df51fb56e458889a6a4a64b4d3ab35f8c43c7c23e706166` |

取得方法为现有HTTPS partial clone对象库的`git show <指定commit>:<path>`原字节，缺失小blob可由Git惰性取得；保存Git blob/字节数/commit/SHA/本地副本。没有下载实验zip/真实张量/权重。原估算器五个重点文件、适用AGENTS/Skill、project.json、COLLABORATION、STATUS、ARCHITECTURE及历史交接也已读取，其固定基线SHA见[源清单](../../project/analysis/block_v2_offline/sources/manifest.json)。最终runner设置`GIT_NO_LAZY_FETCH=1`，只核已有对象。

GitHub身份核验未成功：连接器`get_user_login`先提示缺link_id，指定YUZE-LU后返回Unknown tool；`get_profile`仍提示缺link_id，系统PATH无gh。未借用其他成员身份。匿名web读取PR73与Issue63返回404，不据此推断私有资源不存在。最新PR/Issue状态、是否有新增成果及线上差异均**unverified**，没有伪称最新状态已核或源文档实验已被本次重跑。固定Git对象/路径/摘要已核验，底层服务器原始证据未重新验证。

## 字段对照主要发现

对照逐行包含v2语义/固定来源/旧字段/四级兼容程度/建议表达/验证/缺项，覆盖来源、能力、存储、数值、状态、通信、物理与边界八类。

旧工具的shape、logical/storage位宽容器、每步消息数、指定有向路径的逐跳打包以及部分容量账可复用；私有RAM、ROM、FIFO与S共享bank不能互借。频率、服务率、真实物理连接没有证据时留null并标缺项，不用0替代未知。

W8A8/INT32是旧主矩阵合同。ACT16、signedness、混合K组unit、PARTIAL/COMPLETE证书、ALIGN_REDUCE、RNE顺序及状态owner/unit/epoch/version/guard/abort/commit需要新版本机器字段；仅把文字放进`quantization_contract`不等于机器可验证。六模板M/V/A/R/S/D仍是逻辑模板，库存数不等于六类物理宏冻结。

通用宽度与受限软件实现必须分开：S2明确S32×C32完整N256读出通用最坏72 signed bits，当前I64候选依赖guard；norm U128、保守RQ I128及分组对齐宽算术不能统一按INT32/INT64处理，也不能把保守宽度称为样本必须有对应物理乘法器。物理实例/真实端口/固定接入/冻结底座/限定金属层与技术过孔全部blocked/unverified。

## 两图输入、手算与成本

图1：x=[2,-1,3,4]，W=[[1,2,-1,0],[-2,1,1,2]]，均signed INT8，K4分两组K2、unit1。手算partial `[0,-5]`及`[-3,11]`，完整归约`[-3,6]`，RNE除2/SAT8得`[-2,3]`、unit2；加预置同unit残差[1,-2]得`[-1,1]`，INT16。提前对组RQ再加得到`[-2,4]`，改变函数，输入合同拒绝该顺序。负数tie额外用独立Fraction oracle核对。

图2：s0=[1,-1]，u1=[2,1]、u2=[-1,4]、u3=[3,-2]，unit1、epoch0。R唯一owner，proposal INT32，经全lane精确INT16 guard后原子提交；成功态/版本为`[3,0]/v1 → [2,4]/v2 → [5,2]/v3`。t2 shadow生成后失败仍保留`[3,0]/v1`及S只读快照，失败无输出。重试t2成功一次、旧请求拒绝；错owner/version/epoch/unit和正负INT16溢出拒绝。实际临时文件保存恢复后两步与连续三步一致，chunk不重置。

统一合成通信：单跳128bit、每拍16B、header64B、payload64B对齐、包≤2KiB；元数据装预留header。单在途stop-and-wait；小包需要每端点128B FIFO。链路拍数不代表端到端延迟。

| 情形 | 消息/逻辑payload/物理字节/理想链路拍 |
| --- | --- |
| 图1两条PARTIAL32[2] | 2 / 16B / 256B / 16 |
| 图1预置x/W/残差（单独可选加载账） | 3 / 14B / 384B / 24 |
| 图2正常三输入+三快照 | 6 / 24B / 768B / 48 |
| 图2含t2失败后重试 | 7 / 28B / 896B / 56 |
| 图2初态R/S两copy（单列setup） | 2 / 8B / 256B / 16 |
| 图2三个输入预置（单列setup） | 3 / 12B / 384B / 24 |

初始预置不计runtime，setup不是已冻结外存/主机传输。图1V内部后续算子无跨块消息。S正常访问索引`读1/写1/读2/写2/读3/写3`，重试则在失败读2之后再读2；每个索引只有一次128bit 1RW读或写，未赠同周期读写；中间等待/计算不作为真实周期预测。

| 显式静态保留 | 可复核容量 |
| --- | --- |
| 图1 M | x4+W8+两partial16+metadata24=52B |
| 图1 V | partial16+complete8+RQ2+residual2+output4+metadata32=64B |
| 图1 FIFO/总计 | M.TX/V.RX各128B，总372B |
| 图2 R | old4+INT32 proposal8+INT16 shadow4+input4+metadata32=52B |
| 图2 S | 三输入12+snapshot4+RX staging4+metadata24=44B |
| 图2 FIFO/总计 | 四端点各128B，总608B |

这是该静态分配策略下的峰值保留容量，scratch无有效值期间也占槽。各区域生存期/元数据字数见README，不能只算两个状态向量而漏proposal/input/control。R=8/51B、S=43B、M=51B、V=63B等不足反例被拒绝；FIFO独立，不当作额外RAM。

## 实际执行、失败与验收入口

首轮实际执行在`evidence/run01/`，Python为本机3.13.5（Anaconda打包），未安装依赖。下列命令按顺序执行，退出码0：

```powershell
python -B scripts/check_project.py
python -B -m unittest discover -s project/analysis/block_v2_offline -v
python -B -m unittest discover -s project/analysis/llm_resources -v
```

新业务 **32项通过**，原估算器 **31项本次重跑通过**。两图CLI各执行两次，科学JSON字节一致且与手写expected逐字段吻合。`git diff --check`退出0；fixture、expected、旧估算器/快照及来源副本SHA前后不变。额外新文件空白检查弥补未跟踪文件不进入普通git diff的限制。最终范围检查只允许本目录、字段表、架构入口、本人进度和本交接；不更新docs/STATUS全项目阶段。

负例首轮实际CLI：缺K组退出2，错误`[-2,4]` expected退出2，原stderr分别为`ERROR: missing K group: exactly 2 required`和`ERROR: expected mismatch at $.rq_codes[1]: actual=3, expected=4`。unittest另验证重复组/unit/dtype/shape、容量、提前RQ、owner/版本/epoch、失败泄漏、INT16溢出、重哈希checkpoint篡改、输入被改且另造expected、输出覆盖保护。所有负例只改临时副本，不重写fixture。无业务测试失败被隐去；线上读取失败照原状记录。未执行项目如下，不以合成通过代替：

- SSH/SCP/Slurm/任何服务器命令、EDA/RTL/物理/PPA、完整模型推理、权重/大型归档下载：本次禁止，未执行。
- 真实rescale/epoch变化、完整conv/history、完整整数真实算术/应用质量、全码域宽度/ALIGN_REDUCE、任意调度/死锁：不在两图实现范围，未执行。
- 新GitHub Issue/PR/标签/评论/Projects变更、push/merge：禁止，未执行。线上head差异未核验。

最终完整回执生成命令（输出目录全新，旧run01保留）：

```powershell
python -B project/analysis/block_v2_offline/validate_delivery.py --output-dir project/analysis/block_v2_offline/evidence/run02
```

最终JSON含实际argv/退出码/数量/stdout-stderr摘要、源commit逐文件SHA、旧估算器与fixture前后SHA、局部未提交成果SHA、允许范围和最终工作区快照。它不声称自己已绑定本地未创建的commit；不对自身产生递归hash。

## Issue #63 衔接与恢复后事项

本批只提供字段建议、两个合成输入/预期输出、拒绝语义及离线验证器。用户提供的已知边界是Issue #63部分源码仍在服务器、未发布成果commit；本次没有取得或重写该通用适配器。线上最新发布状态因读取失败仍待核。

后续处理人待指定，顺序为：先用YUZE-LU核GitHub身份/适用规则及PR73/Issue63最新head和成果commit；记录相对固定88e9c4b的差异，保留本批基准。适配器负责人发布可读小源码/机器schema后，再把本表的unit/组证书/生命周期/事务字段接入其正式版本，保留两个fixture作为最小独立验收。混合scale/guard域和通用宽位必须另加真实证书，不能只把新字段填到v1。

**仅在服务器恢复且另获运行授权后**才需要执行：在全新目录核适配器和真实源SHA，接入真实图/张量/生命周期，验证全history/checkpoint、合法rescale和多代状态，校准宽算术/SFU/ROM/真实bank端口及同函数服务；随后由物理任务提供实例/冻结底座/限定层/技术via/RC/STA资格。不要重写旧实验或借用其他成员作业；本批不启动这些动作。

协作回执：负责人/本地进度目录为YUZE-LU；本次认证查询未成功，不冒称已在线核身份。登记沿用旧交接management-hub PR5 pending，当前线上状态unverified；本地无config/board.json，有status-mapping配置，实际看板/条目unverified、同步pending，未申请额外权限。审查人待指定，Issue/PR/看板未更新，不标done；本地交付完成与未来线上登记/审查是不同事实。

## 2026-10-25 用户授权发布追加节

用户要求“总结一下，PR”，随后明确“就是要用huangpingyang04-lgtm这个成员身份”。本次发布据此使用该成员，保留原始离线交付和固定来源。Git credential-manager github list列出该登录、现有Git作者为该成员，浏览器GitHub用户导航也读回该账号。未改全局凭据、作者或其他成员已有进度；此前本批尚未提交的YUZE-LU进度新增段转移至实际发布成员，不改其原有内容。

2026-10-25已实际执行`git ls-remote --heads origin main task/48-int8-resource-estimator codex/block-v2-offline-prep`：main为`0cc36f3238c7084d7126d94c314fe7d8bf0f9c5d`，估算器分支为固定基线`b06d85a801a87c07f9745ccae6950dc7e4cbd0d2`，本批远端分支尚不存在。针对main会重复带入PR50的17个既有文件，故本次Draft PR使用`task/48-int8-resource-estimator`作base；PR50合并后再考虑改base为main，不把依赖成果混成本批实现。

本批无新Issue，PR说明使用Refs #63作为部分接续，不宣称完成/关闭适配器任务。审查人待指定，不自动合并。项目登记/Projects仍pending/unverified，缺少board配置/连接器Projects能力的事项原样交接，不因上传PR改成synced/done。PR总结与发布前新证据放在`project/analysis/block_v2_offline/evidence/`；后续回执记录实际commit/PR URL及读回状态。

发布前`run03-pr-preflight`中管理结构、新32测试、旧31回归及两图重复重放均通过，但`git diff --check`退出2、范围检查发现YUZE-LU文件多出一个空行，因此整体回执为false，原样保留。经归一化换行后逐字节确认正文与基线完全一致，仅为移除本批新增进度段时留下的行尾/CRLF差异；已恢复其基线原字节，不改其他成员内容。补充目录级`.gitattributes`，使固定fixtures、来源和旧回执在Windows/Linux checkout时不被行尾转换破坏SHA。修复后的完整检查另存全新run04，不覆盖失败记录。

发布事实：2026-10-25 00:19（Asia/Shanghai），[Draft PR #78](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/78)已创建并读回`open/draft=true`、作者`huangpingyang04-lgtm`、base=`task/48-int8-resource-estimator`@b06d85a。实现提交`3b1fc28fb6b733e0bcf3decc0aae20ba21196f1c`由Git HTTPS实际推送；后续文档回执提交独立追加，最终HEAD以PR读回为准，不把旧run01/run02改写成发布后绑定。

连接器因Unknown tool不可用，浏览器焦点变化后停止桌面输入；启动浏览器进程的命令曾被自动审批以blocked by policy拒绝，未重复该启动命令。最终通过Git标准凭据管理器在进程内认证GitHub API，先GET /user确认`huangpingyang04-lgtm`/239819021，再核仓库push权限true、无重复PR及base/head SHA，才POST创建Draft。凭据没有写入文件、回执或输出。API另读回PR50 open/unmerged/head=b06d85a，Issue63 open/status:blocked/负责人本人；保持Issue63状态不变，不更改Projects或合并PR。

run04实际完整成功；暂存时Git把原CRLF的不可改证据判作行尾空白，故仅对原字节来源/证据声明标准`cr-at-eol`，仍保留blank-at-eol/blank-at-eof/space-before-tab检查。之后`git diff --cached --check`退出0，10份固定fixture/来源文件的Git索引字节与工作文件逐一相同，112文件/422733B且范围无越界。业务实现/fixture未为发布而改写。
