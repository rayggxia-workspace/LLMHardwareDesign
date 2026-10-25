# Issue93 流式 gamma 交接

- 仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign；[Issue93](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/93)，负责人Liangruizhi。
- 分支`task/93-gamma-stream`，本机`D:/Projects/LLMHardwareDesign-gamma-stream`，临时`D:/Projects/Codex/gamma-stream-20261025-01`。已合入92最终6a106885祖先；不改85工作区。
- 当前交付由主会话统一push/PR；本分支尚未push/开PR，Issue在线仍in_progress，尚未验收/合并，不能done。management-hub登记PR5 pending，board.json未配置/实际Projects缺read:project，状态unverified同步pending；处理人管理员或待指定。
- 真实服务器仅`/public/home/yuzelu/RuizhiLiang/issue93-gamma-stream-20261025`、`lrz-i93-*`。无新增模型/其它机器，原84及61数据只读；所有正式运行已结束，恢复前再次盘点本人和成员作业。

## 可复用源码/命令

norm93.sv SHA `a42bb0f74a097eb14297820eaca6fe14350f233139d47153eb20dd47218aea5d`，chain93.sv SHA `39f03a636376b81668ec480b8356916e5c0e97b949e526990cd46a78541ee4c9`；RTL自2dc00e2未变。正式driver/build03与rtl-s003/s103冻结于cc8f5c2；严格receiver+cost02冻结phase7@5895c7a（完整commit在binding）。后续报告与字节接收提交不改变这些实验源。

服务器Python `/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python`；容器`orfs-26Q1-repacked.sif`、Verilator5.042、现有Yosys/Nangate45。实际完整argv/Slurm/source绑定见work93最终execution和selected内execution02。重跑从README复制命令到新的own输出，不能覆写。原输入input02绑定84原payload及61Gemma捕获（含gamma=1+raw原实现SHA），不在PC打开实际张量计算。

正式run：build03/rtl-s003/rtl-s103；最终严格接收receipt-s005/receipt-s105；资源map-b001 chain93与map-b101 chain85；成本cost02。每路51记录（48正确、1预期零分母、2错误gamma数值拒绝），实际功能链和控制恢复见报告。成本不称同外存I/O加速或PPA。

## 最终字节回执

服务器delivery02/full-results.zip：78,633,323B，276成员，SHA `0d64f2a9c0814fb6401e2de2274129e48982ddf9b4f77eae87db2d0d7780ab64`；独立全包PASS。

仓库results/issue-93/final/selected.zip：200,022B，88成员，SHA `4883d7d43faa966af7fa7b0baecc083dcfa5cc2b2e5d1680080da054824c78b4`；独立本机字节PASS。index SHA `2b9d44202bc20036e6afc2fc211a6ec2426bfe634ef0a20d877d5b4516d4d8c1`；7phase108原Git源逐字节PASS，6错误包/源/schema负例全部拒绝。

cost02 SHA `249757b86326f9cb85ff1737eb9bc823b9f5c04f45d29dccd551260e094924eb`；receipt-s005 SHA `d41300241996d27e0b36941fb5c711e5f7e4ffc88b5944fe8a4d293bcdd1d4dd`；receipt-s105 SHA `90d51dde489f8e569e041490eb8571235e61ac000599501abe9df60e181ce1a7`。

初包/cost01保留审计：错误是把每个128bit bridge beat记成4B，已独立改为16B；RTL、整数结果、周期、面积不受影响。使用final目录，不使用初cost01 wire_bytes结论。

## 下一步/阻塞

本轮已完成容量/功能/有费逻辑候选及根审阅追加的文件级语义负例。真实复制正式run并修改输出码/global_den、重写所有artifact SHA后，由冻结phase7完整receiver main分别因独立输出不符和全行sum/den不符退出1；不是hash失败。Slurm90920通过，完整变异文件及stderr保留。

1. Issue97复用norm93 direct接口，先完成专用SiLU→全K δ/A8→residentM→norm；512B frame为预留，不是已集成V；新V/IO/地址搬迁必须单独计费。
2. Issue98对实际93/97网表继续物理资格；不得继承88/86，也不能把RTL输出epoch赋值当门级FF注入。
3. H2560完整M、H1536独立norm、同外存入口resident预取、任意队列重排/CDC、目标SRAM/LUT/工艺、完整A/R/D以及制造前端点/金属定制仍未验收，分别由后续Issue与成员55/63接续；无原则性用户阻塞。
4. 根会话交付前核身份Liangruizhi/id182389313、origin、base及文件范围，push任务分支开/更PR、Issue同步/读回；不能自行合并。

恢复第一步：读Issue93/97/98与最新PR及成员进度，核server final/cost02、receiver与SHA；如只是继续97集成无需为文档合并重跑未变RTL。两项补充语义负例与归档均已通过；根会话可正式PR交付。

## 文件级语义负例补充包

源工具phase8@8017ebe调用不变phase7 receiver；服务器semantic-negative01及semantic-delivery01。完整补充11,221,672B/145成员，SHA `72986069253b1147048fa9b2b26e67fdc8a2695b6a7ac0907937c9ae438408a3`；精选37,566B/32成员，SHA `8fe1d4a065eddaafef4f5b71d1af130a5ec66bd2f867704e54d33aa403649647`，仓库`results/issue-93/semantic-supplement`。index SHA `2759f504c032240b42818adb50449471776859ade6641dbc8f0253ad845ce07a`；数学拒绝回执 SHA `b1fadead7213fc3ec30036294230084474bbaec7e10fb3a6e8bb64e64eaafab4`。

独立全包/精选字节通过，8phase112原Git源通过（包含主包7phase108，不相加冒充220个不同源）。两次完整receiver main返回1，错误分别是`independent full row integer output`、`one entireH sum/den`；不会产生假PASS receipt。所有作业最终状态见work93/slurm-final.txt，失败和取消均有原因，未遗留运行任务。


发布回执（2026-10-25）：[PR100](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/100)已上传；Issue93为in_review，待独立审查合并，未done。远端读回58dc6278623d779b548d2b664aabb10a49762c35的报告/最终索引/cost02/语义负例回执与原Git blob逐字节相同，见work93/remote-readback.json。登记PR5 pending；board配置与read:project缺项，状态unverified/同步pending，管理员/审查人待指定。当前仍继续97/98/99，不把本任务完成等同Block库全部完成。
