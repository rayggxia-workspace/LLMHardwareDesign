#!/usr/bin/env bash
#SBATCH --job-name=yzl-ffn-native
#SBATCH --partition=c64
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --nodes=1
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
threads=$SLURM_CPUS_PER_TASK
case "$SLURM_JOB_PARTITION:$SLURM_NTASKS:$threads" in c64:6:10|c96:8:12) ;; *) exit 2;; esac
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
scontrol show job "$SLURM_JOB_ID" > "$root/allocation.txt"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c
P=project/experiments/shared_x_control
N=project/rtl/block_local_native
vlt=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
runtime=/public/software/singularity-ce-4.3.4/bin/singularity
four=${3:-0}
shared_dma=${4:-0}
program=${5:-0}
split_up=${6:-0}
early=${7:-0}
early_k_prep=${8:-0}
prefill=()
dma=()
if [[ -f "$P/rtl/p_native_weight_prefill.sv" ]]; then prefill+=("$P/rtl/p_native_weight_prefill.sv"); fi
if [[ $four == 1 && ${#prefill[@]} == 0 ]]; then exit 2; fi
if [[ $early == 1 ]]; then prefill+=("$P/rtl/p_native_weight_overlap_candidate.sv"); fi
if [[ $shared_dma == 1 ]]; then dma+=(project/rtl/mother_control_native/mc_dma_fabric_typed_p.sv); fi
mkdir -p "$root/obj"
srun --exact -n1 -c "$threads" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 "$image" "$vlt" --lint-only --timing --assert -Wall --top-module p_stream_scope_node "-GFOUR_BANK_LOOKAHEAD=1'b$four" \
 "-GEARLY_EXEC=1'b$early" --Mdir "$root/obj" \
 "$P/native_s_lint.vlt" \
 "$P"/rtl/{p_scope_range_service,p_native_stream_m2_bounded,bounded_serial_m_guard2,m_dual_exec_issue,m_short_command_tx,private_a_scaled_fenced_frontend,private_a_scaled_abort_frontend,private_a_tile_abort_frontend}.sv \
 "$N"/{p_stream_scope_node,p_scope128_decode,record_range_iterator}.sv "${prefill[@]}" > "$root/lint.log" 2>&1
cols=${1:-0}
if [[ $cols == 0 ]]; then exit 0; fi
down=${2:-0}
EXP=project/experiments/block_local_native
W=project/rtl/w8a16_v1
S=project/rtl/s_sram
MC=project/rtl/mother_control_native
program_sources=()
if [[ $program == 1 ]]; then
 program_sources=("-I$MC" "$P/p_program_lint.vlt" project/experiments/mother_control_native/native_mc_lint.vlt
  "$EXP/ffn_program_control_fixture.sv" "$MC"/{mc_native_controller,mother_control_native64,mc_packet128_bridge,mother_control_native64_transport128}.sv
  project/rtl/mother_control_v1/control_pm.sv "$P"/rtl/{lc_program_store_1k,lc_scope_fetch128,lc_native_scope_controller}.sv)
fi
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
echo "$(cat bank.sha256)  $bank" | sha256sum -c
srun --exact -n1 -c "$threads" --cpu-bind=cores \
 "$runtime" exec --cleanenv --bind /public/home/yuzelu "$image" "$vlt" \
 --binary --timing --assert -Wall --timescale-override 1ns/1ps --x-initial unique --x-assign unique -j "$threads" \
 --top-module test_ffn_three_p_native "-GCOLS=$cols" "-GWITH_DOWN=1'b$down" "-GFOUR_BANK_LOOKAHEAD=1'b$four" \
 "-GWITH_SHARED_DMA=1'b$shared_dma" "-GWITH_PROGRAM=1'b$program" "-GSPLIT_UP_CHANNEL=1'b$split_up" \
 "-GEARLY_EXEC=1'b$early" --Mdir "$root/obj-joint" \
 "$P/native_s_lint.vlt" "$EXP/real_s_lint.vlt" \
 "$P"/rtl/{p_scope_range_service,p_native_stream_m2_bounded,bounded_serial_m_guard2,m_dual_exec_issue,m_short_command_tx,private_a_scaled_fenced_frontend,private_a_scaled_abort_frontend,private_a_tile_abort_frontend,native_s128_mux3,early_copy_3p}.sv \
 "$N"/{p_stream_scope_node,p_scope128_decode,record_range_iterator,s32_stripe_copy,ffn_gate_up_ring_control,ffn_gate_up_mid,ffn_stripe_commit,quant_mid_s128_router,g_s128_observed_scale,copy_scale_header_rx,copy_scale_header_tx,early_copy_epoch_3p,s32_a16_tile_quantizer,a_scale_directory32,native_s128_mux4}.sv \
 "$W"/{m_native_leaf_s32,m_native_s32,weight_records,m_group_s32,projection_context_s32,scale_group_s32,g_s32,g_s128_frontend}.sv \
 "$S"/{local_s_base,block_feed_s16k_sram}.sv "$bank" "$EXP"/{test_ffn_native_p_node,test_ffn_three_p_native}.sv "${prefill[@]}" "${dma[@]}" "${program_sources[@]}" \
 > "$root/build.log" 2>&1
pids=()
for seed in 25001 25002 25003 25004 25005 25006; do
  srun --exact -n1 -c "$threads" --cpu-bind=cores "$runtime" exec --cleanenv --bind /public/home/yuzelu "$image" bash -c '
   set -euo pipefail
   root=$1; cols=$2; seed=$3; exp=$4; down=$5; program=$6; split_up=$7; early_k_prep=$8
   out="$root/seed-$seed"
   vectors=(--root "$root/source" --out "$out" --columns "$cols" --seed "$seed")
   if [[ $down == 1 ]]; then vectors+=(--down); fi
   if [[ $split_up == 1 ]]; then vectors+=(--split-up-channel); fi
   python3 -B "$root/source/$exp/make_ffn_native_vectors.py" "${vectors[@]}"
   program_args=()
   if [[ $program == 1 ]]; then
    python3 -B "$root/source/$exp/ffn_program_emit.py" --fixture "$out"
    crc=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))[\"local_crc32\"])" "$out/program.json")
    program_args=("+MOTHER=$out/mother.hex" "+LOCAL=$out/local.hex" "+LC_CRC=$crc")
   fi
   if [[ $early_k_prep == 1 ]]; then program_args+=(+EARLY_K_PREP); fi
   for mode in 0 1; do
    for initial in 0 1 2; do
     log="$out/mode-$mode-initial-$initial.log"
     "$root/obj-joint/Vtest_ffn_three_p_native" "+mode=$mode" "+seed=$seed" "+X=$out/X.hex" \
      "+SCOPES=$out/scopes.hex" "+MID=$out/Mid.hex" "+DOWN=$out/Down.hex" +TRACE_TILES "+verilator+seed+$seed" "+verilator+rand+reset+$initial" "${program_args[@]}" > "$log" 2>&1
     grep -q "PASS ffn_three_p_native columns=$cols " "$log"
    done
   done
  ' bash "$root" "$cols" "$seed" "$EXP" "$down" "$program" "$split_up" "$early_k_prep" > "$root/seed-$seed.log" 2>&1 &
  pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
