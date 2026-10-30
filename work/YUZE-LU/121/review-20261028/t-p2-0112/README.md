# 完整实际接口P2几何验收

实际捕获时间/SHA见[index.json](index.json)，目录标记不是精确时间。原始receipt、revision300-escape.json、joined-readback.json全部通过且逐文件SHA绑定。三次真实DEF/ODB读回、每位对应/精确几何/连接/间距、完整native M10接入、joined GDS全部原生层XOR0、新增实际M10金属负例与新层规则通过，原文件不变。

T261：386位；1120µm测试外框/145136µm线长/via10 386/via11 196；每线376µm，base58.4270fF/high87.6405fF，386根base全部超48fF线预算。

这是有限实际完整端口场景，组合接口时序、完整12层工艺/制造及任意排列/阵列资格仍为false。简化RC参数未经工艺校准，不能把几何通过或native300MHz自动等同带线后的300MHz。
