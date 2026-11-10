# 原体系S16桥接实际费用复评

Issue247 / PR243。冻结run35已通过的生成源码及全部输入，8个base必须完整RESULT相等。
只按run41真实原生packed16时序替换原S16 NExp额外服务；原vector_region/E/S/cache/DDR保持。
不是完整原生RTL大模型运行，也不改变共享32KiB或外存17.1GB/s。

32场景：base；s16_measured（实测补充计算wrapper费）；s16_full_u_bound（再加完整U帧费用的保守敏感性，
与原模型S费用有重计，因此不称精确校准）；s16_vector8_target（实测S16费用＋仍未闭合的U每拍8值目标）。
E核心II=1不等于U服务II=1，不据此授予vector8完整RTL资格。

profile.py逐SHA校验原生回收日志、全部count1..8、三组seed、完整U输入/计算/输出阶段和真实S访问、
全S16域计算数值、默认精确回归与面积gate。新生产RTL必须和原生部署字节SHA一致。
冻结生成模型依赖run35原回执SHA，禁止从新生产源重生成旧校准再冒称已覆盖新候选。

运行必须在Slurm分配：在新授权个人RUN目录部署source/、frozen_model/、inputs/、native/、run35-result.json及SHA清单，
复制job.sh后执行sbatch --parsable job.sh。完整源码/输入版本由inputs.json与各SHA索引绑定。
