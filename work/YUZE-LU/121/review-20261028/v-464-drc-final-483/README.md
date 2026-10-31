# 旧463完整独立DRC最终结果

Refs #121 / PR122。实际464/93610自然FAILED/1:0；原生458项，完整未删改GDS规则129类别/0项。原生为Metal Spacing456/NS Metal2，M2=275/M3=182/M6=1；没有排除规则或豁免。

13份原始文件和1份大型GDS索引，309源Git blobs、全部receipt输入、稳定输出及同一实际最终源回执已核验；失败child日志封存后追加堆栈单独记录。来源36a02f4a/归档2efd4206，源归档与实际manifest一致。

此前480最终三初态功能和482独立strict LEC通过，不能抵消旧463的最终setup/maxcap与此次原生DRC失败。该源拒收，且不转移资格或坐标到当前476。实际当前4个Issue allocations与历史错460/422统计见accounting-readback。

逐文件SHA、服务器大文件位置、规则源和完整解析见index.json与verification.json。
