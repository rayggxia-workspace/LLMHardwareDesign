# Issue61服务器批次执行交接（持续更新）

仓库 https://github.com/rayggxia-workspace/LLMHardwareDesign；Issue61/草稿PR62；负责人Liangruizhi，task/61-server-models；工作目录 D:/Projects/LLMHardwareDesign-servermodels。最新commit以PR62 head和phase5/binding.json为准；初始采集源码8a1fe4b，尚未正式采集。仅本人服务器目录 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023，所有计算经lrz-* Slurm，不动其他成员作业。

恢复第一步：重新读AGENTS/Skill、Issue61/PR62与成员任务；squeue检查实际作业，读取D:/Projects/Codex/issue61-server-models-20261023/*relay01.log及最终JSON，不能因为下载中未有lrz队列就重复启动。relay为SSH数据传输，权重不落本机；只有服务器全文件SHA验证后原子发布，.relay-part仍是未完成。

已执行89992/89993（23秒/4秒）Qwen真实partial/state独立复核、90002（35秒）Gemma/Phi后端预检，全部COMPLETED0:0。89995直接HF下载DNS失败，保留失败日志，不删除失败。来源输入、回传包SHA、条件与范围见docs/experiments/issue-61-server-models.md和work/Liangruizhi/61/model-acceptance.json。69文件接收已核原字节57项，另12项Git LF可精确还原原CRLF并SHA一致，详见pr36-intake.json；两类验证不可混称原字节全等。

Gemma/Phi phase5源码已单独冻结上传，等待权重SHA后提交capture-job.sh；新运行目录gemma-capture01/phi-reserved01，不能覆盖。协议Gemma128/window±1/4096+32、完整2Q/1KV、缓存真实storage；Phi128/1024+32完整3Q/1KV采集封存，禁止以其结果调划分。CPU FP32/原BF16权重与W8A8/硬件区分，非GPU测量。

PR36保存部分和和递推原张量，但普通/全局attention主要是shape/接口记录，完整GQA的Q/K/V实际输入不足；后续只补短代表层，不重跑已覆盖的长推理或GPU矩阵。相同权重/config/分词器哈希的Qwen镜像已核，Qwen3.5 LICENSE只有LF/CRLF差异、可精确还原旧SHA，权重无变化。现代独立5.20.2环境依赖wheel已固定，尚未安装或推理；不修改53旧环境。

未完成：权重传输/全文件校验、正式Gemma/Phi采集与封存、必要Qwen完整GQA缺项、接收schema导出、独立整数与成本验证、统一索引/报告/实际业务检查。未提交改动按git status核验，不覆盖其他目录。登记management-hub PR5 pending；无board.json/Projects能力，看板unverified同步pending待管理员，审查人待指定，PR未合并/任务非done。
