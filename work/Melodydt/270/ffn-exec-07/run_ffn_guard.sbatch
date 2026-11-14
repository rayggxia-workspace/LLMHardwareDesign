#!/bin/bash
#SBATCH --job-name=zny-ffn-guard
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:35:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
base="/public/home/yuzelu/Melodydt/runs/issue-270/ffn-wait-06/run-113287/source"
work="$PWD/run-$SLURM_JOB_ID"
mkdir -p "$work"
target=project/experiments/shared_x_control/rtl/p_native_weight_overlap_candidate.sv
archive=/public/home/yuzelu/project-circuit/issue260-decode638-live-product-ffn-repeat5-SR6Qffhj/source.tar
printf '%s  %s\n' 8294abc3b8da18f22db091627353b68cdd1498ab2e32c1293a8b0abd56b4a5da "$archive" | sha256sum -c
mkdir -p "$work/source"
tar -xf "$archive" -C "$work/source" --no-same-owner --no-same-permissions
python3 -B prepare_native_probe.py "$work/source"
python3 -B prepare_ffn_wait.py "$work/source"
cmp "$base/$target" "$work/source/$target"
sha256sum "$work/source/$target" > "$work/baseline.sha256"
case ${1:?baseline or candidate} in
 base) ;;
 exec)
  python3 -B prepare_exec_priority.py "$work/source"
  python3 -B prepare_guard_fixture.py "$work/source/project/experiments/shared_x_control/rtl/tb_p_weight_global.sv"
  ;;
 *) exit 2;;
esac
sha256sum "$work/source/$target" "$work/source/project/experiments/shared_x_control/rtl/tb_p_weight_global.sv" > "$work/tested.sha256"
rtl=$work/source/project/rtl
exp=$work/source/project/experiments/shared_x_control
cd "$exp"
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
printf '%s  %s\n' 6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7 "$bank" | sha256sum -c
sif=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
runtime=/public/software/singularity-ce-4.3.4/bin/singularity
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
srun --exact -n1 -c1 --cpu-bind=cores /usr/bin/python3.11 -B make_p_resident_x_vectors.py --out "$work/vectors" --groups 8
top=tb_p_weight_global
cat > "$work/sram_unused_pins.vlt" <<'LINT'
`verilator_config
lint_off -rule PINCONNECTEMPTY -file "*/rtl/s_sram/local_s_base.sv"
LINT
srun --exact -n1 -c"$SLURM_CPUS_PER_TASK" --cpu-bind=cores "$runtime" exec --cleanenv --bind /public/home/yuzelu "$sif" \
 "$verilator" --binary --timing --assert --Wall --timescale-override 1ns/1ps --x-initial unique --x-assign unique \
 -j "$SLURM_CPUS_PER_TASK" --top-module "$top" "-GMODE=3'd7" -GGROUPS=8 --Mdir "$work/obj" \
 "$work/sram_unused_pins.vlt" \
 native_s_lint.vlt rtl/{native_s128_mux3,early_copy_3p,private_a_tile_abort_frontend,private_a_scaled_abort_frontend,private_a_scaled_fenced_frontend,bounded_serial_m_guard2,m_short_command_tx,m_dual_exec_issue,p_native_stream_m2_bounded,p_native_weight_prefill,p_native_weight_overlap_candidate,p_native_resident_x_candidate,p_native_a16_dual_profile,resident_x16_directory,p_scope_range_service}.sv \
 "$rtl/block_local_native/"{s32_a16_tile_quantizer,copy_scale_header_tx,copy_scale_header_rx,early_copy_epoch_3p,p_scope128_decode,record_range_iterator,a_scale_directory32}.sv \
 "$rtl/w8a16_v1/"{m_native_leaf_s32,m_native_s32,weight_records,m_group_s32,projection_context_s32,scale_group_s32}.sv \
 "$rtl/s_sram/"{local_s_base,block_feed_s16k_sram}.sv "$bank" "$rtl/mother_control_native/mc_dma_fabric.sv" "rtl/$top.sv" > "$work/build.log" 2>&1
rc=0
for mode in normal before during; do
 flags=()
 if [[ $mode != normal ]]; then flags+=(+CANCEL_FOUR); fi
 if [[ $mode == during ]]; then flags+=(+CANCEL_DURING_OVERLAP); fi
 for init in 0 1 2; do
  for seed in 1 2 3 4 5 6; do
   slot="$work/$mode-$init-$seed"
   if srun --exact -n1 -c1 --cpu-bind=cores "$runtime" exec --cleanenv --bind /public/home/yuzelu "$sif" \
     "$work/obj/V$top" "+VECTORS=$work/vectors" "+SEED=$seed" "+verilator+seed+$seed" "+verilator+rand+reset+$init" \
     "+TRACE=$slot.csv" "${flags[@]}" > "$slot.log" 2>&1; then
    grep -m1 '^REAL_WEIGHT_GLOBAL_PASS ' "$slot.log" || rc=1
   else
    echo "FAILED $mode reset=$init seed=$seed"
    tail -6 "$slot.log"
    rc=1
   fi
  done
 done
done
cd "$work"
sha256sum vectors/* *.csv *.log *.sha256 > proof.sha256
exit "$rc"
