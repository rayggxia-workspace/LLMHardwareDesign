# 360 准入配置

Refs #121 / PR #122。配置只选择既有344/345/346与357/358/359六队列。staging-verification.json核验24份服务器manifest/queue/原始提交器/依赖模块SHA与已提交源。此配置文件提交时尚未部署；部署证据另存，不把配置当成运行事实。

原dispatcher仍独占提交，保留本Issue最多8 allocation及reservation/unknown保护。替换对象只能是旧354轻量登录控制器；运行EDA正常完成，未分配351/352方可退休。节点内独立任务动态补位，单个原生步骤依赖不能强行并发。
