"""Recompute declared capacity/serialization lower bounds; never launches model jobs."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def compute(c):
    assert c["data_link_bits"] % 8 == 0
    data_bytes = c["data_link_bits"] // 8
    private = sum(b["instances"]*b["private_bytes"] for b in c["blocks"])
    rom = sum(b["instances"]*b["rom_bytes"] for b in c["blocks"])
    endpoints = sum(b["instances"]*(b["rx"]+b["tx"]) for b in c["blocks"])+2*c["s_bank_count"]
    fifos = endpoints*c["endpoint_fifo_bytes"]
    banks = c["s_bank_count"]*c["s_bank_bytes"]
    multipliers = sum(b["instances"]*(b["native_mul8"]+b["rq_mul8"]) for b in c["blocks"])
    graph=c["logical_bindings_hybrid"]
    assert all(len(destinations)<=4 and all(d in graph for d in destinations) for destinations in graph.values())
    assert len(c["Gemma_V_destinations"])<=4 and "S4" in c["Gemma_V_destinations"]
    def reachable(start, goal):
        todo=[start]; seen=set()
        while todo:
            node=todo.pop()
            if node==goal:return True
            if node not in seen:
                seen.add(node);todo.extend(graph[node])
        return False
    assert all(reachable("D",n) and reachable(n,"D") for n in graph)
    a=c["attention_example"]; r=c["recurrence_tile"]; m=c["matmul_example"]
    scores = a["Q_tile"]*a["sequence"]*a["score_bytes"]
    ostate = a["Q_tile"]*a["head_dim"]*a["O_bytes"]
    # v1 uses a distinct 64B header beat. This intentionally differs from Issue39's8B header.
    def packet(payload):
        return c["packet_header_bytes"]+((payload+c["beat_bytes"]-1)//c["beat_bytes"])*c["beat_bytes"]
    wire = []
    for rows in (1,4):
        raw = packet(rows*16*4)
        rq8 = packet(rows*16)
        rq16 = packet(rows*16*2)
        wire.append({"rows": rows, "N": 16, "raw_i32_bytes": raw, "rq_i8_bytes": rq8,
                     "rq_i16_bytes": rq16, "raw_link_cycles": raw//data_bytes,
                     "rq_i8_link_cycles": rq8//data_bytes})
    # Source configs are frozen repository evidence; do not inspect ref-project.
    q=json.loads((HERE.parent/"model_selection/configs/qwen35.json").read_text())["text_config"]
    recurrent_layers=q["layer_types"].count("linear_attention")
    state_elements=recurrent_layers*q["linear_num_value_heads"]*q["linear_key_head_dim"]*q["linear_value_head_dim"]
    conv_channels=2*q["linear_num_key_heads"]*q["linear_key_head_dim"]+q["linear_num_value_heads"]*q["linear_value_head_dim"]
    state32=state_elements*4
    conv_elements=recurrent_layers*(q["linear_conv_kernel_dim"]-1)*conv_channels
    resident_capacity=32768+banks
    return {"schema":"block-candidate-analysis/1", "scope":"declared analytical inventory, not area/energy/cycle measurement",
        "inventory":{"signed8_multiplier_units":multipliers,"private_bytes":private,"bank_bytes":banks,
            "endpoint_fifo_count":endpoints,"endpoint_fifo_bytes":fifos,"rom_bytes":rom,
            "all_declared_memory_bytes":private+banks+fifos+rom},
        "matmul_lower_bounds":{"tile":m,"MACs":m["M"]*m["N"]*m["K"],
            "ideal_peak_cycles_lower_bound":m["M"]*m["N"]*m["K"]//256,
            "RQ_service_cycles_lower_bound":{str(lanes):(m["M"]*m["N"]*c["hypothetical_rq_II_cycles"]+lanes-1)//lanes
                                            for lanes in c["hypothetical_rq_lanes"]},
            "qualification":"RQ33 II28 is a sensitivity assumption; prior RQ32 RTL II28 does not qualify RQ33 or matrix utilization"},
        "attention":{"score_spill_bytes":scores,"O_i64_bytes":ostate,
            "score_plus_O_bytes":scores+ostate,"private_A_bytes":32768,
            "score_write_two_reads_bytes":3*scores,"conclusion":"scores plus O exceed A private RAM; S/backing traffic required for this canonical three-pass schedule"},
        "recurrence":{"resident_tile_bytes":r["K"]*r["V"]*r["state_bytes"],
            "qwen35_canonical_state_i32_bytes":state32,"conv_history_i16_bytes":conv_elements*2,
            "conv_history_f32_bytes":conv_elements*4,"R_plus_all_S_bytes_upper_bound":resident_capacity,
            "cold_once_per_token_state_read_write_bytes":2*state32,
            "qualification":"one matrix per value head, canonical layout assumed; actual backend allocation not measured; cold bound assumes every element loaded/written once, no resident/external-cache reuse"},
        "wire_examples":wire,
        "scale_params":{"rows":4,"channels":256,"static_M_r_bytes":256*5,"row_dynamic_M_r_bytes":4*256*5},
        "logical_graph":{"nodes":len(graph),"directed_edges":sum(len(v) for v in graph.values()),
            "maximum_TX_destinations":max(map(len,graph.values())),"D_reaches_all_and_returns":True,
            "qualification":"block-level directed reachability only; no contention, deadlock, pin or timing proof"},
        "decisions":c["decision_names"],"experiment_to_decision":c["decision_experiments"]}


def main():
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    if a.output.exists():
        raise ValueError("refuse to overwrite evidence")
    cfg=HERE/"candidate.json"
    out=compute(json.loads(cfg.read_text()))
    commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    sources=[Path(__file__),cfg,HERE.parent/"model_selection/configs/qwen35.json"]
    bindings={}
    for path in sources:
        name=path.relative_to(ROOT).as_posix();raw=path.read_bytes()
        blob=subprocess.run(["git","show",f"{commit}:{name}"],cwd=ROOT,capture_output=True)
        bindings[name]={"sha256":hashlib.sha256(raw).hexdigest(),"matches_commit":blob.returncode==0 and blob.stdout==raw}
    out["provenance"]={"commit":commit,"python":platform.python_version(),"files":bindings,
        "source_bound":all(b["matches_commit"] for b in bindings.values()),
        "note":"analytical derivations only; bindings distinguish committed source from preparation"}
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"output":str(a.output),"inventory":out["inventory"],"source_bound":out["provenance"]["source_bound"]}))


if __name__=="__main__":main()
