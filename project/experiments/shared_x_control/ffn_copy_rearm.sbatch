#!/usr/bin/env bash
#SBATCH --job-name=yzl-copy-rearm
#SBATCH --partition=c64
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --nodes=1
#SBATCH --time=00:20:00
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
lock="$EXP/FFN_COPY_REARM_SOURCE_LOCK.json"
threads=${SLURM_CPUS_PER_TASK:-10}
seeds=(25001 25002 25003 25004 25005 25006)
if [[ ${SLURM_NTASKS:-6} == 8 ]];then seeds+=(25007 25008);fi
srun --exact -n1 -c "$threads" --cpu-bind=cores python3 -B "$EXP/derive_copy_epoch_rearm.py" --root . --out "$root/generated" --source-lock "$lock"
srun --exact -n1 -c "$threads" --cpu-bind=cores python3 -B "$EXP/derive_ffn_copy_rearm_test.py" --root . --generated "$root/generated" --out "$root/test" --source-lock "$lock"
sha256sum "$root"/{generated,test}/*.sv > "$root/derived.sha256"
top=test_ffn_three_p_copy_rearm
srun --exact -n1 -c "$threads" --cpu-bind=cores \
 "$runtime" exec --cleanenv --bind /public/home/yuzelu "$image" "$vlt" \
 --binary --timing --assert -Wall --timescale-override 1ns/1ps --x-initial unique --x-assign unique -j "$threads" \
 --top-module "$top" --Mdir "$root/obj" \
 "$EXP/native_s_lint.vlt" "$NE/real_s_lint.vlt" \
 "$EXP"/rtl/{p_scope_range_service,p_native_stream_m2_bounded,bounded_serial_m_guard2,m_dual_exec_issue,m_short_command_tx,private_a_scaled_fenced_frontend,private_a_scaled_abort_frontend,private_a_tile_abort_frontend,native_s128_mux3}.sv \
 "$N"/{p_stream_scope_node,p_scope128_decode,record_range_iterator,ffn_gate_up_ring_control,quant_mid_s128_router,g_s128_observed_scale,a_scale_directory32,native_s128_mux4,ffn_copy_epoch_fence}.sv \
 "$W"/{m_native_leaf_s32,m_native_s32,weight_records,m_group_s32,projection_context_s32,scale_group_s32,g_s32,g_s128_frontend}.sv \
 "$S"/{local_s_base,block_feed_s16k_sram}.sv "$bank" \
 "$root/generated"/{early_copy_3p,early_copy_epoch_3p,copy_scale_header_rx,copy_scale_header_tx,s32_stripe_copy,s32_a16_tile_quantizer}_rearm.sv \
 "$root/test"/*.sv > "$root/build.log" 2>&1
pids=()
for seed in "${seeds[@]}";do
 srun --exact -n1 -c "$threads" --cpu-bind=cores "$runtime" exec --cleanenv --bind /public/home/yuzelu "$image" bash -c '
  set -euo pipefail
  root=$1;seed=$2;exp=$3;top=$4
  out="$root/seed-$seed"
  python3 -B "$root/source/$exp/make_ffn_native_vectors.py" --root "$root/source" --out "$out" --columns 384 --seed "$seed"
  for mode in 0 1;do
   for init in 0 1 2;do
    log="$out/mode-$mode-initial-$init.log"
    "$root/obj/V$top" "+mode=$mode" "+seed=$seed" "+X=$out/X.hex" "+SCOPES=$out/scopes.hex" "+MID=$out/Mid.hex" \
     "+verilator+seed+$seed" "+verilator+rand+reset+$init" > "$log" 2>&1
    grep -q "PASS ffn_copy_rearm old_final=65535 new_final=32 held_ack_cycles=7 fences=1 words=3072 scatter=384" "$log"
   done
  done
 ' bash "$root" "$seed" "$NE" "$top" > "$root/seed-$seed.log" 2>&1 &
 pids+=("$!")
done
status=0
for pid in "${pids[@]}";do wait "$pid" || status=1;done
exit "$status"
