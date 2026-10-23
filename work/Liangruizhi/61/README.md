# Issue61辅助记录

负责人Liangruizhi；[Issue61](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/61)/[PR62](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/62)。正式代码/数据在project/experiments/server_models，正式报告在docs/experiments/issue-61-server-models.md。

model-acceptance.json为逐模型/阶段验收表；pr36-intake.json保留原69文件的两类字节核对；bundle-intake01.json验证精选包及27原commit源文件；local-review01.json独立离线重放精选GQA/整数。batch-summary-final.json是生产端结构化汇总，不能独自替代接收证据。negative-receipt.json为真实数据改写后独立拒绝的两个负例。

execution-ledger.tsv覆盖首批至90043，final-execution-ledger.log补90044–90047；bounds-binding02、cost-binding01和submit回执分别绑定4ca7214/8211803源码；bounds-readback02核完整PV32与原有指标一致。最终管理/业务检查另见validation.json及checks.log。

完整capture/编码/strict数据按正式index.json读取服务器大包；仓库精选包不含全部浮点校准输入。Phi封存不用于调参。所有失败和superseded目录在服务器保留；无需重复启动已完成作业。看板unverified/同步pending，登记pending，PR未合并不done。
