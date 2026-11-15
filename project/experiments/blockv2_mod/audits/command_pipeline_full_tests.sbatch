#!/bin/bash
#SBATCH --job-name=yzl-command-regression
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=02:00:00
set -euo pipefail
bash audits/command_pipeline_contract_tests.sbatch
bash audits/command_pipeline_tests.sbatch
bash audits/test_weight_pipeline.sbatch
bash audits/test_quantization_pipeline.sbatch
bash audits/test_local_projection_pipeline.sbatch
bash tests/weight_credits.sbatch
bash tests/activation_pipeline.sbatch
bash tests/activation_pair.sbatch
bash tests/shared_read_window.sbatch
bash tests/shared_activation_pipeline.sbatch
bash tests/projection_source_pipeline.sbatch
bash tests/native64_read_window.sbatch
bash tests/projection_read_queue.sbatch
bash tests/dot_cache.sbatch
bash audits/test_dot_cache.sbatch
bash tests/a_frontend_pipeline.sbatch
bash tests/command_pipeline_store.sbatch
bash audits/command_pipeline_store_tests.sbatch
bash tests/activation_scope.sbatch
bash tests/gather_pipeline.sbatch
bash tests/service_cluster_regeneration.sbatch
QUEUE_OUTPUT="evidence/command-pipeline/n-read-queue-$SLURM_JOB_ID" QUEUE_SOURCE=rtl/control/n32_service_cluster.sv bash tests/projection_read_queue.sbatch
QUEUE_OUTPUT="evidence/command-pipeline/e-read-queue-$SLURM_JOB_ID" QUEUE_SOURCE=rtl/control/e32_service_cluster.sv bash tests/projection_read_queue.sbatch
