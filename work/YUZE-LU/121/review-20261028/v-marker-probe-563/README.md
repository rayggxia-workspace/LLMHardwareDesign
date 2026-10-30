# V560 副本显式 RECT 对照失败

Refs #121 / PR #122。源5b6359bf，归档3c9ee22f，313份源Git/远端SHA及receipt输入绑定。14原始小文件/5稳定输出、候选ODB与完整几何两份服务器大文件SHA绑定，失败receipt/原生报告原样保留，原始523 ODB执行前后SHA相同。

实际原生全片DRC由445项降至440项，仍拒收。路径迭代器Counter显示原矩形未丢失、未导出新增RECT，无法满足预期445个新增矩形，整个诊断FAILED。此迭代器遗漏RECT的问题已有native_rect_completion.py的DEF补全机制；本次probe没有使用该补全，因此不能据其Counter宣布导体并集已证明不变。缺失不是通过依据；不能直接把候选替换正式源。

562原生DEF核对已实际PASS，557412普通网络非RECT路径/逻辑端点一致，预期新增445RECT无缺失；完整证据见相邻v-marker-readback-564。不重新运行560，不放宽原生DRC，不向当前552转移资格。当前552原生流程及R404原GRT继续；旧源setup/cap和440项原生间距仍待解决。
