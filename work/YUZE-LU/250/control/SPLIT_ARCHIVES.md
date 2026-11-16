# 原始验收包的传输分片

run38起的`.pack.tar.gz`以不超过1MiB的原始字节分片保存。相邻
`.pack.tar.gz.manifest.json`记录原archive的完整SHA-256、总字节数、
各分片路径/长度/SHA-256。没有删除或改写包内源、向量、失败记录或CSV。

`rtl-run-index.json`的`package`仍是原archive逻辑名，`package_sha256`
仍是原archive SHA。`package_transport_manifest`指向实际传输清单；
不能把manifest本身的SHA与原archive SHA混用。

读取原单文件和分片包使用同一入口：

```python
from archive_transport import open_archive
with open_archive(original_archive_path) as archive:
    members = archive.getmembers()
```

入口先逐项验证分片与完整原archive SHA，再提供可seek的tar读取；最多
打开一个当前分片文件，不要求回拼一份大blob。新包可用
`python archive_transport.py path/to/package.pack.tar.gz --replace`转换。
仅在重新读取全部分片、确认原SHA完全相同后替换这一个明确命名的本地
传输文件。历史原包仍在Git历史和远端不可变运行目录中。

[`split-transport-38-50.json`](split-transport-38-50.json)是这轮逐包核对回执。
run38原21,817,572字节完整保留为21个分片；其余本轮包各小于1MiB，
也采用同一清单格式。每包都从分片重新读出了全部tar成员。
