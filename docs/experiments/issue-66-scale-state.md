# Issue66：完整消费者链scale与连续R整数化

2026-10-24 Asia/Shanghai；负责人Liangruizhi；Issue66；基于PR65@ec3008c的新任务，当前实现/运行中。用户授权服务器并行关键分叉；不新增模型下载/不接管其他成员Issue55/63，Phi封存。

## 已核与输入分叉

旧Q35 down capture为全部K9216但仅16输出，不够验证hidden2560的RMSNorm。真实消费者是layer3完整down→加post_attention_layernorm输入(residual)→layer4.input_layernorm(有效gamma=1+weight,eps1e-6)→layer4.linear_attn.in_proj_qkv；本轮下一投影取前16输出，不能称完整8192/GDN验证。norm会重新建立激活格式，因此不能机械把ACT16乘法3基础积应用到其后的A8投影，需核实际算子链。

旧PR36真实R窗口有6段256步及6邻接1步，层0/14/30、head0/31；只支持同窗口前8/32，不拼成跨window连续任务，且未有conv输入/history。新capture复用同固定Qwen3.5-4B checkpoint，cal/eval不同文本，各prefix128+cached32；layer0完整Vhead0/1共享K0，K/V128、33实际R/conv边界，conv保留原4槽，不能把另一个3历史布局当原字节数。R内核整数、非线性/归一化浮点桥、存储/端口条件分别验收。

## 当前实际执行

本人服务器c96/node13，模型与旧捕获只读。90059 legacy导出COMPLETED0:0，22秒，源码aa7afb9；原输入SHA 049c1cf4e81044fdc740dd1e65701a86293f31293d4b0ee2c554daecfef4e91a，原SHA绑定后导出NPZ8912088B/SHA facb5a23145501a093deee792a3b87fa1a21bafb0566645ef9209ffeae088a5f。源码38bd260冻结的新capture90060已实际RUNNING24CPU。最终是否通过、数值主测及独立接收尚未回填，不以编码/脚本/提交替代实验。

准备阶段CRLF/连接超时失败保存，未启动数值；UTF8 bytes/shlex.quote修复，新phase1b/phase2b不覆盖旧目录。后续数值两分支完成并冻结后并行Slurm；失败不删除，方案只依实际结果收敛。登记pending、看板unverified/同步pending，待审查合并不done。
