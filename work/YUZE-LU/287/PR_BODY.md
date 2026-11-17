Refs #287。

main 合格 C V3/U39 v02 在独立负载下通过，并不证明能驱动实际长线。本轮在远程 debug node27 分配16核、每次7场景并发，将#206/#216真实RC样本接入原生128位收发口，完成200/300MHz共14场景。0.336mm样本本夹具通过；1.304–4.320mm所选样本有输出电容/slew超限，300MHz最差setup为负。200MHz正setup不能覆盖电气失败；超载数字只作诊断。

完整范围、原件索引及复跑入口：work/YUZE-LU/287/README.md。原计划outgoing/incoming接口到U延后接回切口，保留诊断结果但不作为完整路径。最终为native_tx/rx电气回放，起止为内部寄存器，不声明C响应包可直接作为U命令或存储数据功能闭环。静止邻线、理想父层共钟、原子宏Liberty保留；非多PVT/动态串扰签核。

验证：输入网表/ODB/SPEF与main回执SHA一致；119509独立基线和119515联合运行COMPLETED0:0；3584行路径、128边界驱动标注检查通过；181个归档成员回收SHA核验；管理检查、Python编译、git diff --check通过。失败运行和被拒绝的旧接口场景单列。

规则rayggxia-project-collab1.0.0，项目llm-hardware-design，执行YUZE-LU。登记management-hub PR5仍open/unmerged，pending；无config/board.json，Projects unverified/同步pending，待维护者处理。独立审查人待指定，Draft，不自合并、不关闭任务。下一步为原存储数据接口切口接回验证、驱动优化和新几何联合提取。
