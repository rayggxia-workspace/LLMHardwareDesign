# Issue151 L4-A-TSP残差路径验证工具

负责人Melodydt，PR152；研究输入7aba36a0，main六叶来源4b1df2c7。本目录为真实H1024/Sq2残差保存切片的合成整数golden、冻结TB合同、服务器运行器和后续证据位置。

本轮新增block_w4_atsp_top与独立TB，使用真实S/T/E和既有S helper/E controller；Wo是外部S16Fin10切口，没有实施M、Attention、通用L5或物理岛。源冻结提交不表示测试已经通过，实际job/结果只以服务器源绑定run-receipt及正式报告为准。

- build_atsp_vectors.py / fixture-contract.json：三个完整4096B fixture，直接signed16饱和add；T/Wo交错顺序单独约定，不复刻控制FSM。--output NEW_DIR --self-check --source-commit FULL_SHA生成；--check只读核对已有生成目录。
- atsp-tb-contract.json：具体TB SHA、严格CASE顺序、真实接受输入和输出dump映射、编译源与适用边界。
- run_atsp_job.py：只在本人Slurm zenanyan-atsp/8CPU运行，固定输入SHA、生成golden、编译/运行Verilator、检查CASE和真实dump长度/SHA，保存命令、工具、警告及终态。
- evidence/：仿真后实收的轻量日志/回执/源清单/输出索引；构建和生成二进制留本人服务器新任务目录，不上传Git。

全部RTL仿真仅服务器Verilator。服务器仅yuzelu@10.129.166.172，本人/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/atsp-7aba36a-20261102，独立input-rNN/runs/rNN，禁止覆盖既有尝试。提交前固定source commit；提交后立即公布job、目录、命令与追踪信息。遵守仓库REMOTE_RULES与rayggxia-project-collab1.0.0。
