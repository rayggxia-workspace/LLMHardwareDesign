# P私有S扩容研究（Issue246）

冻结PR243@42fb01d4b77f3dbe2041617bfc801b9fc02e8c11的P/DMA模型，15个功能依赖SHA见source.json；旧实验/生产RTL保持。用户要求量化43KiB单行A能否通过扩大S提速，本研究沿本会话task/242-r-load-bounds/PR243交付，Issue246独立跟踪。

仅P容量由16KiB扫描32/43/48/64/128KiB，2P、1U、U的16KiB、17.1GB/s、M算术、300MHz参考时钟和64B端口宽保持。原observe与已测adaptive组合分别对照，不将前轮调度收益冒充容量收益。64KiB额外考察P端口每64B占用由1变2周期的敏感性，U不变；这是端口吞吐成本，不是假定SRAM只增加1拍流水读延迟。不是同面积比较，未实装大容量S，不转移原RTL/物理/功耗/真实模型质量资格。

generate.py只对SHA锁定源生成隔离模型、matrix/detail头及审计器；16KiB必须与前轮完整case JSON完全一致（仅新增容量/端口字段除外）。审计保留流量/形状/阶段/ACK及U固定容量检查，P容量按声明检查并每case注入超容量负例。大容量下独立验证FFN下投影A每P/每层仅读一次。运行前冻结8份输入SHA（四trace、m-profile、原manifest/基线、前轮实际result.json）。

```bash
# 仅在获授权Slurm资源和固定SystemC环境、新结果目录执行
python3 -B project/experiments/sram_capacity_study/run.py --inputs FROZEN_INPUTS --out NEW_RESULTS
```

job.sh申请c64/c96、4核、UNLIMITED，工具来自授权安装/容器；实际作业/结果与SHA在Issue246回执及正式报告中记录。容量满足全A不代表保持原K；48KiB边界可能迫使K变小，必须一起检查命令数。生产S的地址/描述符/真实1RW仲裁及新叶宏时序另验。
