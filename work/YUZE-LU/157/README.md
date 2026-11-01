
## 2026-11-01T23:44:30+08:00：小容量R专项续办

按用户新指令聚焦256/512/1024，2048作对照。[专项报告](SMALL_CAPACITY_REVIEW.md)逐条核对16组实际运行及完整S/DDR/控制成本；复现脚本project/experiments/r_architecture/small_capacity_review.py。1024作为Qwen128×8条带的主候选，256为面积下界，512保留折中；Falcon256×8条带按2048维度对照，未新增完整模型执行。四容量最大扇出都在rd_index[2]，不能仅看role下降。

A0/94708与A1/94726本轮仍RUNNING，未产生最终receipt，见SMALL_CAPACITY_PHYSICAL_SNAPSHOT.json。B256现有setup/hold失败；512/1024尚无最终物理资格。暂不新增物理候选，优先收齐已有作业；如继续一项代表实验，建议B1024紧凑布局且先审查M10接点容量。未取消、修改其他任务。
# Issue157：R 架构探索与端到端代价分析

生成：2026-11-01T22:44:56+08:00。独立研究分支task/157-r-architecture；不修改PR144/Issue143。先读FINAL_RECOMMENDATION.md，然后FUNCTIONAL_VALIDATION.md、FANOUT_ROOT_CAUSE.md、BOTTLENECK_ANALYSIS.md和PHYSICAL_RESULTS.md。

交付：ARCHITECTURES.md、FUNCTIONAL_VALIDATION.md、SYNTHESIS_RESULTS.csv、SYSTEM_AREA_RESULTS.csv、SYSTEMC_RESULTS.csv、BOTTLENECK_ANALYSIS.md、PARETO_ANALYSIS.md、FINAL_RECOMMENDATION.md；另有HIGH_FANOUT_TOP20.csv、PARETO_RESULTS.csv、SYSTEM_COST_MODEL.md及物理证据。大ODB/映射/可执行文件保存在远程不纳入Git；收集manifest逐文件SHA，原始文件位置和映射SHA可复核。

冻结版本见BASELINE.json/EXTRA_INPUTS.json及inputs。R SHA4032c5edcbee9d38e1a51dd9f9c533e414d5263dd2440d7104a1688e73ca382d；A1 d826dc5f562a55ceb1fce6dbbb04e3f21b4ceafe00187607413cbeed97b28b96；最终A2h 3f45ac421563fe7360862bb0056266089895c55e2579c012f92bf2af71e4358e。历史map4df8e33ce3a23efc2c3f1e08f1cae2c474e73391522349cf7fde5b3b8fcfd865与新A0map15d180a81662f629bbecfc756084e0eb7112624bd140d2672820e2ef241d11df不同，不能替换配对。

固定环境：Yosys0.68+post、Nangate45 typical Liberty SHA8d540a4d4cf6d09d27c87ad067857a9c0c2eeb023ab7a56e058cd3113db4e9b1，容器/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif SHA49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a；Verilator5.042在容器内运行，SystemC3.0.1共享库SHA930767c0ec7a203c38552201a22fa2a27a319c47d4d9019096457a674bca0848。命令及Slurm allocation记录在每attempt/BUNDLE/FILES.sha256和部署回执。

远程根/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture。每个attempt为不可变源归档；不得用当前checkout冒充先前实验源。复现时新建目录并提取对应source.tar，sha256sum --check FILES.sha256，然后在相同容器和Slurm allocation下执行该attempt的sbatch脚本。完整RTL测试/形式证明在标准单元映射前；A1入口partition_run.py，最终A2h入口grouped_local.py（RTL回归/降低）及grouped_prove.py（全状态关系重证/映射）；系统入口cosim_sweep.py，E补充e_followup.py；C-N入口native.sbatch及native_followup.sbatch（新增硬件测试→映射→联合模型）；物理入口physical.py --candidate A0/A1/B256（仅在满足证明/筛选门后）。

本地重新生成统计：python project/experiments/r_architecture/final_report.py。完整数值输入在attempt003/results/corpus（63份固定seed、逐文件SHA），真实维度strip在027/corpus。所有最终周期以实际RTL/SystemC联合运行015/022/027/038/045/053/055/056为主，早期003/005快速模型只保留历史，不混入最终CSV。

调度采用节点内动态独立任务队列，编译每项16线程，形式证明封闭锥并行48项，联合仿真最多96个单核任务；依赖未满足不占满全节点盲目启动P&R。最多两个新物理候选B256和A1，A0为匹配基线控制。仅取消本任务被替代的proof作业，回执记录精确jobid，未取消其它作业。management-hub/Projects看板登记待管理员完成，不影响实验文件复核。
