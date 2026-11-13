#!/usr/bin/env bash
#SBATCH --job-name=yzl-copy-m-fence
#SBATCH --partition=c96
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=12
#SBATCH --nodes=1
#SBATCH --time=00:30:00
set -euo pipefail
root=$SLURM_SUBMIT_DIR
EXP=project/experiments/shared_x_control
N=project/rtl/block_local_native
NE=project/experiments/block_local_native
W=project/rtl/w8a16_v1
S=project/rtl/s_sram
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
sha256sum -c "$root/candidate.sha256" > "$root/candidate-check.log"
scontrol show job "$SLURM_JOB_ID" > "$root/allocation.txt"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c
echo "$(cat bank.sha256)  $bank" | sha256sum -c
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
runtime=/public/software/singularity-ce-4.3.4/bin/singularity
threads=${SLURM_CPUS_PER_TASK:-12}
seeds=(25001 25002 25003 25004 25005 25006 25007 25008)
srun --exact -n1 -c "$threads" --cpu-bind=cores python3 -B "$EXP/derive_copy_epoch_rearm.py" --root . --out "$root/generated" --source-lock "$EXP/FFN_COPY_REARM_SOURCE_LOCK.json"
srun --exact -n1 -c "$threads" --cpu-bind=cores python3 -B "$EXP/derive_ffn_copy_combined_test.py" --root . --generated "$root/generated" --out "$root/test" --source-lock "$EXP/FFN_COPY_COMBINED_SOURCE_LOCK.json"
if [[ ${1:-serial} == lookahead ]]; then
 srun --exact -n1 -c "$threads" --cpu-bind=cores python3 -B "$EXP/derive_combined_copy_lookahead_test.py" --test "$root/test" --generated "$root/generated" --source-lock "$EXP/FFN_COPY_LOOKAHEAD_SOURCE_LOCK.json"
fi
sha256sum "$root"/{generated,test}/*.sv > "$root/derived.sha256"
top=test_ffn_copy_combined
srun --exact -n1 -c "$threads" --cpu-bind=cores \
 "$runtime" exec --cleanenv --bind /public/home/yuzelu "$image" "$vlt" \
 --binary --timing --assert -Wall --timescale-override 1ns/1ps --x-initial unique --x-assign unique -j "$threads" \
 --top-module "$top" "-GFOUR_BANK_LOOKAHEAD=1'b1" "-GWITH_SHARED_DMA=1'b1" "-GSPLIT_UP_CHANNEL=1'b1" --Mdir "$root/obj" \
 "$EXP/native_s_lint.vlt" "$NE/real_s_lint.vlt" \
 "$EXP"/rtl/{p_scope_range_service,p_native_weight_prefill,p_native_stream_m2_bounded,bounded_serial_m_guard2,m_dual_exec_issue,m_short_command_tx,private_a_scaled_fenced_frontend,private_a_scaled_abort_frontend,private_a_tile_abort_frontend,native_s128_mux3}.sv \
 "$N"/{p_scope128_decode,record_range_iterator,ffn_gate_up_ring_control,quant_mid_s128_router,g_s128_observed_scale,a_scale_directory32,native_s128_mux4,ffn_copy_epoch_fence,ffn_copy_scope_admission}.sv \
 "$W"/{m_native_leaf_s32,m_native_s32,weight_records,m_group_s32,projection_context_s32,scale_group_s32,g_s32,g_s128_frontend}.sv \
 project/rtl/mother_control_native/mc_dma_fabric_typed_p.sv \
 "$S"/{local_s_base,block_feed_s16k_sram}.sv "$bank" \
 "$root/generated"/{early_copy_3p,early_copy_epoch_3p,copy_scale_header_rx,copy_scale_header_tx,s32_stripe_copy,s32_a16_tile_quantizer}_rearm.sv \
 "$root/test"/*.sv > "$root/build.log" 2>&1
pids=()
for seed in "${seeds[@]}";do
 srun --exact -n1 -c "$threads" --cpu-bind=cores "$runtime" exec --cleanenv --bind /public/home/yuzelu "$image" bash -c '
  set -euo pipefail
  root=$1;seed=$2;exp=$3;top=$4
  out="$root/seed-$seed"
  python3 -B "$root/source/$exp/make_ffn_native_vectors.py" --root "$root/source" --out "$out" --columns 384 --seed "$seed" --split-up-channel
  for mode in 0 1;do
   for init in 0 1 2;do
    log="$out/mode-$mode-initial-$init.log"
    "$root/obj/V$top" "+mode=$mode" "+seed=$seed" "+X=$out/X.hex" "+SCOPES=$out/scopes.hex" "+MID=$out/Mid.hex" \
     "+verilator+seed+$seed" "+verilator+rand+reset+$init" > "$log" 2>&1
    grep -Eq "^PASS ffn_copy_combined scopes=2 copy_fences=1 blocked_ack_cycles=7 M_fences=[1-9][0-9]*,[1-9][0-9]*,[1-9][0-9]* first_purges=[0-9]+ purges=[0-9]+ W64=52224 COPY=3072 scatter=384$" "$log"
   done
  done
 ' bash "$root" "$seed" "$NE" "$top" > "$root/seed-$seed.log" 2>&1 &
 pids+=("$!")
done
status=0
for pid in "${pids[@]}";do wait "$pid" || status=1;done
exit "$status"
