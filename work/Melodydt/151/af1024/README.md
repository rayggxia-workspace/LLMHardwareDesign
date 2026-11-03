Qualified attempt r03: source b3e14e27e1c38afc697d383e33f5d8d90be62267, Slurm95849/node1/c64/8CPU COMPLETED0:0/00:26:07, 34 CASEs/12 actual dump SHA checks PASS. Failed attempts r01/r02 remain recorded. [Report](../../../../docs/W4_AF1024_IMPLEMENTATION.md), [receipt](evidence/runs/r03/results/run-receipt.json), [roadmap](roadmap-update.json), [local PDF index](local-PDF-index.json). Preparation text below records source-time intent; scope remains fixed synthetic integer A-to-F, not trained quality or general L5.

# L4-AF1024 fixed A-to-F integration

Issue151 / PR152, Melodydt; input ddc6b42dc3cc134e5184ef251df5fa9e6f7b8c10, task/151-six-connection-study to task/143-seven-block-v2. The local isolated partial API package is work/Melodydt/151/af1024-ddc6b42/integrated; no .git/HEAD/index/staging. Existing52 RTL/TB/include files and source locks stay unchanged.

The new parent instantiates one complete AFULL A and one baseline F1024. Total native resources are M2/N2/E2/G1/S2/T2/R0, not a single shared island. A produces two H1024 hidden rows; its existing T actually holds these while one F is invoked twice. The parent stores only independent F gamma in128x128bit/2048B registers, plus real control/metadata holding. No new4096B Y array is assumed.

The selected format is S16 Fin10, S8 Fin7, epsilon_code1. A and F weights/gamma are independent. F's9MiB matrix stream is actually replayed for both rows, hence18MiB accepted F data alongside6MiB A data. Fixed parent sequencing, actual destination storage ACK, source holding, child completion, T releases and parent terminal obligation must all be verified.

Formal RTL/TB are project/rtl/block_connection_w4/block_w4_af1024_top.sv and project/tb/block_connection_w4/block_w4_af1024_tb.sv. The ABI/lifetime contract is docs/rtl-contracts/AF1024_PORTS_AND_LIFETIME.md. build_af1024_vectors.py and fixture-contract.json define independent math and fixed vector hashes; af1024-tb-contract.json freezes source closure/CASE order/12 actual dump checks; run_af1024_job.py is Slurm/server-only.

All RTL compilation/simulation is only on yuzelu@10.129.166.172, under /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/af1024-ddc6b42-20261103, job name zenanyan-af1024 and8CPU. New attempts use new input/output folders; no failed attempts overwritten. Evidence and results are added only after execution, not inferred from preparation.

This fixed synthetic integer vertical integration is not trained-model quality, arbitraryshape/cache/decode, generic L5 mother control or peer storedACK network, real MEM, product ROM/M11-M12 binding or physical qualification. Old24 real-target GAP decisions remain. The local sharing PDF is updated in place after each completed step at the user's existing canonical filename; it stays local rather than being uploaded to Git.
