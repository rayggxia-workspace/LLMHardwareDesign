#!/usr/bin/env bash
#SBATCH --job-name=mdt-280mwave
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:15:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
base=/public/home/yuzelu
bundle=${SLURM_SUBMIT_DIR:?}
cd "$bundle"
if [[ ${1:-} != container ]]; then
    sha256sum -c bundle.sha256
    exec srun --exact -n1 -c 2 /public/software/singularity-ce-4.3.4/bin/singularity exec \
      --cleanenv --bind "$base" --env "SLURM_SUBMIT_DIR=$bundle" "$base/opt/eda/containers/orfs-current-repacked.sif" \
      bash "$bundle/run_c639_m_wave_audit.sbatch" container "$SLURM_JOB_ID"
fi
out=$bundle/wave-$2
runs=$base/Melodydt/runs/issue-280
main=$runs/c639-g32-gate-01/c639-g32-116937
active=$runs/c639-g32-active-01/active-116950
fst=$base/opt/eda/verilator-5.042/share/verilator/include/gtkwave
mkdir "$out"
(cd "$main" && sha256sum --quiet -c gate-results.sha256)
sha256sum --quiet -c "$active/active-results.sha256"

cat > "$out/m_wave_audit.c" <<'C'
#include "fstapi.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

enum Field { CLK, ALLOC, AREADY, START, SREADY, CONTROLS, SPACE, CANCEL, DRAIN, CONSUMED, NUM_FIELDS };
static const char *const names[NUM_FIELDS] = {
    "clk", "alloc_valid", "alloc_ready", "start_valid", "start_ready",
    "controls", "alloc_space", "cancel_valid", "drain_valid", "consumed_valid"
};
struct site {
    fstHandle handles[NUM_FIELDS];
    char before[NUM_FIELDS], after[NUM_FIELDS];
    unsigned cycles, alloc_accepts, start_accepts, overlap, m60_eligible_only;
};
struct trace {
    struct site site[3];
    uint64_t last;
    int have_tick, invalid;
};

static void finish_tick(struct trace *trace) {
    for (int i = 0; i < 3; ++i) {
        struct site *site = &trace->site[i];
        const char *state = site->before;
        if (state[CLK] == '0' && site->after[CLK] == '1') {
            for (int j = 0; j < NUM_FIELDS; ++j) {
                if (state[j] != '0' && state[j] != '1') trace->invalid = 1;
            }
            ++site->cycles;
            site->alloc_accepts += state[ALLOC] == '1' && state[AREADY] == '1';
            site->start_accepts += state[START] == '1' && state[SREADY] == '1';
            const int overlap = state[ALLOC] == '1' && state[START] == '1';
            site->overlap += overlap;
            site->m60_eligible_only += overlap && state[AREADY] == '0' && state[CONTROLS] == '1' &&
                state[SPACE] == '1' && state[CANCEL] == '0' && state[DRAIN] == '0' && state[CONSUMED] == '0';
        }
        memcpy(site->before, site->after, sizeof(site->before));
    }
}

static void event(void *context, uint64_t time, fstHandle handle, const unsigned char *value) {
    struct trace *trace = context;
    if (trace->have_tick && time != trace->last) finish_tick(trace);
    trace->have_tick = 1;
    trace->last = time;
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < NUM_FIELDS; ++j) {
            if (trace->site[i].handles[j] == handle) trace->site[i].after[j] = (char)value[0];
        }
    }
}

int main(int argc, char **argv) {
    if (argc != 2) return 1;
    fstReaderContext *reader = fstReaderOpen(argv[1]);
    if (!reader || fstReaderGetTimescale(reader) != -12 ||
        fstReaderGetEndTime(reader) - fstReaderGetStartTime(reader) != 81920000) return 2;
    struct trace trace = {0};
    const char *suffix = "/M/native/weights";
    const size_t suffix_length = strlen(suffix);
    char path[4096] = {0};
    size_t size = 0, depth = 0, offsets[128];
    struct fstHier *entry;
    while ((entry = fstReaderIterateHier(reader))) {
        if (entry->htyp == FST_HT_SCOPE) {
            const char *name = entry->u.scope.name;
            const size_t length = strlen(name);
            if (depth >= 128 || size + length + 1 >= sizeof(path)) return 3;
            offsets[depth++] = size;
            if (size) path[size++] = '/';
            memcpy(path + size, name, length + 1);
            size += length;
        } else if (entry->htyp == FST_HT_UPSCOPE) {
            if (!depth) return 3;
            size = offsets[--depth];
            path[size] = '\0';
        } else if (entry->htyp == FST_HT_VAR && size >= suffix_length && !strcmp(path + size - suffix_length, suffix)) {
            int lane = strstr(path, "/p0/") ? 0 : strstr(path, "/ps[1]/") ? 1 : strstr(path, "/ps[2]/") ? 2 : -1;
            if (lane < 0) continue;
            for (int j = 0; j < NUM_FIELDS; ++j) {
                if (entry->u.var.length == 1 && !strcmp(entry->u.var.name, names[j])) {
                    if (trace.site[lane].handles[j]) return 4;
                    trace.site[lane].handles[j] = entry->u.var.handle;
                }
            }
        }
    }
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < NUM_FIELDS; ++j) {
            const fstHandle handle = trace.site[i].handles[j];
            if (!handle) {
                fprintf(stderr, "Missing P%d %s\n", i, names[j]);
                return 5;
            }
            fstReaderSetFacProcessMask(reader, handle);
        }
    }
    if (!fstReaderIterBlocks(reader, event, &trace, NULL)) return 6;
    finish_tick(&trace);
    fstReaderClose(reader);
    if (trace.invalid) return 7;
    for (int i = 0; i < 3; ++i) {
        const struct site *s = &trace.site[i];
        if (s->cycles != 8192) return 8;
        printf("%s\tP%d\t%u\t%u\t%u\t%u\t%u\n", argv[1], i, s->cycles, s->alloc_accepts,
               s->start_accepts, s->overlap, s->m60_eligible_only);
    }
}
C
gcc -std=gnu11 -O2 -D_GNU_SOURCE -I"$fst" -include "$fst/fst_config.h" \
    "$out/m_wave_audit.c" "$fst"/{fstapi,fastlz,lz4}.c -lz -o "$out/m_wave_audit"
sha256sum "$fst"/{fstapi.c,fstapi.h,fst_config.h,fastlz.c,lz4.c} > "$out/fst-reader.sha256"
inputs=()
for mode in 0 1; do
    inputs+=("$main/replay-116937/DDR-$mode/"ffn-{gate-up,down}.fst "$active/replay-116950/DDR-$mode/ffn-g32-active.fst")
done
sha256sum "${inputs[@]}" > "$out/wave-inputs.sha256"
printf 'fst\tlane\tcycles\talloc_accepts\tstart_accepts\tstart_alloc_overlap\tm60_predicate_only\n' > "$out/handshakes.tsv"
for source in "${inputs[@]}"; do "$out/m_wave_audit" "$source" >> "$out/handshakes.tsv"; done
test "$(wc -l < "$out/handshakes.tsv")" -eq 19
awk -F'\t' 'NR>1 {cycles+=$3; alloc+=$4; starts+=$5; overlap+=$6; eligible+=$7} END {printf "C639_M_WAVE_AUDIT cycles=%d alloc=%d start=%d overlap=%d m60_predicate_only=%d\n",cycles,alloc,starts,overlap,eligible}' \
    "$out/handshakes.tsv" | tee "$out/summary.txt"
sha256sum "$out/"{m_wave_audit.c,fst-reader.sha256,wave-inputs.sha256,handshakes.tsv,summary.txt} > "$out/wave-results.sha256"
sha256sum -c "$out/wave-results.sha256"
