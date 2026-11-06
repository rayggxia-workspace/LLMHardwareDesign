# P16 原生服务双块试验

试验复用 [PR #190](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/190) 的 P16 RTL 和 [PR #195](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/195) 的原生服务与确认逻辑。输入清单锁定验收版 P4 SRAM 封装及相关叶宏。P16 源码逐文件对照验收快照，块的两个外部 SRAM 客户分别用于主机检查和链路传输。

试验使用同一时钟域的一个母控、两个局控和两个 P16。母控先 CALL P1，再 CALL P0。P1 局控发出 RESERVE 和 RECEIVE，P0 局控驱动装载、M 计算、G 门控和发送。M 的结果写入 P0.S[8]，G 从各自的输入地址读数，结果写入 P0.S[14]。固定链路读取 P0.S[14]，按预约地址写入 P1.S[20]，目的 SRAM 响应握手才释放源响应。这里单独验证 M 写回和 G 写回，跨块传输使用 G 结果。

局控通过 ENABLE_NATIVE_P16 参数选择试验配置，ABI 0x01790160、拓扑 0x01790161、容量 0x17630001。局控镜像限定为 v2、资源位 0、1 至 8 条执行描述符，object 和 transfer 表为空。L_EXEC 按索引选择描述符，L_WAIT 等待对应 token，程序字保持 64 bit。原生参数留在执行描述符内。母控与两个局控都通过配置端口加载、读回并部署镜像。

在获授权的服务器容器内运行，指定 PR195 验收包的 staged 目录和 issue #155 对应的 SRAM bank 模型。脚本先验证全部输入，再运行正常、双向背压和确认被阻塞时的同域复位重装。

```bash
NATIVE_STAGE=/path/to/verified/staged \
SRAM_BANK=/path/to/s_sram_256x128_freepdk45.v \
VERILATOR=verilator bash project/control_p16_native_v1/run.sh /path/to/results
```

验收限于固定单向、单个 128 bit 在途字和试验复位。跨任务 ACK 身份、生产 M11/M12、CDC、复位认证和组合 300 MHz 时序需要使用生产端点分别验证。[验证索引](../../work/Melodydt/179/p16-native-validation.json)
