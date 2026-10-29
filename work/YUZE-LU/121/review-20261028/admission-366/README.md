# 366 准入配置

Refs #121 / PR #122。只选择R344/345/346与V363/364/365六个已有队列，24份manifest/queue/dispatcher/dependency SHA已与服务器和已提交源绑定。配置提交4034242、控制源423c006；实际PID2777187，08:19:47及08:20:48 UTC两轮UID/cmdline/来源SHA核验见capture-start/index.json及launch-readback.json。控制正负检查通过。

保持原dispatcher独占提交、reservation/unknown保护和本Issue8 allocation上限。仅替换360轻量登录控制，原357/311及所有EDA不取消；仅未分配358/359允许退休。c96六个16CPU独立槽即完补位，真实依赖/内存才降并发，1.2预测与16GiB guard/liveRSS保持。
