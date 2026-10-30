# 598组合试验：实际启动

Refs #121 / PR #122。93794/node19启动，8原始/317归档Git blob与远端SHA核验。归档ff3b356ac62993862bf843f6f3762fb51cdd318030d8701f7f16a7e44bc6d1a3，helper6a9e9748，只增加诊断、不改RTL或当前588。首次本地stage读取尚在生成的tar，在检查manifest前报unexpected end of data；未创建远端目录、未sbatch。归档进程正常完成后只stage一次远端，identity guard通过，实际job93794。不是EDA重试，也不是最终资格。
