"""Join bounded exact-byte G evidence; external native artifacts stay indexed."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
WORK=ROOT/"work/YUZE-LU/250/physical"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def record(folder,name):
    base=WORK/folder
    index=json.loads((base/"index.json").read_text())
    row=index["files"][name]
    path=base/"evidence"/name
    assert path.stat().st_size==row["bytes"] and sha(path)==row["sha256"]
    return json.loads(path.read_text()),dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path))


def inventory():
    reports,bindings={},{}
    selected={
        "mapping":("g-map-03","mapping/g_s32/receipt.json"),
        "physical":("g-audit-01","audit/physical/five-macro-physical.json"),
        "density":("g-audit-01","audit/density/occupancy.json"),
        "drc":("g-audit-01","audit/drc/drc.json"),
        "function":("g-function-01","function/final-function.json"),
        "formal":("g-formal-01","formal/formal.json"),
        "delivery":("g-deliver-01","delivery/delivery.json"),
        "access":("g-access-02","tasks/access/access.json"),
        "frontend_mapping":("g-frontend-01","frontend/receipt.json")}
    for name,(folder,path) in selected.items():
        reports[name],bindings[name]=record(folder,path)
        if name!="density":
            assert reports[name]["passed"]
    d=reports["delivery"]
    odb=d["final_files"]["6_final.odb"]["sha256"]
    for name in ["drc","function","formal"]:
        assert reports[name]["final_odb_sha256"]==odb
        assert reports[name]["source_receipt_sha256"]==d["source_receipt_sha256"]
    assert reports["access"]["finite_full_escape_qualified"]
    assert reports["access"]["native_final_files"][d["final_files"]["6_final.odb"]["path"]]==odb
    assert reports["drc"]["original_gds"]["sha256"]==d["final_files"]["6_final.gds"]["sha256"]
    assert reports["drc"]["full_deck"]["total_items"]==0 and reports["drc"]["native_report"]==""
    assert all(reports["physical"]["checks"].values())
    assert all(reports["formal"]["strict_native_lec"]["checks"].values())
    assert len(reports["function"]["runs"])==9 and reports["function"]["oracle"]["actual_model_packets"]==2048
    baseline=json.loads(Path(__file__).with_name("baseline.json").read_text())["macros"]["G"]
    density=reports["density"]
    assert density==d["density"]
    assert density["active_outline_ratio"]>=baseline["occupied_outline_ratio"]
    assert density["active_core_ratio"]>=baseline["occupied_core_ratio"]
    simulation=WORK/"g-sim-07/results/summary.json"
    run=json.loads((WORK/"g-sim-07/result.json").read_text())
    assert run["passed"] and sha(simulation)==run["files"]["results/summary.json"]["sha256"]
    services=json.loads(simulation.read_text())["G_S128_services"]
    assert len(services)==15
    for service in services:
        assert sha(simulation.parent/service["log"])==service["sha256"]
    continuous=next(row for row in services if row["mode"]==0)
    assert [x["occupied_cycles"]for x in continuous["frames"]if not x["fault"]]==[107,14,32]
    assert continuous["done_events"][0]["after_ack_delta"]==0
    frontend=reports["frontend_mapping"]
    assert frontend["native_s_joint_summary_sha256"]==sha(simulation)
    assert frontend["source_sha256"]["project/rtl/w8a16_v1/g_s128_frontend.sv"]==sha(ROOT/"project/rtl/w8a16_v1/g_s128_frontend.sv")
    assert frontend["mapped_dff_count"]==874 and frontend["instantiated_hard_macros"]==0
    assert frontend["payload_hold_bytes"]==96 and frontend["added_sram_bytes"]==0
    mapping=reports["mapping"]
    assert mapping["source_sha256"]["project/rtl/w8a16_v1/g_s32.sv"]==sha(ROOT/"project/rtl/w8a16_v1/g_s32.sv")
    image=WORK/"g-deliver-01/layout.png"
    assert sha(image)==d["image"]["sha256"]
    return dict(schema="issue250-g32-native-results/1",passed=True,provider="P:G32_SILU; C/F:G16_MULTI unchanged",
        native_leaf_accepted=True,finite_full_escape_geometry_passed=True,bindings=bindings,
        native=dict(die_um=d["die_um"],functional_area_um2=density["active_area_um2"],
            occupied_outline_ratio=density["active_outline_ratio"],occupied_core_ratio=density["active_core_ratio"],
            corresponding_main_outline_ratio=baseline["occupied_outline_ratio"],corresponding_main_core_ratio=baseline["occupied_core_ratio"],
            setup_ns=d["timing"]["minimum_setup_ns"],hold_ns=d["timing"]["minimum_hold_ns"],
            full_native_gds_drc_items=0,native_signal_bits=204,final_files=d["final_files"],
            final_odb_sha256=odb,native_anchors=d["native_anchors"]),
        table=dict(logical_entries=257,logical_bytes=1028,lookup_calls_per_cycle=4,
            inferred_read_views=mapping["inferred_memories"],mapped_total_area_um2=mapping["mapped_area_um2"],
            physical_single_table_promised=False,instantiated_sram_bytes=0),
        coverage=dict(pure_g_actual_model_values=4096,pure_g_actual_ffn_sources=4,
            pure_g_all_oracle_packets=8048,pure_g_final_odb_tests=9,
            joint_g_s_actual_values=128,joint_g_s_actual_ffn_source="layer0/batch0",joint_g_s_mode_initial_tests=15,
            complete_model_reexecuted=False,complete_ffn_reexecuted=False),
        frontend=dict(physical_qualified=False,payload_register_bytes=96,other_state_bits=874-768,
            mapped_dff_count=874,mapped_area_um2=frontend["mapped_area_um2"],added_sram_bytes=0,
            phase="Ordinary S128 only; cannot overlap native S_P feeder",
            no_stall_to_final_ack_cycles="3*words+11; words=1,7,32 measured",frame128_values_to_ack=107,
            frame128_values_reads=64,frame128_values_writes=32,
            done_asserts_on_final_ack=True,earliest_clocked_done_take="following edge; separately charged by LC boundary convention",
            overflow_fault="drain accepted work; report committed prefix; LC discard/replay destination window"),
        access=dict(signal_bits=204,simultaneous_connected_bits=204,native_die_um=[240,240],
            charged_test_footprint_um=[320,320],charged_halo_um=40,
            native_obstruction_intersections=reports["access"]["native_m10_obstruction_intersections"],
            calibrated_upper_rc_qualified=False,combined_upper_300mhz_qualified=False),
        image=dict(path=image.relative_to(ROOT).as_posix(),sha256=sha(image)),
        hierarchical_lib_qualified=False,m11_m12_system_qualified=False,
        scope="Independent native TT1.1V/25C M1-M10 G leaf and finite uncalibrated escape only. Explicit new P S32 profile; no automatic C/F/new-model or integrated LC/frontend acceptance.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=inventory()
    if args.output:
        args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps(dict(passed=True,native=result["native"],frontend=result["frontend"])))
