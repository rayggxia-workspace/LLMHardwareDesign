# Issue151 混合控制总方案交接

2026-11-03（Asia/Shanghai）；仓库rayggxia-workspace/LLMHardwareDesign，project_id=llm-hardware-design，负责人/认证Melodydt。复用Issue151、PR152、task/151-six-connection-study→task/143-seven-block-v2；本轮输入6ecc33a2b956cdce0f92d6b083d5905a541a1e81。实际新交付commit以PR头/在线回执核验，不能把输入SHA写成已含本更新。

## 用户确认目标与权威入口
[总方案v0.6](../HYBRID_METAL_CONTROL_PLAN.md)、[决策0009](../decisions/0009-hybrid-metal-control-product-graphs.md)。
冻结后仍可永久定制此前未列出的、在已声明功能/数值/shape/资源内的合法新图；成品不启动下载新控制程序。主候选为金属粗任务表＋固定共同母顺序器/资源管理＋预制TX/RX/真实stored ACK/局部令牌握手＋固定岛内程序。不能回退为只支持六固定链/八个预存完整程序，也不承诺未知算子/无限图。

## 当前真实进展与未完成
本轮只改文档及静态资料，没有新RTL/服务器/仿真。旧54runtime、锁和24GAP保持。QUALITY95979已完成28官方参考/8行56RTL/8actualSHA；完整trained整数AF、新代表性数据与产品阈值仍未接受。L5共同端点/母控、一般拓扑、D/H/X、MEM及M11/M12物理未验收。

## 目录和并行协作
本轮隔离API部分资料包位于C:/Users/Administrator/Documents/ChatGPT/课题研究 大模型硬件化/hybrid-plan-20261103-6ecc33a2/integrated，没有.git/HEAD/index/暂存；不是完整Git checkout。本地外层C目录的.git为另一空管理上下文，git.exe启动失败（系统DLL重定位）；不修改它或假装git status已成功。通过本人GitHub API继承固定树、只更改明确文档路径并使用expected_sha非force提交。
原D:/Study_material/Study_material/LLMHardwareDesign及quality-77b47e3既有工作包不覆盖。实施对话ID01a190bf-bf6e-7b10-9250-d896e081c770已确认本轮暂停共享文档/分支写入，待本交付后核新头接续；只有用户已明确授权的跨对话同步，不发送他人。

## 下一执行顺序
1. 从PR152最新头读本方案/Issue和本交接，更新自己的隔离包，先检查是否有别的更新；不得从旧API包覆盖新共享文档。
2. H1：固定图语法/节点边角色、同岛重入/分支/有初值循环、有限资源/控制表字段及错误拒绝；至少三种不同图的完整调度、生存期、程序和物理预算。当前主线L4质量门保持，H1是L5输入，不假称已实施L5。
3. 并行前置金属控制存储可行性：预制位单元/读出/译码/驱动、编码与读回、容量/landing/扇出、M11/M12和通孔的实际可布线性；普通ROM不自动可编程。
4. H2/H3再以同RTL仅换表/路线证明端点SACK与源保活、释放、错误/partial/reset、重入/fork/join/反馈；新仿真只用本人服务器Slurm/Verilator，按规则立即给出追踪回执。
5. 保留L4-QUALITY-AF：真实训练参数完整整数A→F误差、新数据/质量门；D/H/X/MEM/完整产品/物理各自退出。用统一资源条件对比模板、混合、纯令牌和其他路线，不能给无证据PPA结论。

## 同一交流PDF
用户要求每完成一步覆盖原PDF，不新建版本、不推Git、不发送他人：
D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/local-share-2026-11-02-v2/output/pdf/七宏功能岛方案交流_2026-11-02_更新版.pdf。
实施对话已按方案提交05bccbea5d7e7206154a85c5eb33a3b03a0933b9同名覆盖原PDF：12页、437710B，SHA256 ca87b5f4ee43be38d9905df1619f85a1df68fe916c7ef8cf73f27d8dcc96c2ca。全页视觉/文字检查和14处链接检查通过，9个唯一固定commit目标读回确认，无阻断问题；本会话另行只读核对实际文件SHA相同。PDF与生成/QA记录仅本地，无PDF上传/对外发送、无远端代码或服务器改动。本轮目标与commit已由实施对话接收，下一按H1图/资源/控制存储规格接续，L4-QUALITY-AF门保留。

## 交付与协作状态
本地文档/静态检查、远端上传和读回分别记入work/Melodydt/151/hybrid-control/的回执。PR保持开放未合并，Issue为实际阶段而非done；外部审查人和优先级待指定。登记management-hub PR5既有pending证据复用，看板因无board.json/Projects item工具保持unverified/同步pending，处理人待指定，不写成已同步或权限已拒绝。本轮无在跑作业/自动监测。
