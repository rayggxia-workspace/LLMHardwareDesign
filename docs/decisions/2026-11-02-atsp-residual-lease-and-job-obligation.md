# ATSP固定残差lease与任务完成义务

Issue151/PR152，Melodydt；2026-11-02。RTL源d1efc16b、95277有限验证已形成待审证据，完整A/产品/物理未接收。

先用同一T串行承担原X和最终输出两个事务。原X交错布局匹配两行Wo组的E消费顺序；真实S258写ACK是E发射门，最后E目的ACK及响应是T释放门，不添加私有残差缓存或第二T。原S区可以真实覆写，避免容量分析依赖不存在的旧数据。

独立job admission即形成终态义务，含输入/prestart取消。X与Wo检查generation/index/last；坏拍不发S请求，错误返回held DONE而不静默接入下一job。已接受的输出前缀和S写不回滚，硬reset取消任务。该局部同钟域协调reset不代替跨岛/MEM任意late response排空。

Wo明确外部切口，使用合成整数验证传输/生命周期/饱和加法；不将H1024维度等同完整Attention或训练质量。下一实现一KV两Q保持真实H/D，数值质量与后端预算保持独立门。
