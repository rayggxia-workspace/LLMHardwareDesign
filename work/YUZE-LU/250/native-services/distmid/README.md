# 三P分散Mid：原16KiB容量与S-window复用回归

Refs #250 / PR #251。输入是host真实写ACK产生的A16 Mid，不宣称本fixture执行上游M/G/量化、实际MC/LC程序或Down M算术。

102366：六seed×三初态×两背压=36次。每次86个K128 tile按`t mod3`分存三份真实16KiB S，地址`256+16 floor(t/3)`；三份各自32项stride3目录实际只占29/29/28项。六轮完整遍历共516 COPY，三目的S暂存880..895，同源S也作目的，保持每S单128位端口和两响应owner。258对A双槽、3096次A使用，24768个真实覆盖写；每轮读结果与独立输入逐位一致，最后逐字复读全部1376个Mid word证明保留。没有新增payload SRAM。

失败全部保留：102357/360 strict fixture检查；102361无背压通过但背压死锁。同S下一源读响应挡住旧目的写ACK，旧ACK又是接受该响应的条件。a424fd244为STREAM关闭下一word预取，102366通过。旧U源独立S配置保持默认预取；新STREAM路径费用另测，不能沿用旧时延。

原始bank日志较大，按项目存储规范完整保存在index.json的拥有者集群archive URI，SHA256和字节数均回收核对；本地C盘有同字节镜像，不将约0.8GB展开日志复制进Git。source小包随Git交付。审计必须有完整raw包，索引本身不冒充离线通过：

```powershell
# 从index的准确URI逐项scp，保存为 CACHE/<job>-receipts.tar.gz；不执行归档代码。
python project/experiments/block_local_native/audit_quant_copy_a.py --root work/YUZE-LU/250/native-services/distmid --receipt-cache CACHE
```

已在完整镜像上执行上述审计PASS；源/逐文件SHA、严格构建、所有36份数值与守恒回执均检查。SHA变化即失败。验收仍是组件功能，不是whole-FFN或300MHz系统验收。
