# S 改为每个 Block 单独仲裁：服务器结果

2026-11-03，Asia/Shanghai。实施[Issue177](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/177)，依据[设计文档PR176](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/176)。执行账号huangpingyang04-lgtm；基线main `4b1df2c7`，最终测试源码 `8b92b67ea88dc651a151b3f265e72d97487545fc`。

## 结果

新增Block-local S已完成服务器RTL验证。每个Block有独立普通口轮转仲裁、命令/owner保持及真实返回；P另有本地普通/宽读交替选择。原16KiB存储和feeder源码未改。一个Block停止接收返回时，其余Block继续完成自身请求。接口、客户分组和物理状态归属见[规格](../BLOCK_LOCAL_S.md)。

| 实际检查 | 结果 |
| --- | --- |
| 最终Slurm96410 | node27/debug/4CPU，COMPLETED 0:0，10秒 |
| 实际工具 | Verilator5.042；Yosys0.63，git70a11c6bf；工具和可执行文件SHA见原始结果 |
| 集成RTL lint | PASS，完整命令和输出见lint.log |
| 层级/存储检查 | 9个独立S、9个仲裁器、3个feeder、36个128×256bit bank，共144KiB工作payload；feeder小队列另计 |
| 仲裁器综合 | CLIENTS=1/4/5均完成综合、ABC逻辑映射和check -assert；不是目标库PPA或物理签核 |
| RTL回归 | 3种初态×3种子＝9/9 PASS，合计12,676,350次断言检查；每组7个阶段，共63个阶段完成记录 |
| 源绑定 | 8份Git原始输入上传前/服务器执行前后一致；当前提交同8份输入一致；两份旧存储/feeder与基线逐字节一致 |
| 本地实收 | 5轮80份原件共1,574,128字节，服务器SHA、下载归档成员和本地落盘SHA一致 |

每种seed在0/1/随机初态下的复位后输出一致。这是三种初始化覆盖，不能把重复结果当成不同的随机向量集合。

| 种子 | 每初态检查数 | 每初态周期 | 每初态请求/响应 | 三初态 |
| --- | ---: | ---: | ---: | --- |
| 177 | 1,408,366 | 24,396 | 66,726 / 66,724 | 全过 |
| 1001 | 1,408,723 | 24,401 | 66,782 / 66,780 | 全过 |
| 9001 | 1,408,361 | 24,395 | 66,723 / 66,721 | 全过 |

每组两笔请求由定向reset取消：一笔仅进入命令寄存器、一笔已写入但返回被背压。因此响应比接收少2是预期取消，不是漏返回。每组实际消费351个A包和63个B包；未用期望值替代真实握手。

## 验证了哪些行为

1. 九个真实S的全部1024个字地址写后读回；同地址跨Block使用不同数据，检查存储隔离。
2. 本块全部客户持续争用，按轮转完成；每客户获得服务，完成次数差不超过1。
3. P0响应长期背压，600周期内其他八块继续完成超过1000笔响应；同块不覆盖owner。
4. 随机请求/读写/返回背压，独立记分板逐次检查数据及写入确认；请求进入寄存器后源可继续变化。
5. 三个真实feeder，覆盖rows1/5/8、tiles1/4、A/B宽格式、B复用、标签/字序和A/B输出保持；普通口同时有请求。
6. feeder的A/B连续100周期不接收时，每个P的普通口仍至少接受10笔事务，随后feeder继续完成；done不得早于实际A/B消费。
7. 本块reset取消未写请求、取消已写请求的未消费返回、保留已写RAM、清旧feeder事务；复位后正常重入。其他Block独立继续执行。

原始[最终results.json](../../work/huangpingyang04-lgtm/177/evidence/job-96410/result-r01/results.json)绑定命令、工具、源、每组日志及摘要。[接收索引](../../work/huangpingyang04-lgtm/177/evidence/remote-index.json)保存所有五轮的实际作业终态及原件SHA。

## 失败及修复没有覆盖

| 作业 | 真实结果 | 后续处理 |
| --- | --- | --- |
| 96402 | FAILED，结构审计把旧feeder的512×2队列当成payload bank | 按明确名称/尺寸分别校验payload与三类旧队列，没有放宽36个payload bank门槛 |
| 96403 | 本人取消；持久yosys-abc管道等待，output.blif已生成但父进程没有返回 | 核本人UID/任务路径后取消；后续以同一ABC二进制经批处理-exe接口执行，映射及check保留 |
| 96404 | FAILED，C++驱动把Verilator标量端口按数组访问，未进入RTL测试 | 区分整型端口和VlWide端口，修复编译 |
| 96407 | FAILED；全0初态三组通过，全1/随机六组在cycle0发现reset期间done_valid可见 | 在新增包装屏蔽reset期间的feeder完成信号，旧feeder源码不改 |
| 96410 | 最终9组全部通过 | 采用上述修复，重新完成综合/映射/完整RTL回归 |

ABC的自定义执行接口见[Yosys官方说明](https://yosyshq.readthedocs.io/projects/yosys/en/latest/cmd/abc.html)。本次只是改变调用方式，未跳过ABC，未更改工具、映射脚本的门集合或硬件测试阈值。过程原件和被取消轮次保持其真实失败/取消身份。

## 通过范围

本轮交付可综合局部S包装和九实例集成验证。各块客户端是协议peer，没有执行完整计算宏、母控、网络或三个LLM。测试池每块16KiB是为了隔离仲裁变量，不是PR176中P.S32KiB的模型容量承诺。

未执行新宏P&R、300MHz、物理网表功能/LEC、M11/M12接入、目标库面积/功耗、完整模型质量。旧六叶物理资格保持原范围；新增包装不能继承组合资格。后续先审查，再将局部S接入完整局控/RX/TX并开展相应物理验证。
