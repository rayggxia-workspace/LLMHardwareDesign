# H1 独立静态审查

本审查仅导入当前 Python 编译器并执行抽象事件/资源检查，未调用写正式产物的 `check_all()`，未修改编译器、target或三份graph。未执行RTL、数值、服务器、综合或物理流程；不是外部PR批准。

最终审阅源：`scripts/check_h1_graphs.py`，SHA256 `341d13be96edd24ced7bc42b1c88a0a6363ea9bcd7cecd7a4f6eef0ccd25c0cf`。源码commit由根任务的实际提交回执绑定，本文不预填。

## 实际执行与结果

在本包integrated根目录执行：

```text
python -B -X utf8 work/Melodydt/151/h1/review/independent_h1_review.py --output work/Melodydt/151/h1/review/independent-review-r02.json
```

最终结果为 `PASS_INDEPENDENT_H1_STATIC_REVIEW`：三图四路径、11项独立拒绝probe通过。逐条解码128bit候选记录并核对各字段；解码64B header，核对表数量、四个offset、graph摘要及完整image字节数。三图结果如下。

| 图 | 控制记录 | 完整候选image | lowered kernel调用 |
|---|---:|---:|---:|
| G1 AF | 48 | 1184B | 3 |
| G2 AFAF | 88 | 2016B | 6 |
| G3 fork/SELECT | 81 | 1808B | 5，每个p路径都执行两F2 |

每条成功路径仅有一次最终EXPORT、一次真实host存储确认的抽象等待、一次CLOSE_OUTPUT；HALT时无活跃edge槽。上述“确认”是未来helper必须实现的合同事实，不是已经发生过的硬件ACK。

## 发现与处理

1. 原源 `88a4d535…` 允许在STORE尚未确认时FREE目的object，再ALLOC同object，将slot1迁至slot0，后续ACK却给新槽置valid。现源禁止释放pending.source或pending.dest，保存并核对目的slot，且图内object只分配一次；独立反例按 `E_FREE_INFLIGHT` 拒绝。
2. 同一原源允许target声明4KiB总容量却接受8KiB峰值，也允许无S叶、无edge owner或record_bits64。现源互验容量/槽、12叶配方、单owner/inflight及128bit编码；四项独立反例分别被正确拒绝。
3. 中间源 `013d4ce7…` 允许同一256word输出再次EXPORT并再次确认。现源用独立状态拒绝重复EXPORT和重复SETOUT；反例返回 `E_DUPLICATE_EXPORT`。

另核对IF的true/false越界目标、host ACK前关闭输出、非接单时捕获p、只完成左消费者就释放fork源。均拒绝，未因修复移除正常保活或引用检查。当前START位于输入/参数存储完成后；不将ARM接单与原生启动混同。

审查r01保留：其唯一失败是审计脚本把重复EXPORT的预期诊断写为较泛的 `E_EXPORT_STATE`，实际源已返回更明确的 `E_DUPLICATE_EXPORT`。r02只修正审计预期，不修改根源码；两份JSON均保留，未覆盖历史记录。

## 证据边界

本结果只覆盖三份固定图、四条选择路径和列出的畸形控制，不证明全部合法图、资源活性或物理编码可制造性。参数引用仍是符号身份，真实参数manifest/容量、通用端点/ACK、错误路径与晚响应隔离、M11/M12读出及物理路线均须后续接收。128bit记录和1184/2016/1808B是逻辑表候选预算，不是ROM面积、FF数量或已实现RTL。训练质量与原24项模型GAP不变。
