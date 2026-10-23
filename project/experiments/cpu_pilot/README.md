# CPU迁移pilot（Issue53）

只复用已核SHA的Qwen3-0.6B固定权重；不下载大模型，不替代师兄已交付Qwen证据。
Python3.12独立venv、CPU torch2.10.0+cpu、transformers4.57.6；依赖wheel逐项SHA与离线安装报告另存。
服务器默认python3.6不代表没有其他Python：本轮已找到既有3.11/3.12，并仅在本人目录安装Python库。

`prepare.py --model-dir <已有权重> --out <新D盘目录>`验证原8个模型文件后生成528个固定teacher-forced token。
`pilot.py --model-dir <model> --inputs <inputs.json> --binding <binding.json> --out <新目录>
--threads 8 --dtype float32`在Slurm分配内运行，线程不得超配额或实际affinity。
binding须提供源码SHA/commit与token SHA。job.sh冻结32CPU/20分钟，六条件依次执行并与其他独立任务并行，
避免同时占用CPU的模型进程干扰线程伸缩对比。申请核数不是整节点独占；记录真实affinity和进程lifetime RSS。

每条件核128+8的full/cached与32token分块，逐层K/V和logits比较。FP32门为atol/rtol各1e-4；
BF16只使用事前2%相对RMSE工程pilot门，并同时报告严格FP32标准、最大误差和top1，不称应用质量接受。
性能另执行无观察器128/512 prefill、固定16token decode，各一轮热身/三轮样本；加载、校验和正确性不计入吞吐。
这是eager注意力的CPU软件试跑，不是最佳CPU后端/96核性能、不证明AMX内核、不表示INT8或目标芯片加速。

主测其他架构、长序列、原生递推/窗口以及实际量化后端均需各自支持与正确性核验，不能由本pilot一并验收。
数值输入/状态采集、整数oracle可迁CPU；GPU显存、吞吐和GPU真实内核留显卡，GPU 4bit格式不假定能直接在CPU执行。
结果通知门继续保留：兄方数值包未经用户完成通知不下载整合，已读Issue/PR进度用于避重。
