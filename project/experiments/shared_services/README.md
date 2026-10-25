# Issue106 shared services

先运行 `python -B scripts/check_project.py`。全部真实张量/整数参考/RTL/map/gate仅本人服务器。复现时创建新输出，不覆盖已有结果。当前已获有界L2、完整恢复与选定raw门级证据，非物理/全模型/完整库验收。

- [协议](PROTOCOL.md)：唯一16KiB1RW/8S8/S32/SFU/link、互斥lease、外部地址/原子根义务和结果提交边界。
- [报告](../../../docs/experiments/issue-106-shared-services.md)、[结果索引](results/issue-106/index.json)、[实际命令](../../../work/Liangruizhi/106/execution.json)。
- 服务器根 `/public/home/yuzelu/RuizhiLiang/issue106-shared-services-20261025`。正式混合mixed002/102=phase3；最终27命令qual004/104=phase6；map01/gate001/101/独立gate-receive01=phase4；analysis01/delivery01=phase7。
- 正常7命令与恢复27命令两等待均独立全值接收；门级只选4个完整正常命令，无Q注入，逐字段比同driver RTL再独立原oracle。负例是真文件改码重SHA后走receiver，不是只测一个helper。
- 精确build/sim/receive/map/gate/negative argv和源SHA见execution；恢复应使用其对应冻结phase及原source.zip，不让新文档或一行空白整理冒充原运行源。

PC仅接收字节，输出另存D盘本任务新目录：

```text
python -B work/Liangruizhi/106/verify_delivery.py --index project/experiments/shared_services/results/issue-106/index.json --archive project/experiments/shared_services/results/issue-106/selected.zip --out NEW_BYTE_RECEIPT.json
python -B work/Liangruizhi/106/verify_sources.py --repository . --index project/experiments/shared_services/results/issue-106/index.json --selected project/experiments/shared_services/results/issue-106/selected.zip --expected-phases 7 --out NEW_SOURCE_RECEIPT.json
```

完整数据与已执行二进制在服务器完整包，精选只含源/配置/metadata。GDN104、通用ISA/GEMM、KV append/online、真实下游事务暂存、宏/物理与制造后连接仍单列。
