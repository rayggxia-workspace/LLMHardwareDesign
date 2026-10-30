# 旧476最终网表严格等价检查

Refs #121 / PR122。实际477/93614，common inputs 53478、outputs 53467；diff0/diff1 inputs/outputs均0，SAT为UNSAT、Circuits are IDENTICAL。16原始文件、8大文件SHA索引、311源Git blobs及全部receipt输入/输出绑定；与498三初态功能检查严格绑定同一final-source及功能receipt。

只证明该旧源最终LEC；旧476/477负setup与maxcap2的物理拒收保持，完整DRC单独记录，不转移到新493。路径、实际SHA与源核验见[index.json](index.json)。
