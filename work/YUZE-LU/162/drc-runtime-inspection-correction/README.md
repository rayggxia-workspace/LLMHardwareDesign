# DRC只读规则记录纠正

Issue162 / PR163。旧drc-runtime-inspection-01通过source env.sh后cat取得stdout，包含`OPENROAD: /OpenROAD-flow-scripts/tools/OpenROAD`启动提示；其6082f788…哈希仅代表该原始stdout，不是纯平台deck哈希。原始记录及历史快照保留。

新的02记录在同一自有Slurm95341分配内直接读取容器中的原文件，纯XML SHA-256为`4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147`，精确等于旧stdout移除这一个前缀后的全部字节。此纠正只涉及只读诊断快照；实际gates/pg_fixed_access始终直接调用并哈希容器内原始平台完整deck，未调用该快照。没有修改任何原规则、活跃任务、源快照或几何，也没有授予硬件资格。
