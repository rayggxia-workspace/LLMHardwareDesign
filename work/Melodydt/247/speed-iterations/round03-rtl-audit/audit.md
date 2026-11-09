# run20 独立原始证据审计

结论：PASS。源码 `a3149d69a23f52efb808dbbb46b5558dffce4df7`；Slurm 101872，COMPLETED 0:0。

主结果SHA `87842b59e42fb0773eedb82dce4981614432868fa12218c3aa15166b0b839eff`。流式核验447个已回收输出与22个payload源码成员；未复制327MiB原始材料，未执行EDA。

六次实际运行各66例，7458个有效packet、7638项检查和20个reset时点。完整47字段原始控制逐行投影核对并与实际server probe在有效字段上匹配；仅忽略首个reset边沿前未初始化payload。
独立重算serialized S96/RNE oracle；实际输入SRAM字、最终输出字与原始vendor日志逐字核对。S96内部数值未被control记录，其实际逐列断言通过依赖冻结bench和原始PASS证据，不能称control replay验证了数值。

| 配置 | K2048 ctx1 | K11008 ctx1 | K2048 ctx8 | K11008 ctx8 |
|---|---:|---:|---:|---:|
| BUF1 | 777 | 4137 | 6153 | 33033 |
| BUF2 | 396 | 2076 | 3098 | 16538 |

以上为首cmd接受至最后done消费的连续RTL程序周期，三seed一致；不能直接当旧K256模型费用。无人工hold的读/写请求→消费ACK均严格2拍。正常峰值不超过2个读metadata、8项completion和各自1/2 input buffer，压力例实际填满8票。
原S仍16KiB/4×1RW；额外buffer声明位数2158位=269.75B，wrapper479.5→749.25B。只是源码结构代理，未取得面积或300MHz资格。

实际内容审阅的文件及原SHA逐项列于audit.json；所有其他已回收results文件仅做流式SHA匹配。未回收object/binary仅有服务器清单，未冒称本地审核。
