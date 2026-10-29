# 既有六队列的准入检查

V330已ready而本任务8个allocation仍在运行，R311及后续队列还依赖真实结果。采用轻量登录控制进程每60秒调用既有提交器，目标固定为311/312/313/330/331/332。它解决节点释放后的准入等待，不增加宏、候选、产品或新的节点内调度器。

提交权威仍是原dispatch.py：Issue共享锁、先写SUBMITTING reservation、pending/unknown计入8上限。控制预检查只匹配本Issue记录作业ID，同账号无关工作不占本任务名额。任何旧提交记录均不重投；观察超时不推断终态；不取消Slurm任务。六份manifest/queue/dispatcher/dependency以SHA固定。计算仍全部在Slurm内，节点内6×16及内存规则保持。

实际335源0029a9b、配置acbd45e，本地/服务器控制检查通过，含未知/既往终态不重投、PENDING、同账号无关作业及格式错误负例。334原控制版本的过度计数负例与仅替换控制进程的回执保留，不改源或原物理结果。335两轮/proc/状态读回已验证，当前330因真实8allocation限制等待；这不构成物理或最终验收。

证据入口：work/YUZE-LU/121/review-20261028/admission-335；旧记录admission-334。后续先验证控制进程实际身份和status，再按真实V/R结果继续，不重复启动已有控制器或EDA。
