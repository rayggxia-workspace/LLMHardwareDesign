# 证据保留边界

`run901`至`run908`的`index.json`描述对应完整本地捕获：每项原始回执、原报告SHA、已核验的小文件及明确标记的派生摘要。仓库只保留索引、36+12项汇总、工具控制、准备回执，以及四个代表案例的原始receipt/summary/逐线links/timing/electrical报告；索引中的其他文件不因此声称已全部上传到Git。

完整原始报告与完整源/Verilog/SPEF/ODB位于授权服务器对应run目录。`.local/interconnect907-final`和`.local/interconnect908-final`是本工作树的完整捕获副本。使用`interconnect_collect.py`可在新目录重新获取并逐文件校验；`interconnect_report.py`接收完整捕获，而非此处筛选后的目录。

`measurements.json`是从源SHA已核验的报告生成的逐案例汇总。大报告中的全零扇出字典只在派生摘要中替换成计数与字典SHA，原报告、原始回执、校验门均未改变；无需在Git中重复数十万项相同零扇出记录或多份接点坐标。
