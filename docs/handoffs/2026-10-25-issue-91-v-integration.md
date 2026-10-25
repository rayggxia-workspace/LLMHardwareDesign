# Issue91 V/S整合合同交接

- 仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign；Issue：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/91；负责人Liangruizhi。
- 分支`task/91-v-integration`；工作目录`D:/Projects/LLMHardwareDesign-v-integration`，基线`d60fac795ba6341df2e48804df564afd3e4e9818`。实际结构源`8fa5dde64dc26802087cd618d8a8d95bc8dd268a`；最终交付commit由根会话读本分支HEAD填写，不能将文档自引用的HEAD当实验源码。
- 临时目录`D:/Projects/Codex/v-integration-20261025-01`；没有创建服务器目录、连接其它机器或运行服务器作业。本轮纯结构工具获Issue91明确本机授权。
- GitHub实际认证`Liangruizhi`、ID182389313、origin目标和push权限已核验；只读回执`work/Liangruizhi/91/remote-readback.json`。没有借用成员账号。

## 已完成

1. `docs/V_S_INTEGRATION_CONTRACT_V1.md`：真实80/82/85库存、程序与LUT分开，地址/live-range/命令/scale/有限仲裁/错误合同，新增byte ALU/mux/控制成本与最小RTL实验。
2. `docs/BLOCK_LIBRARY_ACCEPTANCE.md`：M/V/A/R/S/D分层缺项，特别A/R宽格式不能免费借M8，16KiB S不是候选多bank，runtime cache不是金属定制。
3. `project/experiments/v_integration/`：4个符号trace/8个布局，独立receiver不导入生成器，23单元测试；交付负例拒绝四类实际改码/伪造。
4. `docs/experiments/issue-91-v-integration.md`和`docs/decisions/2026-10-25-v-s-gamma-streaming.md`：容量/事务计数及有理由的下一步选择。全部结果小于大文件阈值，仓库直接保存trace.gz及SHA，无权重或真实tensor。

结构report SHA-256：`145956d188d24b05b96fdd1c08008c3c5abc337c716e286ea9b0c1da898c1efc`。输入配置、18个原Git源、每条trace大小/SHA均在report；统一索引`project/experiments/v_integration/results/issue-91/index.json`。

## 实际验证与恢复命令

`work/Liangruizhi/91/execution.json`、check-*.log保存真实命令/exit0/时间及SHA。管理结构PASS；23业务检查PASS；正式输出与入仓副本两次独立接收PASS；负例删除gamma-release并重新签SHA仍拒绝，typed counters/sourceSHA/schema均拒绝。没有执行任何新真实数值、RTL、综合、STA、电气或物理验证。

恢复先核最新AGENTS/Issue91与88/92/PR89/90/成员55/63进度，再核本分支status与实验原源SHA。用现有Python、不安装工具：

```text
python -B scripts/check_project.py
python -B -m unittest discover -s project/experiments/v_integration -p "test_*.py" -v
python -B project/experiments/v_integration/verify.py --folder project/experiments/v_integration/results/issue-91 --out NEW_D_DISK_RECEIPT.json
python -B work/Liangruizhi/91/replay_negatives.py --source project/experiments/v_integration/results/issue-91 --out NEW_D_DISK_NEGATIVE_DIR
```

重新生成trace用原结构源8fa5dde的独立目录；直接用新HEAD生成会如实绑定新源，不能冒充原实验。PC仅结构/字节检查，实际张量或RTL仍仅本人服务器新任务目录。

## 未完成及下一步

- 根会话统一上传/PR/Issue状态：本分支本地完成，不自行push或创建PR。正式状态发布后应in_review，不关闭或done；项目全Block设计尚未完成。
- 根已建立[Issue93](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/93)（ready），待91交付及92控制源冻结后才启动。根只读指出旧61 Gemma capture有H2560 norm输入/输出及raw_weight可核，需服务器校验manifest/source SHA，Gemma有效gamma为1+raw_weight，epsilon1e-6对应Q24=17；本91未读数组/未宣称数值已核。
- 下一独立Issue先gamma streaming：H1536旧完整消费者回归 + H2560全行den、tile credit、异常/响应/旧epoch/恢复；H2560没有合法真实数据时明确用合成。继承92终止态修订后再跑新协议，继承88方法重新检查新netlist电气。
- 随后才做旧74真实SiLU→512粒度scale→8专家A8及RTL delta→M→norm闭包，不能喂旧host delta当完整scale传播。新增byte ALU/S8 mux/程序控制/LUT桥全部综合计费。
- source X/G initially external是本结构比较的共同初态，M已在S的X不能重复加载记益；流式对照必须另计可能的spill。
- 登记沿用management-hub PR5 pending；本工作树无config/board.json，Projects未核实/同步pending。根会话需读实际权限并补同步或留准确缺项；没有宣称看板已更新。审查人待指定；根的只读候选审阅不等于正式PR批准。
- 未改85工作区，未接管55/63；本地提交仅91文件及本人进度/架构入口，最终无未提交改动后交根接收。
