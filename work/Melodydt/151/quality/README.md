# L4-QUALITY首切片：官方框架参考与W8有限闭环

Issue151/PR152；Melodydt；输入77b47e38。仅本目录新数值/检查脚本与固定合同，旧54份RTL/TB/include不改。固定官方revision和旧4prefix作回归，比较官方eager FP32与独立C++的28个stage/case，并对baseline和同Fin10 W8各4个末token执行原qnum RTL，共8fixture×7检查、8份9MiB实际流SHA。

所有误差容差/输入/候选在运行前由quality-contract.json冻结，不根据新结果调整阈值。旧eval已被观察，不再当未见holdout；产品阈值、代表性语料、完整整数A→F质量及旧24GAP保留。数值或RTL尚未运行，实际源commit/命令/结果以后续实跑回执为准。Python依赖wheel仅本地与本人服务器，Git留版本/大小/SHA索引。

交流PDF每步完成后同名覆盖原本地文件，不推Git、不发送他人。正式报告与进度通过原任务分支/PR交付，不自合并。
