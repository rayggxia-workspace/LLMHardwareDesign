# 当前源准入354

只将V白名单337/338/339换为350/351/352，R344/345/346保持。源5b659f1accdb97a5bebc175cd170a0ff90921193、配置8c450079bab46491db2a5f11eba1133113156b53；六队列24份SHA固定，本地/服务器控制正负检查通过。PID2486398及05:28:01/05:29:16 UTC两轮存活、UID/cmdline/源SHA核验见capture-start。

初次部署观察只等10秒，原dispatcher首轮实际超过该窗口；随后按原launch.json恢复同一PID读回，没有重启或重投。原过程已成功启动，实际350提交93210。只替换347登录控制进程；338/339核实无allocation才退休未来选择，原337/311和其他EDA均正常收尾。原347 source/config/log和退休记录保持。

每60秒检查真实前置和空位，原dispatcher锁/先写reservation、Issue121最多8个allocation（pending/unknown计入，其他成员/同账号无关作业排除）保持。c96默认6×16即时补位，1.2预测和16GiB guard/liveRSS保持。R342 mapping未完成，344/345/346不得提前获资格。控制器不在登录节点执行EDA或授予最终资格。
