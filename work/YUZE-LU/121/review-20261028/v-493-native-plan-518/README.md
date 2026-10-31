# 拒收 V493 的只读原生标记规划

Refs #121 / PR #122。没有修改ODB/DEF、创建硬件版本、启动EDA或新增allocation。该分析只为后续实际失败标记的处理准备方法，不能给当前V507授予资格。

实际494最终源receipt SHA为`70af2e70e7301805668c4bd9158cf2b66c5030b02d58bb389b9b01fd303a7513`。逐行读取674158983字节的完整最终DEF并核对其封存SHA，抽出496个原生标记涉及的精确NETS记录；报告绑定512。技术参考复用429封存的Nangate45 tech LEF，远端和本地字节/SHA一致；它不是本轮运行时技术文件的新验收。

现有`revision300_via_realization.plan`生成479项候选，涉及476条网：M2为297项，M3为182项。每个候选仅扩展过孔金属包围矩形，且新增部分完全处于原同网导体矩形并集内；线段、via中心/cut、单元、pin与PG不改。另有17项被拒绝，保留原标记和理由；不能据此认定这些标记必然只能改线，更不能当作已消除479项DRC。

真正应用仍须在选定最终源上重新生成候选，经过同尺寸identity-clone控制、实际ODB/完整DEF/连通核验、完整GDS掩膜对照及全部最终门。这里未执行这些物理检查。

[index.json](index.json)保留原始采集索引；其中10.7MB的`via-plan.json`保留在授权服务器，精确压缩副本为`via-plan.json.gz`。[storage.json](storage.json)记录远端路径与每文件实际SHA、计划器源commit/SHA及元数据读取失败/恢复过程。失败未修改设计数据库，进程缺失核验后才重新读取。

在仓库根目录运行以下命令，可从封存DEF记录、原报告和技术参考只读重算，逐字节比较完整计划：

```powershell
python work/YUZE-LU/121/review-20261028/v-493-native-plan-518/reproduce.py
```
