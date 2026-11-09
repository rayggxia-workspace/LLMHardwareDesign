# Issue247 融合与流水研究证据

2026-11-09 Asia/Shanghai；Melodydt；[Issue247](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/247) / [PR243](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/243)。[详细报告](../../../../docs/experiments/issue-247-u-fusion.md)、[决策](../../../../docs/decisions/issue-247-u-fusion.md)、[摘要](summary.md)、[机器摘要](summary.json)、[文件索引](index.json)。

run09/101728源码af9e43282c82ed8bc43cdaf3c2ec3c1ce8fc53b2，9:56 COMPLETED(0:0)，完整结果SHA f65520c819194e07af2d2d8764cde506406913d5d4818c78bc1cb48bcd202919；run07/101720源码1e6e10a7618f3d37542d1f22dd51af6ad1958eb8，0:21 COMPLETED(0:0)，结果SHA e8aa9c641b299ed4c43b6dcea6583cfb77fad7220c1de783190fe2150f37d860。run06/101712与run08/101721失败保留，原生成功子回执不改变整轮失败状态。

服务器登录yuzelu@10.129.166.172；原始成果/public/home/yuzelu/Melodydt/issue247-area-speed/run06–09。collection.json和output-files.sha256记录全部输出，包括未下载的原始JSONL、编译对象和二进制。run06/07/08/09分别回收核验15/20/48/104个原始输出。大事件仅留服务器，不把索引当成已上传原文件。

部分原始日志及run09完整结果使用`原文件名.gz.b64`：对原字节gzip(mtime=0)后Base64，属于无损文本传输。索引SHA验证编码文件；verify.py再解码并比对服务器原SHA，复用原解析器重新检查24项原生/108项FIFO回执。它也核验实测功能源锁与当前源码、作业终态/来源，拒绝将失败运行标为成功。验证不会重跑仿真、不会授予物理资格。

在仓库根运行：

```sh
python -B scripts/check_project.py
python -B work/Melodydt/247/fusion/verify.py --repo . --index work/Melodydt/247/fusion/index.json
python -B work/Melodydt/247/fusion/analyse_fusion.py --fusion work/Melodydt/247/fusion/run09/results/result.json.gz.b64 --overlap work/Melodydt/247/fusion/run07/results/result.json --out-prefix /absolute/new-summary
```

三种证据分开：实际条件SystemC融合；冻结DDR/cache费用的有限资源流水预测；原生S16 RTL局部周期。生产RTL和SRAM容量未新增修改，无完整模型张量数值/真实生成、面积/STA/P&R验收。run09有22完整case/9默认全字段回归/12小trace/3非法CLI，225kernels/4validation/5smoke，独立oracle与预算负例。

规则rayggxia-project-collab1.0.0。文件经任务分支PR交付，Issue in_review，审查人待指定，未合并。登记management-hub PR5 pending；缺board.json/Projects能力，看板unverified/同步pending、管理员待指定。CI按PR回执如实列出。无活动作业，未配置自动监测。
