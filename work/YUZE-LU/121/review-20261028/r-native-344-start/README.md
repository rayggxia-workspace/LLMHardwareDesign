# R344 全新原生实现启动

Refs #121 / PR #122。源 `dda5fd65c494719b840f8439ffcb4a2621817cb4`，归档 SHA `cb5eb96f24fbe75b5d4e403b071683d6ce0f34aea374256db1135f30e055652d`。354原准入自动提交实际 `93237/node21`，新原生六阶段从头执行；R RTL 与342通过的映射完全一致。

实际采集 7 份原始小文件并核验 SHA，307 源 Git blobs 与源归档绑定核验，见 [index.json](index.json)、[verification.json](verification.json)。默认16CPU独立任务；当前只有一个具备前置的R物理任务，345最终门与346接口按真实完成条件补位。原311正常收尾，不继承其CTS/route资格。

这是启动证据，尚无新源最终物理、最终功能/严格LEC或接口资格。未重投342、未取消或重启任何EDA。
