# 144 · 两块同版验收与归档前置校验

- P 的 139 最终 ODB 已取得三初态功能通过回执，J 的 119 亦已通过。两块的原版完整 GDS 规则仍在运行。
- 准备远端 `144-release-preflight/{verify.py,run.sh}`，用六件 SHA、四门回执、证据文件 SHA、GDS/ODB/SPEF 绑定、完整原版规则零标记和执行源 SHA 作硬门限。只有全部通过才生成单块交付包。
- `verify.py` 的 SHA-256 为 `ad7365ffd97ab4f587b3af6e228666cb368cb968c752a1d5cec31ee15bd5ba4e`，`run.sh` 为 `11bdffc0b5716edb5eb03141b7c81cb420f95b5d29e53454577e09e9254fa529`。语法已通过，待原版门限后在计算节点各用 12 核并行打包。