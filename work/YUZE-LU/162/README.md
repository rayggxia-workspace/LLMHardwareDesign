# Issue162：可编程控制、搬运与块旁适配

任务：https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/162

本次先在既有 PR146 加入 `project/systemc/include/control`、测试和 `CONTROL.md`；后续从六宏 main 建独立 RTL/物理 PR，不能把本次 SystemC 测试称为最终交付。

本地原HEAD：2eb72686feb4421c6772ee0fcf60fd7677017959。SystemC3.0.1/GCC10.3/CMake3.27，UBSan与-Werror，原524425断言、新723检查、4/4 CTest、管理检查通过。实测记录另附 `systemc-test.log` 和输入SHA；未运行服务器EDA。

登记复用management-hub PR5 pending；无config/board.json，看板unverified/同步pending，处理人待指定。Issue162保持in_progress；本模型及新RTL待用户审查，不自行合并。
