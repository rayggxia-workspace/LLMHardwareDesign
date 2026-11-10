"""Independent post-run work, FIFO, lifecycle and performance admission audit."""
import argparse
import json
from pathlib import Path

def analyze(root):
    reports = [json.loads(path.read_text()) for path in sorted(root.glob("*/report.json"))]
    reports.sort(key=lambda report: (report["plan"] != "baseline-Xreg", report["plan"]))
    assert len(reports) == 8 and reports[0]["plan"] == "baseline-Xreg"
    assert all(report["passed"] and not report.get("error") for report in reports)
    baseline = reports[0]["results"][-1]["result"]
    historical = json.loads((root / "historical-baseline.json").read_text())
    old = next(case["result"] for case in historical["results"] if case["bw_MB_s"] == 51200)
    assert baseline["tokens_per_second"] == old["tokens_per_second"] == 9.21564723269
    assert baseline["detail"]["end_subcycles"] == old["detail"]["end_subcycles"]
    equal_fields = ("logical_read_bytes", "logical_write_bytes", "read_bus_bytes", "write_bus_bytes",
                    "M_commands", "M_tiles", "vector_work_ticks", "M_work_ticks", "adapter_work_ticks",
                    "KV_state_write_bytes", "dma_descriptors")
    rows = []
    for report in reports:
        result = report["results"][-1]["result"]
        for field in equal_fields:
            assert result[field] == baseline[field], (report["plan"], field)
        for field in ("FFNs", "G_values", "G_cycles", "scale_metadata_bytes", "partial_read_bytes", "partial_write_bytes"):
            assert result["closure"][field] == baseline["closure"][field], (report["plan"], field)
        assert report["input_trace_SHA256"] == reports[0]["input_trace_SHA256"]
        sx = result["shared_x"]
        assert all(p["peak_reserved_B"] <= 256 and p["issued"] == p["arrived"] == p["consumed"] for p in sx["ports"])
        if sx["mode"] == 1:
            assert sx["objects"] == result["closure"]["FFNs"] == 36
            assert sx["fill_B"] == 36 * 4096
            assert sx["read_B"] == 36 * 2 * (11008 // 8) * (2048 // 128) * 256
            assert sx["descriptor_count"] == sx["read_B"] // 256
        if sx["mode"] == 4:
            loads = 36 * (11008 // 128) * (2048 // 128) * 3
            assert sx["local_S_X_read_B"] == loads * 256
            assert sx["local_tile_reused_M_commands"] == 36 * 2 * (11008 // 8) * (2048 // 128) - loads
            if "local_A_loads" in sx:
                assert sx["local_A_loads"] == loads
                assert sx["local_A_load_prepare_cycles"] == loads * sx["descriptor_cycles"]
        if sx.get("early_X_copy"):
            assert sx["early_copy_source_B"] == sx["early_copy_dest_B"] == 36 * 3 * 4096
            assert sx["early_copy_holding_B_per_P"] == 16
        declared_sram_peak = result["closure"]["S_peak"] + (4096 if sx["mode"] >= 2 else 0)
        # The new raw M has no A SRAM. Charge the explicit frontend registers,
        # then remove their512B historical double-A reservation from private S.
        sram_peak = declared_sram_peak - (512 if sx["mode"] >= 3 else 0)
        assert sram_peak <= 16384
        rows.append(dict(plan=report["plan"], tokens_s=result["tokens_per_second"],
                         latency_ms=result["seconds"] * 1000,
                         throughput_change_pct=(result["tokens_per_second"] / baseline["tokens_per_second"] - 1) * 100,
                         at_least_baseline=result["tokens_per_second"] >= baseline["tokens_per_second"],
                         FFN_ms=result["spans_ticks"]["FFN_closure"] / 300000,
                         FFN_S_peak_B=sram_peak, historical_conservative_S_peak_B=declared_sram_peak,
                         external_A_register_B_per_P=sx.get("new_A_slot_register_B_per_P", 0),
                         independent_full_X_B_per_P=result["closure"]["full_A_register_bytes_per_P"],
                         pool_SRAM_B=sx["pool_capacity_B"], FIFO_B_per_P=sx["FIFO_B_per_P"] if sx["mode"] == 1 else 0,
                         shared_service=sx))
    return dict(passed=True, source_base="85fe7989b11a95725c9b1bc6daee085f74a500b8",
                historical_baseline_reproduced=True, work_conservation_fields=list(equal_fields),
                input_trace_SHA256=reports[0]["input_trace_SHA256"], rows=rows,
                evidence_scope="SystemC timing + independent S16 transport oracle; inherited PR249 quality, no new full-model numeric RTL/physical admission")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.root)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
