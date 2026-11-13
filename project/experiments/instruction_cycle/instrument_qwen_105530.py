"""Add passive edge witnesses to the exact 105530 RTL fixture and audit them."""

import argparse
import hashlib
import json
from pathlib import Path
import re


TOP_SHA256 = "4594f4bc1b1dd8cfb09453d20d36fb70227dd19d38129d5ae8666d93bb323421"
RUNNER_SHA256 = "6ea3179da4c715364bbc64fe5a1e72382a5aca6222edf5ccc50c0448992e6344"
CORE_PERIOD_PS = 10000
FIRST_EDGE_PS = 55000

OBSERVER = r"""
    // Sample all handshakes before nonblocking updates on the shared core edge.
    always @(posedge clk) begin : qwen_observe
        longint unsigned edge_ps, core_cycle;
        if (!reset) begin
            edge_ps=longint'($realtime/1ps);
            core_cycle=(edge_ps-64'd55000)/64'd10000+1;
            if (qkv_attention_datapath.prompt_start&&qkv_attention_datapath.prompt_ready)
                $display("QWEN_EDGE prompt_accept ps=%0d cycle=%0d generation=0 ddr_core_before=%0d",
                         edge_ps,core_cycle,core_cycle-1);
            if (qkv_attention_datapath.rms_active&&qkv_attention_datapath.prompt_req[0]&&
                qkv_attention_datapath.physical_req[0]&&qkv_attention_datapath.physical_ready[0])
                $display("QWEN_EDGE prompt_ddr_admit ps=%0d cycle=%0d generation=0 ddr_core_before=%0d address=%0d tag=%0d",
                         edge_ps,core_cycle,core_cycle-1,qkv_attention_datapath.physical_addr[63:0],
                         qkv_attention_datapath.physical_tag[63:0]);
            if (datapath.start&&datapath.ready)
                $display("QWEN_EDGE job_accept ps=%0d cycle=%0d generation=0",edge_ps,core_cycle);
            if (qwen_page_launch)
                $display("QWEN_EDGE page_launch ps=%0d cycle=%0d generation=%0d step=%0d page=%0d targets=%0d",
                         edge_ps,core_cycle,generation,page_step,page_index,targets);
            if (pm_valid&&pm_ready)
                $display("QWEN_EDGE pm_admit ps=%0d cycle=%0d generation=%0d domain=%0d tag=%0d address=%0d",
                         edge_ps,core_cycle,generation,pm_tag[19:16],pm_tag,pm_address);
            for (int lane=0;lane<LOCAL_COUNT;lane++) begin
                if (dr_valid[lane]&&dr_ready[lane])
                    $display("QWEN_EDGE descriptor_admit ps=%0d cycle=%0d generation=%0d target=%0d tag=%0d address=%0d",
                             edge_ps,core_cycle,generation,lane,dr_tag[lane],dr_address[lane]);
                if (provider_valid[lane]&&provider_ready[lane])
                    $display("QWEN_EDGE service_accept ps=%0d cycle=%0d generation=%0d target=%0d ticket=%0d schema=%0d op=%0d",
                             edge_ps,core_cycle,generation,lane,ticket[lane],provider_descriptor[lane][31:0],
                             provider_descriptor[lane][63:48]);
                if (provider_done_valid[lane]&&provider_done_ready[lane]) begin
                    $display("QWEN_EDGE service_retire ps=%0d cycle=%0d generation=%0d target=%0d ticket=%0d status=%0d read=%0d write=%0d",
                             edge_ps,core_cycle,generation,lane,provider_done_ticket[lane],provider_done_status[lane],
                             provider_done_reads[lane],provider_done_writes[lane]);
                    if (lane==3&&generation==7&&provider_done_ticket[lane]==10)
                        $display("QWEN_EDGE layer0_residual_commit ps=%0d cycle=%0d generation=%0d target=%0d ticket=%0d",
                                 edge_ps,core_cycle,generation,lane,provider_done_ticket[lane]);
                    if (lane==3&&generation==8&&provider_done_ticket[lane]==12)
                        $display("QWEN_EDGE layer1_rms_retire ps=%0d cycle=%0d generation=%0d target=%0d ticket=%0d",
                                 edge_ps,core_cycle,generation,lane,provider_done_ticket[lane]);
                end
            end
            if (page_done)
                $display("QWEN_EDGE page_commit ps=%0d cycle=%0d generation=%0d calls=%0d read=%0d write=%0d status=%0d",
                         edge_ps,core_cycle,done_generation,calls,done_reads,done_writes,done_status);
        end
    end
"""


def verify(condition, message):
    if not condition:
        raise ValueError(message)


def checked_text(path, digest):
    data = path.read_bytes()
    verify(hashlib.sha256(data).hexdigest() == digest, "unexpected frozen source: {}".format(path))
    return data.decode("utf-8")


def replace_once(text, original, replacement):
    verify(text.count(original) == 1, "expected exactly one source anchor: {}".format(original))
    return text.replace(original, replacement)


def instrument(source):
    base = source / "project/experiments/block_local_native"
    top_path = base / "test_native_decode638_product_replay.sv"
    runner_path = base / "run_decode638_q_tile_replay.sh"
    top = checked_text(top_path, TOP_SHA256)
    runner = checked_text(runner_path, RUNNER_SHA256)
    ending = "\r\n" if "\r\n" in top else "\n"
    top = replace_once(top, "logic page_done, retired, job_done;", "logic page_done, retired, job_done, qwen_page_launch;")
    top = replace_once(top, ".page_launch(),.page_terminal_valid(page_done)",
                       ".page_launch(qwen_page_launch),.page_terminal_valid(page_done)")
    top = replace_once(top, "endmodule", OBSERVER.replace("\n", ending) + "endmodule")

    # Preserve original simulator flags, argv and HDL. This run uses the archived
    # prepared data, which avoids executing an unrelated member's Python environment.
    runner = runner.replace("\r\n", "\n")
    start = runner.index('"$model_env/bin/python" -B "$EXP/$prepare"')
    stop = runner.index('readarray -t fields < <(', start)
    runner = runner[:start] + 'test "$scope" = history-final-product-ffn-next-rms\ntest -f "$g/program.json"\n' + runner[stop:]
    runner = replace_once(runner, "model_env=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern",
                          "model_env=/public/home/yuzelu/Melodydt/runs/issue-265/reference-env-20261113-01/venv")
    top_path.write_bytes(top.encode("utf-8"))
    runner_path.write_bytes(runner.encode("utf-8"))


def audit(log_path, frozen_log):
    log = log_path.read_text(encoding="utf-8")
    frozen = frozen_log.read_text(encoding="utf-8")
    prefixes = ("PRODUCT_PM ", "PRODUCT_PAGE_TERMINAL ", "DECODE_QKV_TERMINAL ", "PRODUCT_FFN_TERMINAL ",
                "PRODUCT_FDS_TERMINAL ", "HISTORY_KV_COMPLETE ", "NEXT_LAYER_RMS_COMMITTED ", "PASS ", "DDR_")
    expected = [line for line in frozen.splitlines() if line.startswith(prefixes)]
    verify(expected and expected == [line for line in log.splitlines() if line.startswith(prefixes)],
           "instrumented simulation changed a frozen terminal or DDR clock witness")
    events = []
    for line in log.splitlines():
        if not line.startswith("QWEN_EDGE "):
            continue
        _, kind, *values = line.split()
        event = dict(kind=kind, **{key: int(value) for key, value in (field.split("=") for field in values)})
        verify(event["cycle"] > 0 and event["ps"] == FIRST_EDGE_PS + (event["cycle"] - 1) * CORE_PERIOD_PS,
               "edge witness differs from synchronized DDR core clock")
        verify(not events or event["cycle"] >= events[-1]["cycle"], "nonmonotone edge sequence")
        events.append(event)

    def kind_rows(kind):
        return [event for event in events if event["kind"] == kind]

    jobs = kind_rows("job_accept")
    prompt_starts = kind_rows("prompt_accept")
    prompt_ddr = kind_rows("prompt_ddr_admit")
    starts, commits = kind_rows("page_launch"), kind_rows("page_commit")
    verify(len(jobs) == 1 and len(starts) == len(commits) == 8, "unexpected job or page witness count")
    verify(len(prompt_starts) == 1 and len(prompt_ddr) == 3 and
           prompt_starts[0]["cycle"] < prompt_ddr[0]["cycle"] < jobs[0]["cycle"], "unexpected prompt startup witnesses")
    verify(all(row["ddr_core_before"] == row["cycle"] - 1 for row in prompt_starts + prompt_ddr),
           "prompt witness differs from DDR counter before the sampled edge")
    previous = jobs[0]["cycle"] - 1
    for index, (start, commit) in enumerate(zip(starts, commits)):
        verify(start["step"] == 0 and start["page"] == index and start["generation"] == commit["generation"] == index + 1
               and previous < start["cycle"] < commit["cycle"] and commit["status"] == 0,
               "invalid page launch or commit sequence")
        previous = commit["cycle"]
    verify(jobs[0]["cycle"] <= starts[0]["cycle"], "launch precedes accepted job")
    verify(len(kind_rows("pm_admit")) == 58 and len(kind_rows("descriptor_admit")) == 786
           and len(kind_rows("service_accept")) == len(kind_rows("service_retire")) == 393,
           "unexpected PM, descriptor or service transfer count")
    boundaries = []
    for kind, generation, ticket, operation, read in (("layer0_residual_commit", 7, 10, 2, 16384),
                                                      ("layer1_rms_retire", 8, 12, 3, 32768)):
        selected = kind_rows(kind)
        verify(len(selected) == 1, "missing or duplicate {}".format(kind))
        edge = selected[0]
        match = lambda row: (row["generation"], row["target"], row["ticket"]) == (generation, 3, ticket)
        issue = [row for row in kind_rows("service_accept") if match(row)]
        retire = [row for row in kind_rows("service_retire") if match(row)]
        verify(match(edge) and len(issue) == len(retire) == 1 and (issue[0]["schema"], issue[0]["op"]) == (3, operation)
               and (retire[0]["status"], retire[0]["read"], retire[0]["write"]) == (0, read, 8192)
               and starts[generation - 1]["cycle"] <= issue[0]["cycle"] < edge["cycle"] == retire[0]["cycle"]
               <= commits[generation - 1]["cycle"], "invalid provider terminal for {}".format(kind))
        boundaries.append(edge)
    cycle_delta = boundaries[1]["cycle"] - boundaries[0]["cycle"]
    verify(cycle_delta > 0, "reversed layer boundary")
    clock = re.search(r"^DDR_CLOCK_PROOF period_ps=(\d+) first_edge_ps=(\d+) last_edge_ps=(\d+) steps=(\d+)$", log, re.M)
    verify(clock and tuple(map(int, clock.groups()[:2])) == (CORE_PERIOD_PS, FIRST_EDGE_PS)
           and int(clock[3]) == FIRST_EDGE_PS + (int(clock[4]) - 1) * CORE_PERIOD_PS
           and int(clock[4]) >= commits[-1]["cycle"], "run clock proof differs")
    return {"core_period_ps": CORE_PERIOD_PS, "first_edge_ps": FIRST_EDGE_PS, "total_cycles": int(clock[4]),
            "boundary_core_cycles": cycle_delta, "boundary_ps": cycle_delta * CORE_PERIOD_PS,
            "prompt_start": prompt_starts[0], "prompt_ddr_admissions": prompt_ddr,
            "page_starts": starts, "page_commits": commits, "boundaries": boundaries, "event_count": len(events)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    patch = commands.add_parser("patch")
    patch.add_argument("source", type=Path)
    inspect = commands.add_parser("audit")
    inspect.add_argument("log", type=Path)
    inspect.add_argument("baseline", type=Path)
    args = parser.parse_args()
    if args.command == "patch":
        instrument(args.source)
    else:
        print(json.dumps(audit(args.log, args.baseline), indent=2))


if __name__ == "__main__":
    main()
