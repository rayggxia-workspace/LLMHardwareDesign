# V379 当前平方和归约新源的实际工作区测量

Refs #121 / PR #122。源5a6e0be84d3aedbb139a29268317761b74e4fbee，归档b6854770bc030eb47b74c8ff920ddd83b29165c92a83d1ea0a24d8c60ac4416c，V RTL SHA7d1ba24a15ac6d5fbc2e43cfbd3859e8940e7fa800988d670e82b2f211a9e3e7。

2026-10-29 13:28:44–13:30:00 UTC，现有R311/93125/node18 allocation内运行：父0–15，五个16CPU子槽16–95动态补位。七项全部通过，135有限场景与78公共端口测量保持373结果；完整measurements逐字段比较见comparison.json。53原始文件、39稳定输出、308源Git blobs和输入回执核验见index/verification.json。没有新增allocation。

RESOURCE-BUDGET使用当前已提交生成器重绑379实际输出；八模型、80候选的全部model字段与封存pre379字节产生的结果完全相同。只更新来源/哈希。有限场景和预算不构成整模型数值质量、10 token/s、功耗或制造资格。380→381→382仍须独立物理、最终门和接口验证。
