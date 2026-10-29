# V361 归约预取修正的六项行为／算术验证

Refs #121 / PR #122。源5ccd9d71a149f1d3ae7e7e1f4430b32644c2a992、归档61538893333d7b15e1f40efea4fa19a2c896eadcb7e9a8609baf896eb56fc628；主V RTL SHA 2c166771f5a0a56477172cec95552bc67daef7e485d495da64315c9485476aed。只将归约叶值改用已有operand_a，尾块有效位提前8bit捕获，未增操作周期。

三初态各566999检查/414906拍；公共42/扩展36案例各两初态，全部measurement字段与355一致；组合/逐命令延迟各三初态；实际RTL函数264bit全输入add/sub/RNE证明和真实单bit负例均通过。47原始文件/35稳定输出、308源Git blobs及receipt输入绑定核验，见index.json/verification.json和measurement-comparison-to-355.json。

映射在原R344/93237/node21的空闲80CPU继续，父16CPU保留、五个16CPU槽即完补位；内存预测/1.2安全系数/16GiB guard/liveRSS不变，无新allocation。尚不能把映射和新源最终P&R标为通过，原357正常继续。
