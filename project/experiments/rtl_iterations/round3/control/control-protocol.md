# R3 control probe：逐边接口

仅镜像有限控制状态，不计算矩阵、RNE或饱和值。对齐冻结wrapper SHA `783089199218a48c3c6cfe78a67509dba1ee95ea23858f7c7e79737e7911510c`。未本地编译/仿真。

服务器编译：

```sh
g++ -std=c++17 -O2 -Wall -Wextra -Werror control_probe.cpp -o control_probe
./control_probe 1 < inputs.txt > observed.txt
```

每行20个无符号十进制数，循环必须连续，可在同一流中含reset：

```text
cycle reset cmd_valid ctx tag ki total_k k n shift first last a_byte b_byte out_byte read_ready read_rsp_valid write_ready write_ack_valid done_ready
```

输入必须为RTL端口实际值（例如ctx只有3bit，不允许用超宽值再假设硬件拒绝）。在posedge、NBA之前观察组合信号，随后本工具更新状态；实际bench也应在同一边界记录。

输出每行前缀`CONTROL`，后续27个整数为：

```text
cycle cmd_ready read_valid read_addr64 read_rsp_take write_valid write_addr16 write_ack_take done_valid done_ctx done_tag done_next_k done_last done_error leaf_valid leaf_ready leaf_fire leaf_ctx leaf_end_k leaf_sequence commit_valid commit_ctx commit_end_k final_capture reservation_count read_count live_buffers
```

建议所有输出完整比较；若实际bench没有记录无效payload的陈旧metadata，只能明确对valid字段门控比较对应payload，不能跳过有效请求的地址/tag/nextK。核心数值和`done_data/saturated`由独立RTL大整数oracle验证，不能拿本工具替代。

`finite_control.hpp`不含S延迟常量：读ready/response、写ready/ACK、done_ready全部来自真实记录。SystemC接入时需要另一个有明确校准来源的S模型产生这些输入。仅该控制probe通过，不等于完整模型已获通过，也不证明真实DDR/局控联合实现。
