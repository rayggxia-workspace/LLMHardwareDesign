# 16 KiB 局部 SRAM S

这套实现将 [#178 的局部仲裁](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/178)与 [#158 的四银行 OpenRAM 后端](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/158)接在同一个 16 KiB 叶宏内。

| 配置 | 参数 | 外框 µm | setup 裕量 ps | hold 裕量 ps | 完整 GDS DRC |
| --- | --- | ---: | ---: | ---: | ---: |
| P4 | 4 客户端，有 feeder | 1850 × 1850 | +18.735 | +21.339 | 0 |
| N4 | 4 客户端，无 feeder | 1160 × 1160 | +245.836 | +18.567 | 0 |
| N5 | 5 客户端，无 feeder | 1430 × 1430 | +182.921 | +26.648 | 0 |

通过范围为 Nangate45 M1–M10 独立叶宏、TT 1.1 V、25 °C、300 MHz。各版通过原生 DRC、完整原版 GDS DRC、四银行时钟周期与脉宽、信号与 PG 连通、电气、最终 ODB 网表三初态功能、四银行边界严格等价。P4 采用 30% 电容修复目标，终检使用原 Liberty 上限。银行时序沿用 #158 的晶体管原理图表征，银行内部连线寄生仍未提取。系统互联和层级时序另行验收。

[源码与六文件索引](../work/YUZE-LU/155/local-sram-main/index.json) · [P4 版图](../work/YUZE-LU/155/local-sram-main/p4/layout.png) · [N4 版图](../work/YUZE-LU/155/local-sram-main/n4/layout.png) · [N5 版图](../work/YUZE-LU/155/local-sram-main/n5/layout.png)

## RTL 接入

实例化 `block_local_s_macro`，设置 `USE_SRAM=1`，按表设置 `CLIENTS` 和 `WITH_FEEDER`。四个真实 256 × 128 bit SRAM 银行由 `block_feed_s16k_sram` 实例化，编译及综合分别使用源索引指定的模型与物理视图。默认 `USE_SRAM=0` 选择标准单元后端，既有 `block_feed_s_macro` 调用方继续使用基线实现。

普通接口每块只允许一笔在途。请求握手进入本地命令寄存器，写完成由实际 SRAM 响应确认。仲裁器保留 owner 至响应被消费。P4 的普通口和宽读在两路可服务时交替授权。复位清理排队的命令和响应，保留已写入 SRAM 的数据。

在 Linux/WSL 用 Verilator 5 和 #158 的原始生成银行模型复核九实例 RTL。两种存储后端各覆盖三初态与三个种子，真实模型的功能仿真周期为 10 ns。

```bash
bash project/experiments/block_local_s/check_backends.sh \
  /path/to/final-033/bank/s_sram_256x128_freepdk45.v /path/to/new-output
```
