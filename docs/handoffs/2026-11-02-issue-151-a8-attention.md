# Issue151：A8 Attention切片交接

- 仓库：https://github.com/rayggxia-workspace/LLMHardwareDesign；Issue151/PR152；负责人Melodydt。远端task/151-six-connection-study，base task/143-seven-block-v2；输入parent1d722477564e14f7dc93e39ce8e28b8e2d150cb0；新交付commit读PR152最新回执，不编造。
- 本地：D:/Study_material/Study_material/LLMHardwareDesign/work/Melodydt/151/a8-1d72247/integrated，独立API资料包，无.git/HEAD/暂存，不是完整checkout；正式变更清单见上传manifest/最终PR回执。根管理参考副本、旧工作包、ref-project与他人目录未改。包外draft/sourcearchive/认证公钥文件不上传。
- 本次新增：block_w4_a8_top及独立TB、整数参考/合同、服务器runner/生成器、正式docs/W4_A8_*和八主线进度。32份继承SV/SVH不变。当前仍主线四，完整A/F/L4未退出，L5–L8未开始；外存继续保留灵活性。
- 实际服务器：/public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/a8-1d72247-20261102。input-r01..r04为不同不可覆盖输入，runs/r04为authoritative编译/log/results，slurm为作业日志，exports/c02/text-evidence.tar.gz是55份文本证据归档，SHA见a8-execution-index。编译二进制保留服务器，无波形生成。
- 真正执行：job95116 zenanyan-a8-all/c64/node1/单task8CPU/1m51/COMPLETED0:0；Verilator5.042，N29/F825/A826，共80项完整CASE、3compile/3sim均0。A8正常23S(19W4R)/M10/N6/load2/T1+release；全局reset/abort差额不伪称守恒。独立Python与管理/静态检查见a8-checks及review。
- 失败保留：95111入口/usr/bin/singularity缺失，95112仅环境probe，95114错误VERILATOR_ROOT，95115默认warning fatal。shared runtime真实路径/public/software/singularity-ce-4.3.4/bin/singularity；最终不手设ROOT，容器HOME/tmp/cache在本人目录。当前98条warning全保留，功能通过非lint clean。
- 服务器登录：通过用户提供公钥核验和电脑既有SSH身份，不新增认证/不读私钥；独立SSH/Slurm不依赖Moba窗口。不要上传连接凭据或认证辅助材料。所有未来RTL仿真/回归继续服务器Verilator，不回退本地ModelSim。
- 在线交付：按PR最新回执分别核验文件上传、Issue状态、审查/合并、登记和看板。登记management-hub PR5本轮读回open/unmerged→pending；无board.json/Projects item工具，看板unverified、同步pending、处理人待指定；没有证据认定权限拒绝。外部审查人待指定，PR未合并不done。
- 下一步负责人Melodydt：继续L4，按仓库样本明确Attention变体与数值/layout合同，补QKV、所需Norm/RoPE/GQA/mask、输出门/投影/残差，再做真实shape容量映射；完整MEM/产品/PPA另验。恢复第一步先核最新Issue151正文及PR152头、a8-index/execution-index/此交接，确认源SHA与实际服务器终态，再选定下一有界范围，不擅自跳L5或覆盖旧run。
