# 128-bit and 512-bit SRAM timing experiment

Issue [#234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234) and PR [#260](https://github.com/rayggxia-workspace/LLMHardwareDesign/pull/260).

The 128-bit and 512-bit runs use the same sealed Qwen2.5-3B program, 512 positions of representative KV, two complete 36-layer decode steps, a 3,334 ps core period, two DRAMsim3 channels, 32 DMA credits per channel and an eight-beat KV window. The two-token 512-bit prefill starts with empty KV and ends at the second position's final residual. See the [execution commands](../../../../project/experiments/systemc_benchmark/README.md).

| Run | Slurm job | Source manifest |
| --- | --- | --- |
| 128-bit decode | 107947 | [128-source.sha256](128-source.sha256) |
| 512-bit decode | 108284 | [source.sha256](source.sha256) |
| Width comparison | 108308 | [compare.py](compare.py) |
| 512-bit prefill | 108359 | [prefill-source.sha256](prefill-source.sha256) |

The manifests identify the archived source and runner bytes for the individual jobs. The public replay uses the same short-run modes and takes the paths to the archived inputs as arguments. The inputs stay in the project archive.

| Archived input | SHA-256 |
| --- | --- |
| Sealed deployment proof | `74078b0b40fdeb73aeae71e3091db3e6a25fc5f27bc03c9981214bfef92b39ef` |
| Decode KV binding | `78347abd13135d71a678ff87b4760175ea81fb701a4edb022e080165321f2b4e` |
| DRAMsim3 bridge | `363d38212c06ded6b012c609cf834d2176fb51acb41ec0fedca918768cfbe292` |
| DDR4 channel configuration | `748ba1a2e06c26f4a71f27a9a98060ecf00432376ad417deae1ab92afdcb0766` |
| Initial DDR image table | `e55ce2d889261daccbf43335875be922fe813fe92dc0ae9ee28fd1f5b880d7b5` |

The first four complete layers took 80.203 ms at 128 bits and 43.540 ms at 512 bits. Their per-page DDR read and write counts and mother instruction cycle counts matched. These are simulated layer times. The run-specific throughput is reported by the audit after it verifies the corresponding complete trace.
