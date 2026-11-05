# 021 · 分段 P4 到 M 的供数与反压

- 源 `a18e4a649`，归档摘要 `05e36df4fd1fd8e2d25fbe75aa0031fa65b4879047db668b0793511e805eeda7`。RTL 作业 97511 在 c96 node15 同时两个 12 核步骤，整轮 8 s。
- 019 CUGR 的 P 路径报告集中在 `store/a_ready`、`store/b_ready`。P 增加 A/B 各一个寄存槽，从而在 native M 暂停时保持数据并切断组合反压。独立延迟计入 v1，load_done 只在 SRAM feeder 完成且 M 已消费最后两个槽后发布。
- RTL P/J 回归通过。日志摘要分别为 `fd3e2acb7e8eb6422a9af0b5d6a33a9fc6d522b663dd5a3b641d4b15271be05a`、`31de8deb3b5ebfbf0c65c4a9846c23c6245f06dcde71d52e8e0e910ccd3c93a5`。传统导引 P&R 作业 97512，后继 97513。