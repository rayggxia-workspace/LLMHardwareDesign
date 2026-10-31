# 实际准入部署证据

Issue121 / PR122。源与配置来自6c8ae6b6fdb02646226f43e2c3890e67b1baa385的规范Git字节。

- PID4181231；配置a05bdefc9946c5ffc251406071425b4823d22079ac5c21bb2403ee2cc3d87216。
- 七队列404/405/406/462/463/464/465远端manifest/queue及dispatcher/dependency哈希与归档Git核验。
- launch-readback保留正反控制和实际首轮状态；capture-start保留实际UID、cmdline、start ticks及两轮独立读回。
- staged-readback保存464/465实际远端三文件身份守卫、dry dispatch无分配及426退休回执。只终止登录机轻量控制器，未取消/重启EDA；425未曾分配。
- 运行源/目录不可变，Windows工作树CRLF不能替代规范Git源；部署使用Git blob字节。

真实前置与内存约束之外按6×16动态补位，最大8个本Issue allocations。R404与V463已实际运行；其余最终验收/接口待真实前置。M/S/T不重跑；V/R最终未齐。
