# 023 · 修正落点 Tcl 作用域

- 022 的 Slurm 97515 在 node15 上用两条 12 核步骤。P/J 都在 `do-floorplan.log` 报 `can't read "pg_origin": no such variable`，因为 ORFS 从函数作用域 source 落点脚本。P/J 分别在 30 秒、41 秒终止，后继 97516 取消。
- 修复将 snapped core 导出的 `pg_origin` 显式传入每次间距计算，几何策略与 022 一致。试验 `023-pin-scope` 的脚本 SHA-256 为 `309626ca3aaa779988736093353c0ed6cc77d8618307918522fe805ff8db87f9`，输入 RTL 包 SHA-256 为 `05e36df4fd1fd8e2d25fbe75aa0031fa65b4879047db668b0793511e805eeda7`。
- 作业 97519 在 node17 上用 P/J 各 12 核，两块都完成 floorplan。后继 97520 为 8×12 验收。继续检查实际 DRT、PG 和提取。
