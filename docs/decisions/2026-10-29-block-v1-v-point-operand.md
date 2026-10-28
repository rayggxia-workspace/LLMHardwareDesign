# V独立物理失败：逐元素操作数选择隔离

Refs #121 / PR #122。281独立物理门实际失败：9397 setup、4 hold、12 cap、3 slew，最差setup −2.166809797ns；270原生通过不作为接受依据。最差路径真实映射为offset[1]→output_mem[6][16]，报告与失败原文见work/YUZE-LU/121/review-20261028/v-physical-rejection-0532。

逐元素total使用与计算阶段共享的mul_b，后者在C_MUL/N_LOW/N_HIGH等阶段可以来自回放地址。这使与P_WRITE无关的地址选择逻辑进入组合结构；不能只用功能上的phase互斥给STA加false path。

修订显式计算point_b（broadcast scalar / pair-swapped b / b），逐元素total只引用它；共享乘法阵列继续使用phase选择后的mul_b。P_WRITE时原mul_b的表达式正好等于point_b，命令、位宽、RNE/饱和、延迟、启动间隔、有限容量均不改变。无额外物理版本、无约束放宽。先289新源数值/映射/端口吞吐，再据新映射证据推进fresh P&R；不能把旧270 CTS或281功能/LEC转给新源。

此改动只针对已定位的组合连接问题，尚不能声称已解决全部setup/hold/电气违规。若后续仍有真实长路径，继续按新证据拆分；新增寄存器或周期必须更新规范、测试与资源计价。

281已开始的DRC/功能/后继formal继续正常收尾；其V交付/几何自然BLOCKED。S/R不重复。原285/288只暂存从未分配，所选V281已被拒收，现显式retired.json退役，不能再由advance_ready提交；替代接口/RC队列须绑定修订V最终源，S/R可独立接续，M/T通过项不重跑。
