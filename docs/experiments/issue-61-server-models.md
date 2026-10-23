# Issue61：服务器补齐批次与证据接收

负责人 Liangruizhi；[Issue61](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/61) / [PR62](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/62)，task/61-server-models，独立工作目录 D:/Projects/LLMHardwareDesign-servermodels。用户最新授权本会话在既有CPU服务器承接兄方批次；旧等待/仅本机安排作为历史保留。本批不改变其他成员Issue32/55的归属和审查状态。

机器为c96分区，node13实际约503.5GiB内存，无GPU/GRES。只在本人 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023 执行lrz-* Slurm；不在登录节点加载模型。24+24CPU用于两个独立非性能采集作业；不把96核额度当96倍提速。

## 逐模型验收入口

完整状态、版本、证据和恢复步骤见 [model-acceptance.json](../../work/Liangruizhi/61/model-acceptance.json)。原Qwen2.5代表是 **Qwen/Qwen2.5-3B原始基座**，不是Instruct；修正原实验配置的简称，不改写生产方运行事实。

| 模型 | 当前实际状态 | 尚未通过的验收 |
| --- | --- | --- |
| Qwen2.5-3B | PR36已有GPU证据；CPU两轮1416 INT64 partial全等 | 全包接收/条件审计；确认完整GQA可复用范围 |
| Qwen3.5-4B | CPU两轮5376 partial全等；12 FP64递推窗口、6相邻状态对通过 | 全包审计/全局GQA覆盖；不能称全整数状态或重跑全部8192轨迹 |
| Gemma3-4B-it | 配置/原生后端预检通过；公开原BF16镜像传输中 | 权重实际SHA、全模型参考/窗口边界、真实采集、整数参考及成本 |
| Phi4-mini | 原生后端预检通过；公开BF16镜像传输中 | 权重SHA、采集与封存；冻结策略前不以其量化结果调划分 |
| Qwen3-0.6B / Llama3.2-1B | 既有小规模证据复用 | 本批不重复；原数值/硬件边界保留 |
| Gemma12B / Llama3.1-8B / R1蒸馏 | 条件跳过 | 只有最新任务明确要求且有未覆盖决策时新增 |

## 已执行与失败

源码a30e92cbbb60e3d0d93f3be01dafb2291d7d4cbe的89992/89993均COMPLETED0:0，分别23秒/4秒，是小张量复核耗时，不是模型推理速度。Qwen两模型6+6个调用均使用完整K分组、仅2行/4输出列。NumPy INT64检查部分和，FP32辅助缩放/求和再FP16与生产样本相等；不证明整数RQ。独立NumPy FP64递推的最坏relativeL2约6.55e-7，保存12窗口、6连续边界，不能推断未保存每个token都已重放。

回传31文件包21609B，SHA256 07655d8cec167cb0f37d2790e0ec5c3e7c7220ca6708c7f4526e032a25d009a6。本机D:/Projects/Codex/issue61-server-models-20261023/replay-return01.zip；正式接收审计补充中。

89995直接HF下载因服务器DNS失败，保留FAILED1:0；Gemma官方固定版本未认证返回401。用户授权查公开镜像后采用ModelScope LLM-Research镜像，按文件固定revision和官方Git/LFS双来源哈希验证，不借凭据、不代同意许可。传输只经本机内存转发至服务器，完整权重不落本机。收到字节和正式推理状态分别登记，不能从下载宣称INT8通过。

90002后端预检COMPLETED0:0，torch2.10.0+cpu/transformers4.57.6：Gemma8Q/4KV、head256、window1024、5局部+1全局；Phi24Q/8KV、head128、partial RoPE。只验证配置/tokenizer/原生类，尚未加载完整权重。当前正式采集协议与源码8a1fe4b已冻结，四项边界/整数测试及check_project通过，待权重校验后提交采集。

## 固定协议和边界

Gemma：校准128与独立评价文本；prefix128/1023/1024/1025/4096+decode32，chunk128，首局部/全局层完整2Q/1KV，保存实际cache而非每窗清零；KV逻辑量、底层storage、布局、有效长度分别记。Phi只采集128/1024+32完整3Q/1KV并封存。全部CPU FP32，原始权重仍BF16；不是独立FP32权重、GPU时间或W8A8速度。每次正式运行固定commit、实现SHA、输入token、配置和source-binding；失败保留采样，不后改阈值。真实INT8/INT32与FP32非线性/scale回退必须分别报告。

协作登记PR5 pending；看板未配置/工具缺失，状态unverified、同步pending，管理员/审查人待指定。PR62草稿未合并，Issue61 in_progress，不能称已验收。
