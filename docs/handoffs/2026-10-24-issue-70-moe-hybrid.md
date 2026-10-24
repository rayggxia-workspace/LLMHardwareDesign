# Issue70交接：Granite/Falcon最小集

仓库https://github.com/rayggxia-workspace/LLMHardwareDesign；负责人Liangruizhi（182389313，2663955430@qq.com）；Issue70/PR71，branch task/70-moe-hybrid，base PR69@ab2edaa005d4a249fdc5cfc6b68ed33e812f26e2。根D:/Projects/LLMHardwareDesign-moe-hybrid；并行子worktree -70-granite/-70-falcon/-70-audit，各独立分支，已cherry-pick，不覆盖他人成果。最终交付commit见PR head；实际运行commit以results/issue-70/index.json的11阶段绑定为准（capture ac9d3f3、numeric4482a65、transportafa3bad/4482a65、接收a7b0fde、归档1a47498、配对f0b1f6b）。本交接提交后预期工作区干净，以实际git status核验。

授权CPU服务器/public/home/yuzelu/RuizhiLiang/issue70-moe-hybrid-20261024，node13，Slurm90152–90179。首轮外网下载失败及元数据路径错误、旧接收FP32 scale oracle错误均保留；五个afterok旧依赖取消替换，无他人作业中断。90161科学失败未抹掉；90164及90166–90179实际COMPLETED。无本批仍运行的作业。完整模型原BF16与固定revision/官方SHA在models-relay，只读复用，不重下。本机D盘只下载/校验中转，所有模型/数值/端口计算在服务器；Phi封存，成员55/63未接管。

完整包delivery01/full-results.zip，966025542B，SHA256 4c221db36ee3f756a284cda25dfabd6d9376ca4d7b95341c97d53a2be4d74f8b；包内完整捕获/负例/phase1..10源码，不含权重。phase11双轮SHA补充单列。仓库selected.zip为3137707B/43成员，SHA06e584ee8129e12e3a5eb53060c673c957b60560ad642e4c29d036f201984a05，非独立完整重放包。完整每file字节/SHA、实际命令/模型验收与小精选索引见results/issue-70/index.json、work/Liangruizhi/70/receipts与slurm。

实际验证：check_project、80边界测试、git diff --check通过；服务器32dot/32RQ/4merge、128profile-layer路由归因及23Falcon原生门、完整FP64 head/2304投影dot/编码、24COPY配置双轮和真实重写SHA负例均独立接收。Granite仍为FAIL/PARTIAL；Falcon S16/S32各4sat、FP64更新桥；COPY-only非RTL/PPA或E2E。原报告差错见FALCON_ERRATA.md，修正源码未重写历史NPZ。

恢复第一步：以Liangruizhi认证重新读最新AGENTS/Skill、Issue70/PR71及成员55/63进展，核review/merge和数据SHA，再决定新Issue范围。真正后续为Granite高精度路由合同/参数因式分解驻留、Falcon因果range与完整W8消费者链、真实端点/布局资格；不自动扩大模型或启动其他机器。处理人Liangruizhi，审查人待指定。登记management-hub PR5 pending；无board.json/Projects能力，看板unverified/同步pending需管理员确认配置/权限；不能称远端看板已完成。PR未审查合并不标done。
