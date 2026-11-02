# 正式服务器脚本只读复核

复核对象为当前`integrated/work/Melodydt/151/run_a8_verilator.py`与`prepare_a8_sbatch.py`，未覆盖正式文件，也未执行HDL/SSH/sbatch。执行`check_server_final.py --root <integrated> --output <本目录/server-final-static-checks.json>`：两脚本AST/Python编译、正式源及独立authority校验、N29/F8 25/A8 26共80项完整集合、24项合成日志正反例、两次本地preparer输出和三种非法配置拒绝均通过。所有正式输入SHA在检查前后相同；具体SHA和本地仅供检查的输出脚本在JSON记录，不能提交这些REVIEW_ONLY脚本。

## ROOT诊断

已读回`server-evidence/c01/runs/r02`及r03真实receipt和version日志。两次CLI请求及receipt解析后工具路径均为`/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator`，wrapper都是28119B、SHA`deaac572105cb908ace4f66b845e68905f162aa3e364df964f707172f4693462`；镜像SHA也相同。r02的container.VERILATOR_ROOT是手设prefix，version退出1并报inconsistent path；r03该字段null，version退出0、识别Verilator5.042，继续进入N编译。

官方wrapper用FindBin的RealBin及安装时替换的pkgdatadir相对路径计算真实ROOT，并用realpath检查手设ROOT是否相等。安装prefix不能凭目录名假定为ROOT，具体包的计算值应由实际安装配置证明；本审阅不猜其目录。见[官方源码](https://github.com/verilator/verilator/blob/master/bin/verilator)。由于r02/r03请求路径与Path.resolve后的路径没有变化，没有证据把该错误归因于Python.resolve；Perl本身也采用RealBin。回执未保存lstat/readlink，因此不能仅据此证明文件绝非symlink，但已排除本次可观察的执行路径改写。保留requested/resolved/is_symlink/readlink元数据可进一步增强追溯，不是此次恢复的前置条件。

## 正式改动审阅

preparer和make_job移除了VERILATOR_ROOT参数/env注入，HOME改为个人bootstrap的`--home`，shared runtime由make_job显式传`/public/software/singularity-ce-4.3.4/bin/singularity`。cache/tmp/Slurm资源/目录/新输出保护仍在。r03实际version成功支持此环境修正；该成功不等于RTL仿真通过。

runner新增的`--nonfatal-warnings`默认为false、需显式opt-in；只追加`-Wno-fatal`，不移除任何warning类别、assert、timing或故障用例。实际warning完整log、每suite类别计数和header保留，回执明确不是lint clean。r03默认fatal的33项warning证据保留；warning逐项是否接受仍由源码审阅负责，不能用flag取代判断。新runner还记录同目录verilator_bin指纹，并在全部suite成功后核对wrapper/core前后SHA；若运行提前失败，当前代码保留其before信息和失败日志，不应把缺少after字段写成已经完成前后核验。

完整CASE/精确PASS/summary/非零退出/显式FAIL的判据保持原样，A8仍用独立CASE合同的SHA、module和TB SHA复核；不能只数marker或因兼容性删除fault。只读复核未见这些正式流程改动的阻断。真实Verilator是否覆盖80项、工具是否稳定和全部warning结论，仍以主任务实际新run回执及独立源码审阅为准，不由本地Python检查代替。
