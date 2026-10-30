# 五宏接续入口：602

Refs #121 / PR #122。目标仍是M/V/R/S/T各一个基础宏的300MHz最终M1–M10布局布线与真实M10接口，五宏最终未齐。M/S/T保持独立接收；不重跑、不做裕量版、阵列或产品。无整模型速度/整数质量/制造资格。

## 当前主线

- V生产dea3c22b，576八项检查、577五项有限S/V、修helper后587两项占用实际PASS。576/587/589全部51 RTL/C++精确一致。唯一原生588/93781/node16已完成synth/floorplan/place，23:22 CST实际CTS hold修复；589最终全部门/六文件/完整几何、590逐端口/有限RC均已stage，591按真实依赖接续。
- R404/93555/node21原GRT extra40/100继续；405/406等待。不能因慢或静默取消/重启EDA。
- 591轻量控制器PID1087781仍活跃，配置9462704b及实际UID/代码已核验。本Issue≤8 allocations包含旧/PENDING/UNKNOWN，不是账号总限额；c96六个16CPU独立槽即完即补，真实依赖或测量内存限制时才少跑，不用空任务占位。
- 两旧92045/92046自然运行；其他hpy/其他Issue任务不操作。旧553/93764仍DRC/严格LEC运行；物理13setup失败保持。当前工具只看实际所需任务，不反复轮询封存终态。

## 本次新增实证

- 595预算采用577五项测量、43规范Git输入，14报告源SHA复核。8模型80有限分析候选与551成本完全相同，周期保持；不是额外物理版本或整模型结果。旧551保留。
- 594/93787旧523批量几何，39处via替换后全片native445→406、0新增。597保存14原始/6稳定/316源Git与远端SHA。原ODB/DEF保持，其他正常NETS为token规范化SHA比较，不声称原始字节相同。
- 598/93794自然完成，**实际组合**上述39via与568的232填角后重跑native445→172；相对原始/406基线均0新增。601保存13原始/5稳定/317源Git和远端SHA。557412普通网络数、非RECT header/路径及232 RECT增量精确核对。不是独立计数相加。
- 以上仅旧523派生副本诊断，172项仍拒收。尚无几何端点连通、RCX/STA、完整GDS、最终功能/LEC或交付资格，不替换当前588。下一步若继续方法，应先读601真实剩余报告定位，再形成有依据的有限修复，不能把旧坐标直接用于新V。
- 600保存旧552最终网表三初态功能，每种574942检查/425971拍PASS；27原始、8大文件实际SHA、311源Git及相同最终源receipt绑定。setup失败不被功能PASS抵消，资格不转移588。

## 本地与线上

工作树`D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-121-block-v1`；branch task/121-block-v1-twelve-layer，账号YUZE-LU。主仓库不动。AGENTS/协作Skill/REMOTE_RULES已读，无新subagent授权。

- `.local/issue121/peek588active.py`只读V/R阶段；`peek591live.py`实际控制器；`peek553only.py`只看旧553依赖。
- 596/597/599/600/601 collector与record597/600/601已执行，禁止再次运行覆盖封存。602审计追加后应为448近期原始Git-byte比较、199当前证据SHA。
- source598.tar源6a9e9748，SHAff3b356ac62993862bf843f6f3762fb51cdd318030d8701f7f16a7e44bc6d1a3，317文件/318成员、2,426,880B。首次本地stage早读未完成tar失败在远端创建前停止；归档终态后远端只提交一次93794，599记录。
- `.local/issue121/publish_exact_parallel.py BASE`只上传Git对象，运行期间HEAD必须固定到终态；之后connector expected_sha CAS移动ref。原始文件先`.gitattributes -text -whitespace`再stage并核对Git字节。
- 当前规格`docs/BLOCK_V1_REVIEW_CONTRACT.md`已修复过时535/537入口、周期与预算，执行选择588/589/590保持。旧100MHz正文只作历史。

PR122保持OPEN/DRAFT，Issue121 OPEN/in_progress；不自审/合并/关闭。管理中心PR5登记pending，看板因无config/board.json而unverified/同步pending，管理员/审查人待指定。线上Issue/PR各自ad3c2b3历史后缀不同，更新必须分别保留。当前HEAD的CI只按实际读回，不能用旧39f32da4成功代替。
