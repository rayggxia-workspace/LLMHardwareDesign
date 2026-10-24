# Issue66：消费者scale与连续整数状态交接

2026-10-24 Asia/Shanghai；仓库https://github.com/rayggxia-workspace/LLMHardwareDesign；[Issue66](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/66)/[PR67](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/67)。负责人Liangruizhi/182389313/2663955430@qq.com。身份、协作Skill1.0.0及成员Issue55/63范围已核，未借用其他GitHub身份。

## 分支与源码

根工作树D:/Projects/LLMHardwareDesign-scale-state，task/66-scale-state，base PR65/task/64-block-v2@ec3008c665709fa3126d55719ad084d33af44428。consumer/state子模块分别在独立-66-consumer/-66-state工作树实现，根整合/调度/交付；未覆盖其他工作区。运行源commit按[索引](../../project/experiments/scale_state/results/issue-66/index.json)与work66/phase*-binding.json：capture38bd260、consumer/conv bad673e、native R29bee17、coupled79b6035、256步a1aea81、整数norm首版07fd9c8/新版9dcac84、norm独立接收0ff0123、归档a0b1d46。它们均是原Git历史，不能用最后文档commit代替。最后交付commit读PR67 head；未提交变更以恢复时git status为准，本交接不假定以后无人改文件。

## 已执行与数据

[报告](../experiments/issue-66-scale-state.md)/[v2第8/9节](../BLOCK_PARTITION_V2.md)：完整H2560 down→residual→input RMS→next16/8192，8出口profile数值/整数norm；真实非零初态连续R8profile、conv4、coupled2；旧32/1及256/1诊断各48。科学双轮、不同目录；90059–90082全部COMPLETED0:0，lrz-i66-*，node13/c96。全部主receiver及真实重写SHA负例通过，扩展独立核仅接收前固定3个完整256见证；其余长条件二轮SHA，不能称全48独立数学重算。小精选实际在本机独立重放2R+2consumer，输入完整H但next只16，整数norm另以服务器全8receiver验收。

服务器根/public/home/yuzelu/RuizhiLiang/issue66-scale-state-20261024。原Issue61模型与原捕获只读、无新下载/Phi调优/他人作业中断。完整delivery01/full-results01.zip5,207,960,397B，SHA cf07db65cb9207bd1aea0efd50b2338fa535edee6f2cae760a116df912dfb548；小精选19,581,351B，SHA 36791d8b553490c914fc720df31abc179bb1442c2ca0c5a93645c139ab6bca0b，正式results/issue-66。manifest及源码/日志在完整包和work66，按模块README安全接收/验证。大ZIP未进仓库/未落C盘；临时D:/Projects/Codex/issue66-scale-state-20261024仅保留仍需的输入/回执/脚本。

## 科学限制与恢复的第一步

先重新核AGENTS/Skill/Issue66/PR67、最新成员Issue55/63及其PR/交接，git status/worktree与服务器squeue/sacct；核索引和独立receiver。已完成90059–90082无需再启动；原launch脚本refuse overwrite，只供复查。

然后按新任务Issue/独立分支冻结两个合同：①V16KiB/1RW下完整H scale scan、gamma、norm、新A8的流式/两遍读及近M/共享服务；②R range guard、重定标epoch或合法fallback，与V16/S-shadow/预检查原位候选提交。相关宽乘/sqrt/div需RTL/有限端口校准，之后才公平比较R独立/共享V。

当前S32短误差低但同范围长窗Sat184/193，不能称普遍无溢出；D31消除近1舍入却不证明必须；conv clip和FP SiLU/QK L2norm/GatedRMS/gates尚在。整数norm不覆盖所有norm，所报单口beats/32sqrt/64div迭代不等于目标周期。全模型质量、目标RTL/EDA/布线/时序、PPA、整图收益、Phi独立泛化未执行；处理人Liangruizhi后续任务，物理集成沿Issue55/63实际负责人，不自行接管。准备失败保留，未删sat数据或修改scale掩盖失败。

## 协作未完成项

成果任务分支/PR交付，审查人待指定，未自审/合并，Issue in_review非done。登记management-hub PR5 pending；无board.json及可用Projects字段能力，看板unverified、同步pending，待管理员配置/核卡并读回。恢复必须以远端最新PRhead/Issue标签为准，不把本文件描述当远端设置生效证明。
