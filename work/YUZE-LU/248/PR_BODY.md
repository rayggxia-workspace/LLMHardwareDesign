## 问题与结果

原方案的矩阵服务受普通S中转、端口/格式转换和DDR入口约束。本PR从PR243@9d987151冻结版本另开研究分支，完成有限权重直供、W8A8/A16、带宽/资源消融、状态相关贪心/DP四轮实现与评估。

Qwen2.5-3B、36层、B1/context512 decode，原shared-S模型3.383963 token/s；同17.1GB/s/两P的权重直供为3.672688（+8.53%）。更高DDR/三P/条带化的最佳条件模型5.953188，未达10。这个+75.92%包含资源变化，不能记为算法收益。A16同资源5.798303，缓存DP5.799646；简单A8质量筛查不合格，暂不推荐替换主线M。

Refs #248；接续 #247 / PR #243。这是独立研究PR，base为peer分支task/242-r-load-bounds，审查本轮增量，不改写/合并peer分支。

## 修改范围

- 新增隔离研究目录 `project/experiments/stream_quant_synthesis/`：有限双B bank、K16×N8 W8A8/A16矩阵RTL、四路定点转换、真实checkpoint量化筛查、SystemC消融、共享前沿转移的贪心/DP和计划回放。
- 保留P/U/C/F/J控制分组、独立叶宏和16KiB S，生产RTL/旧验收产物不变。活动P数预算的变化与完整九组物理底座的面积区分，不把闲置宏从面积账上删掉。
- 同计划导出binding ID一致的研究IR/部分操作数端点需求；没有原生ISA/完整静态网/真实pin绑定，不冒充#180/#220完整部署。
- 新bank/转换/mux/DDR入口需新M1–M10有源实现；M11/M12仍只连接真实端点。

## 验证

- 管理结构：`python -B scripts/check_project.py` 通过；`git diff --check`通过。
- 正式SystemC：run12@a76a402589ea4a907084246f2e265a8f55de1385，Slurm101988，4CPU/8:25/COMPLETED0:0，65case通过；其中12次frozen/off完整旧RESULT精确一致。
- 输出标签修正：run13@cacf636ae8baa62c259ba8e26527caeaa0580380，Slurm101989，48秒/COMPLETED0:0；A0/A16两条路径完整RESULT除标签外精确一致。
- RTL：A8/A16各5782packet、44完整Dot、5782填充ACK，八上下文交错、全K极值、背压、非法命令和半包复位；转换输出S8/S16/S32各512独立有理数向量通过。EDA均在Slurm计算节点。
- 算法：190个独立RNE检查、小图4968路径穷举与DP最优估计一致。低带宽DP仅比贪心快约0.04%，且低于固定第一轮配方，无20%算法增益声明。
- 真实checkpoint：两条校准、四条独立prompt筛查，权重固定W8；A8存在严重logit偏差。A16仅通过小样本筛查，浮点非线性/KV，未做整数整机或困惑度验证。
- 离线：`python -B work/YUZE-LU/248/verify.py`通过，13个不可变run包/958成员逐项SHA核验，失败与退化结果原样保留。

## 风险、限制与后续

最高5.95为条件模型，完整原生整机token/s与J/token均为null。RTL两个K16 packet槽与计时模型两个K256 tile bank尚未做完整P/DMA周期校准；没有局控/母控全链路、完整整数生成、DDR PHY、综合/STA/P&R或新300MHz资格。S32同资源更快，当前不建议为吞吐采用新精度。先统一真实P/DMA/局控服务，再校准DP的S/队列/credit等待代价；新的有源硬件另PR物理验收。

## 文档与交接

- [x] 报告：`docs/experiments/issue-248-stream-quant-synthesis.md`；实际数字：`work/YUZE-LU/248/summary.json`；复跑/失败/证据：同目录README与13个包。
- [x] 更新架构命令、决策、本人进度与交接；没有提交凭据、无关数据或修改他人的工作树/作业。

## 提交回执

规则rayggxia-project-collab1.0.0；仓库rayggxia-workspace/LLMHardwareDesign，project_id llm-hardware-design；Issue248/负责人及认证身份YUZE-LU。成果为PR249，个人进度progress/YUZE-LU/STATUS.md。登记沿用management-hub PR5 pending；缺config/board.json与Projects能力，看板字段unverified、同步pending，管理员待指定，持久交接docs/handoffs/2026-11-10-issue-248-stream-quant.md。待指定独立审查人；Issue in_review、未合并、不标done。10token/s与20%纯算法收益未取得。
