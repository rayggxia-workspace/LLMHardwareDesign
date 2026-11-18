Closes #289
Refs #287

完成两套A/B归档方案340个非P目标输出的BUF_X8升级及宏/block后端验收：C153、U153、G33、F内S1；方案A306、B340。信号引脚、宏位置和外形保持不变，逐周期可见行为按记录的证明链核验。

| 父block | TT名义频率 | setup | hold | 完整原版DRC |
| --- | ---: | ---: | ---: | ---: |
| C43 plan0（G hold03-v3） | 250MHz | +6.340040ps | +1.990130ps | 0 |
| U-v19-preserved | 250MHz | +78.050904ps | +3.471112ps | 0 |
| F-h20-v4（S minimal-localv4） | 300MHz | +221.605405ps | +2.453537ps | 0 |

三者setup/hold/电容/slew/fanout均零违例，PG、异步控制、信号几何和宏视图检查通过。C/U冻结契约为目标输出50fF、4ns、0.1ns uncertainty；F沿用原SDC，实际序列化周期3.3333ns。裕量较小，尚未验证多PVT或两套实际顶层长线RC。

C最终原版全量检查120303完成2h20m59/0，零项；278701网络实际提取前后全层/过孔材料一致。实际最终ODB导出网表2b74fbc9…经21095状态/数据/控制证明120296通过。原RTL至综合边界包含有限/通用自动证明和明确人工组合桥，不声称全模块RTL SAT。Liberty/物理LEF/父级抽象重载、引脚/OBS/实际cut覆盖通过。root来源复核120326及严格聚合120366通过；最终发布只读重验120368通过58文件。

C native报告222个同网M2/M3 spacing标记逐项按实际金属与局部space/notch证明，绑定同GDS原版完整0项后精确裁定；F为40历史标记+4逐项证明同网接触。报告未被清空，也没有通用规则例外。C PG相对原CTS230条移除/140新增已精确追溯v16/C35并在当前ODB/GDS复核，信号引脚几何保持不变。

最终报告：`work/YUZE-LU/289/audit/BACKEND-ACCEPTANCE.md`。
联合索引：`work/YUZE-LU/289/audit/evidence/AB-X8-final-joint-release-index.json`，SHA256 `406b800bda878d80bf5f082890b217a6db2222dc938adb2f94ab38a29dcfa053`。
C接受回执SHA256 `e5ce4311b8cd929a92e53de805eb4846223147e7f231fc9d374c92774cd7c314`。U/F接受回执保持原SHA。
大件冻结在授权服务器`/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117`，C位于`audit/C-final-release-v1/`，其余包路径及原样回执见联合索引。

规则：rayggxia-project-collab 1.0.0。项目llm-hardware-design；负责人YUZE-LU；工程验收完成、PR待独立审查、Issue in_review；审查人待指定，不自动合并。`python scripts/check_project.py`通过，此为管理结构检查，物理/功能结论以上述EDA回执为准。登记management-hub PR5仍open/未合并、pending。缺config/board.json和read:project，Projects字段/条目unverified、同步pending；保留Issue7持久交接，由有权限管理员处理（待指定）。P、顶层RC/串扰、多PVT另验，B的G/S压力测试不自动建立产品级协议实现。
