# Issue238：M 长K候选，尚非可部署硬件

独立实验；基于PR235的诊断工具，未替换 `project/rtl/block_v2/block_v2_m.sv`。
模块仍命名 `block_v2_m`，只能单独编译本目录候选，不能与原模块同时编译。

基线驻留S8 K32/N8每16拍接收一条Execute，64个乘法器只有4拍在发射乘法，
其余排空、缩放和提交开销难以由DP实例绑定消除。详见[Issue234预算](../../../work/YUZE-LU/234/linear-capacity-result-002.json)。

## 候选接口

旧op10保留K32、8行、S8/S16及原描述符。新增op13仅允许B1单行、K1–256：

| 字段 | op13 含义 |
|---|---|
| cmd_index[5] | 操作数bank；低5位必须0 |
| cmd_data[1:0]/[2] | A/B S16标志、清除原S64结果，与旧op10相同 |
| cmd_data[3] | 必须0 |
| cmd_data[7:4]/[11:8] | 最后K片有效元素1–8、输出列1–8 |
| cmd_data[17:12] | K8片数1–32 |
| cmd_data[21:18] | 行数必须1；更高位必须0 |

A复用现有存储：长K片t以`a_row=t/4, a_tile=t%4`装载，执行时按一条长向量读取。
**B的tile口从2位增至5位，增加3个输入端点；两bank B存储合计从1KiB增至8KiB。**
这不是免费改动，当前仍为寄存器数组。额外面积、接入/布线、电气/时序及Sfeeder/局控
适配均未验收。控制服务不能把这个候选当原硬宏直接调用。

备选是保留短操作数bank并连续供数/累加，减少存储增长；尚未实现。
两种方向应按面积、端点、背压及真实服务吞吐择优，不能只挑驻留数值。

## 已运行及未运行

候选RTL在三初态下各160形状（四格式、双bank、K及尾部/列边界）S64正确，
拒绝多行长K。1024条驻留K256/N8 S8命令实测接收间隔44拍；约为基线同等计算量的2.91倍。
旧8192形状×三初态的数值及周期表与原网表基线逐字节一致。

这些是**RTL微测试**，没有完整局控程序、Sfeeder、DMA、整模型质量/SystemC或物理结果。
K256可以降低发令摊销，但不能把44拍直接当整模型decode时间或宣称10 token/s达标。
旧格式、完整S64累加与最后舍入需保留；新增故障/背压/清bank/跨格式压力及综合/P&R仍待补齐。

重跑（原始操作数及基线周期表由PR235归档提供）：

```bash
export VERILATOR_ROOT=/path/to/verilator/share/verilator
export PATH=/path/to/verilator/bin:$PATH
bash project/experiments/m_streaming/probe.sh "$PWD" /fresh/output /path/m-tile-0.tsv /path/profile-1-143.jsonl
```

首次手动实验后，统一脚本已从全新目录完整重跑，通过相同检查；只用一核构建和顺序运行。
实际冻结源码、构建、日志和散列见[工作记录](../../../work/YUZE-LU/238/README.md)。


全位宽补测（formats-005）：同一未改RTL，三初态各1024驻留命令；K256/N8的S8×S8为44拍，S16×S8及S8×S16为108拍，S16×S16为300拍。旧模型使用S32×S16时还需多分量调用，不能用S8的44拍替代它。004的测试watchdog设为100拍/命令而超时，保留失败；005只放大watchdog，功能/结果判据不变。见work/YUZE-LU/238/formats-result-005.json；本次复用003已冻结的同RTL编译模型，仅重编驱动，不冒充新一轮P&R或完整统一脚本。
