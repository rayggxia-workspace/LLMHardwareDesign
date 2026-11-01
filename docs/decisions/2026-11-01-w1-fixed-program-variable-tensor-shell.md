# W1以固定程序/可变tensor完成首个岛壳切片（候选）

Issue151/PR152；状态：有限RTL实测，外部审查待完成。

固定DOT8地址/形状/程序，新增8字128bit输入及真实写ACK完整门，替换literal S_INIT为INPUT_CHECK。唯一S helper同时服务入口与RUN，保持一个在途事务，输出经T真实release后完成。busy覆盖frame接受至完成消费；hard reset/prestart abort/RUN abort/已有DONE四类行为明确。

新增控制与适配位于wrapper及本地ROM，不改变七叶或旧P2，也不制造独立bridge物理宏。先证明原生数据接入和生命周期，再扩展各端点/一般跨岛；runtime数据装载不等于启动程序加载，所有有源能力须预制。

真实P2回归19与最终W1 28检查通过，编译失败/弱DONE计数版本保留。完整W1、六profile/大shape、MEM/NUM、无reset排空、物理准入尚未完成；不以小核通过缩减原P2门或声明完整大Block完成。

依据：[实现报告](../W1_MINIMAL_ISLAND_IMPLEMENTATION.md)、[验证范围](../W1_MINIMAL_ISLAND_VERIFICATION.md)、[代理独立审阅](../W1_MINIMAL_ISLAND_REVIEW.md)。
