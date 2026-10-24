# 两种新增架构的最小实验

Issue70：Granite小MoE和Falcon-H1并行Attention/Mamba2。[冻结决策与最小集](../../../docs/experiments/issue-70-moe-hybrid.md)先于模型执行。

- download.py 只下载用户授权的两模型，固定官方API revision与LFS/Git blob；读取原safetensors dtype，下载不等于推理或整数通过。
- [GRANITE.md](GRANITE.md)：完整层MoE捕获、W8A8 router/专家、真实重新路由和共同单位加权归约，FP桥单列。
- [FALCON.md](FALCON.md)：完整混合层连续状态、独立FP64递推、整数状态存储诊断、完整K代表投影及跨head gated RMSNorm。

先python -B scripts/check_project.py，再于已有NumPy环境执行python -B -m unittest discover -s project/experiments/architecture_extensions -p 'test_*.py'。临时文件与进程缓存只在D盘独立任务目录，所有实际模型/数值/服务走本人CPU服务器Slurm lrz-i70-*，输出拒覆写。没有GPU、完整应用质量或RTL/PPA声明。原始weights/大张量不进Git，实际接收、原FAIL/PARTIAL及[精选/SHA索引](results/issue-70/index.json)已保存；80项边界测试通过。完整来源须按phase胶囊复跑，当前修正后的源码不改写原数据。

Granite原chunk16失败见granite_diagnose.py及独立verify_diagnose.py；只有显式 --diagnostic-failed-chunk 且严格通过收窄条件可作局部PARTIAL_DIAGNOSTIC。receive.py --model transport --repeat 第二轮目录 提供COPY/端口独立接收，FP32/S16分列。原Falcon report精度字节勘误见FALCON_ERRATA.md。完整包/归档工具说明见work/Liangruizhi/70/COLLECT.md。
