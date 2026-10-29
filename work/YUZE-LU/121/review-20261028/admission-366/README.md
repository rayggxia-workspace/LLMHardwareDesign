# 366 准入配置

Refs #121 / PR #122。只选择R344/345/346与V363/364/365六个已有队列，24份manifest/queue/dispatcher/dependency SHA已与服务器和已提交源绑定。配置提交时尚未部署，实际运行需后续launch/两轮读回。

保持原dispatcher独占提交、reservation/unknown保护和本Issue8 allocation上限。仅替换360轻量登录控制，原357/311及所有EDA不取消；仅未分配358/359允许退休。c96六个16CPU独立槽即完补位，真实依赖/内存才降并发，1.2预测与16GiB guard/liveRSS保持。
