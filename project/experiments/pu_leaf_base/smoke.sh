#!/usr/bin/env bash
set -euo pipefail
root=$1
cpus=${SLURM_CPUS_PER_TASK:?}
slot=${SLURM_ARRAY_TASK_ID:?}
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
    /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu --pwd "$root/source" \
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
    bash -c '
        set -euo pipefail
        root=$1
        slot=$2
        cpus=$3
        common=(project/rtl/s_sram/{local_s_base,local_s_p,block_feed_s16k_sram}.sv
                project/rtl/block_feed_v1/block_feed_loader.sv)
        bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
        echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
        case "$slot" in
            0) top=tb_pu_p_store
               src=(project/rtl/block_local_s/block_local_s_arbiter.sv
                    project/rtl/pu_leaf_base/pu_p_store_control.sv);;
            1) top=tb_pu_compact_e
               src=(project/rtl/block_v2/{block_v2_e,block_v2_e_compact}.sv
                    project/rtl/pu_leaf_base/pu_compact_e_service.sv);;
            2) top=tb_pu_p_group
               src=(project/rtl/block_local_s/block_local_s_arbiter.sv
                    project/rtl/block_v2/{block_v2_m,block_v2_g}.sv
                    project/rtl/pu_leaf_base/{pu_p_group,pu_p_store_control,pj_feed_hold,pj_mem_port,pj_sram_client}.sv);;
            3) top=tb_pu_u_group
               src=(project/rtl/block_local_s/block_local_s_arbiter.sv
                    project/rtl/block_v2/{block_v2_n,block_v2_n_group,block_v2_e,block_v2_e_compact}.sv
                    project/rtl/pu_leaf_base/{pu_u_group,pu_compact_e_service,pu_u_direct_pair,ucf_s_compute_client}.sv);;
            *) exit 2;;
        esac
        out=$root/$top
        /public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator --binary --timing \
            -Iproject/rtl/block_v2 -Wno-fatal --x-initial unique --x-assign unique -j "$cpus" --top-module "$top" --Mdir "$out" \
            "project/experiments/pu_leaf_base/$top.sv" "${common[@]}" "${src[@]}" "$bank"
        for case in 1:143 2:143 2:144; do
            "$out/V$top" "+verilator+rand+reset+${case%:*}" "+verilator+seed+${case#*:}"
        done
    ' bash "$root" "$slot" "$cpus"
