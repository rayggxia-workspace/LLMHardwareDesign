# R828 完整 DRC 失败封存（850）

Refs #121 / PR #122。作业94421自然FAILED/1:0，耗时3:34:50。完整未修改FreePDK45 GDS deck的129类检查为0项；OpenROAD原生全片复查为584项（583项Metal Spacing、1项NS Metal；M1为2项、M2为323项、M3为259项）。两套检查均是必要门，因此R未接收，delivery和geometry按真实依赖BLOCKED，829未提交。

[index.json](index.json)封存23个原始文件与10个实际服务器大文件SHA/大小；365个归档源码Git字节、receipt输入和稳定输出已核验。失败绑定同一最终源759cae257ff6731b8424eac6270a7bf255b6f0dc980ba0ff3a7bb508037b916b；原始失败保留，不因838物理/信号、840三初态功能和842严格LEC通过而转成接收。

[collect850.py](collect850.py)保存采集方式。下一步851只读导出全部584个标记的完整邻域（所有网络/层、PG、实际pin、OBS与DEF RECT补全），验证原数据库不变，再根据实际几何决定有限局部修复。不先重跑完整P&R，不移用V的坐标和候选资格。每个新修复源仍须重新通过全部最终门及接口验收。
