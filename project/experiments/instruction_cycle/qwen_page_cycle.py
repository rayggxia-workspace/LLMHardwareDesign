"""Predict 105530 generation 1 through the selected Q weight prefix."""

import argparse
import json
from pathlib import Path

from qwen_descriptor_dma import TypedReadFabric, fetch_descriptor
from qwen_drl1_cycle import run_drl1
from qwen_native_control import decode_archive
from qwen_native_ddr import Proof, WINDOWS, fields, file_digest, require
from qwen_page_dispatch import dispatch, next_call, page_commit
from qwen_prompt_pm import INGRESS_BURSTS, EXPECTED_LC_BURSTS, EXPECTED_MC_BURSTS, predict as predict_pm


PROMPT_ACCEPT_EDGE = 2  # fixture anchor, with the same two-edge initial request gap as 108184
MODE_EDGE_SHA = (
    "f909bd275417ec983fa0185350b7ba29d76abfcd55a329051caf379ecb971781",
    "25671452cf3187cd97fa60a6616f919cd421857a227cd318fd083c766004e908",
)
PM_PREFIX_BURSTS = INGRESS_BURSTS + EXPECTED_LC_BURSTS + EXPECTED_MC_BURSTS
DESCRIPTOR_BURSTS = 2
DRL1_BURSTS = 8
SERVICES_MODELED = 2
PREDICTED_BURSTS = PM_PREFIX_BURSTS + SERVICES_MODELED * (DESCRIPTOR_BURSTS + DRL1_BURSTS) + DESCRIPTOR_BURSTS
K0_WEIGHT_RECORDS = 16
FULL_Q_WEIGHT_RECORDS = 256
AFTER_Q = FULL_Q_WEIGHT_RECORDS + 1
THROUGH_KV_STORE = AFTER_Q + 1


def marker(kind, cycle, **values):
    return {"kind": kind, "cycle": cycle, "generation": 1, **values}


def predict(archive, binary, config, output, embedding, mode, *, weight_records=0):
    page = decode_archive(archive)["pages"][0]

    def after_pm(prefix, ddr):
        control = dispatch(page, prefix["mc_config_writes"][-1][2], mode)
        fabric = TypedReadFabric(ddr)
        schedule = []
        markers = []
        for index, call in enumerate(page["calls"][:SERVICES_MODELED + 1]):
            descriptor = fetch_descriptor(fabric, call, control["descriptor_admissions"][0]["cycle"],
                                          serial=call["ticket"])
            require(descriptor["client_accepts"] == [row["cycle"] for row in control["descriptor_admissions"]]
                    and descriptor["local_tags"] == [row["tag"] for row in control["descriptor_admissions"]],
                    "controller and descriptor DMA disagree on the client handshake")
            for row in control["descriptor_admissions"]:
                markers.append(marker("descriptor_admit", row["cycle"], target=row["target"], tag=row["tag"],
                                      address=row["address"]))
            identity = {"target": call["target"], "ticket": call["ticket"]}
            markers.append(marker("service_accept", descriptor["service_accept"], **identity,
                                  schema=call["schema"], op=call["operation"]))
            record = {"call": identity, "dispatch": control, "descriptor": descriptor}
            schedule.append(record)
            if index == SERVICES_MODELED:
                break
            service = run_drl1(fabric, call, descriptor["service_accept"])
            record["service"] = service
            markers.append(marker("service_retire", service["service_retire"], **identity, status=0,
                                  read=512, write=512))
            control = next_call(page, index, service["service_retire"])
        result = {"scope": "105530 generation 1 startup to third service accept", "mode": mode,
                  "core_cycle_origin": prefix["core_cycle_origin"], "prompt_start_one_based_edge": PROMPT_ACCEPT_EDGE,
                  "schedule": schedule, "ddr_events": ddr.events, "markers": markers}
        if weight_records in (K0_WEIGHT_RECORDS, 2 * K0_WEIGHT_RECORDS, FULL_Q_WEIGHT_RECORDS, AFTER_Q, THROUGH_KV_STORE):
            from qwen_projection_front import first_weight_offer
            from qwen_projection_pipeline import run_k0
            front = first_weight_offer(call, descriptor["service_accept"], mode)
            through_q = weight_records >= FULL_Q_WEIGHT_RECORDS
            through_k1 = weight_records == 2 * K0_WEIGHT_RECORDS
            scope = "first Q provider retirement" if through_q else "first Q {} window".format("K1" if through_k1 else "K0")
            result["scope"] = "105530 generation 1 startup through " + scope
            result["projection_front"] = front
            result["projection_k0"] = run_k0(call, front, fabric, mode, through_k1=through_k1, through_q=through_q)
            if through_q:
                markers.append(marker("service_retire", result["projection_k0"]["service_retire"], **identity,
                                      status=0, read=FULL_Q_WEIGHT_RECORDS * 17 * 64, write=512))
                if weight_records >= AFTER_Q:
                    from qwen_post_projection import run_post_projection
                    through_store = weight_records == THROUGH_KV_STORE
                    post = run_post_projection(page, fabric, result["projection_k0"]["service_retire"],
                                               through_store=through_store)
                    result["scope"] = "105530 generation 1 through the first KVR1 " + ("retirement" if through_store else "write offer")
                    result["post_projection"] = post
                    for stage in post["stages"]:
                        stage_identity = stage["call"]
                        call = page["calls"][stage_identity["ticket"] - 1]
                        for row in stage["dispatch"]["descriptor_admissions"]:
                            markers.append(marker("descriptor_admit", row["cycle"], target=row["target"],
                                                  tag=row["tag"], address=row["address"]))
                        markers.append(marker("service_accept", stage["descriptor"]["service_accept"],
                                              **stage_identity, schema=call["schema"], op=call["operation"]))
                        if "service" in stage:
                            service = stage["service"]
                            read = 512 if call["ticket"] == 4 else service["read_bytes"]
                            markers.append(marker("service_retire", service["service_retire"], **stage_identity,
                                                  status=0, read=read, write=512))
            elif not through_k1:
                result["projection_k0"].pop("next_window", None)
        elif weight_records:
            from qwen_projection_front import first_weight_offer
            from qwen_weight_record import read_weight_record
            front = first_weight_offer(call, descriptor["service_accept"], mode)
            result["scope"] = "105530 generation 1 startup through the first P_SCOPE weight record"
            result["projection_front"] = front
            result["weight_record"] = read_weight_record(fabric, front["weight_source_offer"], front["weight_address"],
                                                         beats=front["weight_record_beats"])
            if weight_records == 2:
                result["scope"] = "105530 generation 1 startup through the first two P_SCOPE weight records"
            if weight_records >= 2:
                result["second_weight_record"] = read_weight_record(
                    fabric, front["second_weight_source_offer"], front["second_weight_address"],
                    beats=front["second_weight_record_beats"])
            if weight_records == 3:
                from qwen_projection_pair import projection_pair
                pair = projection_pair(call, front, result["weight_record"], result["second_weight_record"], mode)
                result["scope"] = "105530 generation 1 startup through the third P_SCOPE weight record"
                result["projection_pair"] = pair
                result["third_weight_record"] = read_weight_record(
                    fabric, pair["third_weight_source_offer"], pair["third_weight_address"],
                    beats=pair["third_weight_record_beats"])
        return result

    return predict_pm(archive, binary, config, output, embedding, mode, PROMPT_ACCEPT_EDGE, after_pm=after_pm,
                      allow_writes=weight_records == THROUGH_KV_STORE)


def observed_first_page(path, mode):
    require(file_digest(path) == MODE_EDGE_SHA[mode], "instrumented RTL evidence differs from 108208")
    result = []
    with path.open("r", encoding="ascii") as stream:
        for line in stream:
            prefix, kind, *items = line.split()
            require(prefix == "QWEN_EDGE", "invalid RTL edge record")
            if kind not in ("descriptor_admit", "service_accept", "service_retire", "page_commit"):
                continue
            row = {key: int(value) for key, value in (item.split("=") for item in items)}
            if row["generation"] != 1:
                break
            row.pop("ps")
            row["cycle"] -= 1  # 108208 marks the edge with a one-based counter
            result.append({"kind": kind, **row})
            if kind == "page_commit":
                break
    return result


def audit_wait_release(page, rows):
    """Check the MC/LC handoff given observed provider terminal edges."""
    retires = [row for row in rows if row["kind"] == "service_retire"]
    descriptors = [row for row in rows if row["kind"] == "descriptor_admit"]
    commits = [row for row in rows if row["kind"] == "page_commit"]
    count = len(page["calls"])
    require(len(retires) == count and len(descriptors) == DESCRIPTOR_BURSTS * count
            and len(commits) == 1 and (commits[0]["calls"], commits[0]["status"]) == (count, 0),
            "incomplete generation 1 WAIT evidence")
    for index, (retired, call) in enumerate(zip(retires, page["calls"])):
        require((retired["target"], retired["ticket"], retired["status"]) == (call["target"], call["ticket"], 0),
                "unexpected retired service at WAIT {}".format(index))
        if index == count - 1:
            break
        predicted = next_call(page, index, retired["cycle"])["descriptor_admissions"]
        offset = (index + 1) * DESCRIPTOR_BURSTS
        actual = [{key: row[key] for key in ("cycle", "target", "tag", "address")}
                  for row in descriptors[offset:offset + DESCRIPTOR_BURSTS]]
        require(predicted == actual, "WAIT release after ticket {} differs: {} vs {}".format(
            retired["ticket"], predicted, actual))
    predicted_commit = page_commit(page, retires[-1]["cycle"])
    require(predicted_commit == commits[0]["cycle"], "page commit differs after final observed service")
    return {"input": "observed_provider_retire", "matched_wait_handoffs": count - 1,
            "matched_next_descriptor_admissions": DESCRIPTOR_BURSTS * (count - 1),
            "matched_page_commit": predicted_commit}


def compare(archive, prediction, edge_log, *, weight_records=0):
    mode = prediction["mode"]
    require(mode in (0, 1), "invalid 105530 mode")
    expected = prediction["ddr_events"]
    bursts = PREDICTED_BURSTS + 17 * min(weight_records, FULL_Q_WEIGHT_RECORDS)
    if weight_records >= AFTER_Q:
        bursts += 3 * DESCRIPTOR_BURSTS + DRL1_BURSTS
    require(len(expected) == 4 * bursts, "incomplete DDR prefix prediction")
    proof = Proof(archive, WINDOWS["next_rms"][0])
    trace = "DDR-{}/transactions.tsv".format(mode)
    source = proof.path(trace)
    with source.open("r", encoding="ascii") as stream:
        for index, event in enumerate(expected):
            name, cycle, lane, tag, address = fields(stream.readline(), 5)
            actual = [name, int(cycle), int(lane), int(tag), int(address)]
            require(list(event) == actual, "DDR event {} differs: predicted {}, observed {}".format(index, event, actual))
    trace_sha = file_digest(source)
    proof.check(trace, trace_sha)

    observed = observed_first_page(edge_log, mode)
    wanted = prediction["markers"]
    marker_count = {FULL_Q_WEIGHT_RECORDS: 12, AFTER_Q: 23, THROUGH_KV_STORE: 24}.get(weight_records, 11)
    require(len(wanted) == marker_count and len(observed) > len(wanted), "incomplete dispatch marker prefix")
    for index, (event, actual) in enumerate(zip(wanted, observed)):
        require(event == actual, "control marker {} differs: predicted {}, observed {}".format(index, event, actual))
    page = decode_archive(archive)["pages"][0]
    result = {"mode": mode, "matched_ddr_bursts": bursts, "matched_ddr_events": len(expected),
              "matched_control_markers": len(wanted), "rtl_ddr_trace_sha256": trace_sha,
              "rtl_edge_trace_sha256": MODE_EDGE_SHA[mode], "conditional_wait_audit": audit_wait_release(page, observed)}
    if weight_records >= AFTER_Q:
        name = "DDR-{}/write-transactions.tsv".format(mode)
        source = proof.path(name)
        post = prediction["post_projection"]
        if weight_records == THROUGH_KV_STORE:
            write_events = post["write_events"]
            require(len(write_events) == 32, "incomplete first KV store")
        else:
            ready = post["write_ready"]
            address = ready["address"]
            write_events = [["admit", ready["first_ddr_write_accept_if_idle"], (address >> 6) & 1,
                             ready["tag"], address]]
        with source.open(encoding="ascii") as stream:
            for index, event in enumerate(write_events):
                kind, cycle, lane, tag, address = fields(stream.readline(), 5)
                actual = [kind, int(cycle), int(lane), int(tag), int(address)]
                require(list(event) == actual, "KV DDR event {} differs: {} vs {}".format(index, event, actual))
        write_sha = file_digest(source)
        proof.check(name, write_sha)
        result.update(matched_kv_ddr_events=len(write_events), rtl_kv_trace_sha256=write_sha)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="operation", required=True)
    make = commands.add_parser("predict")
    for name in ("archive", "binary", "config", "output", "embedding"):
        make.add_argument(name, type=Path)
    make.add_argument("--mode", type=int, choices=(0, 1), required=True)
    check = commands.add_parser("compare")
    for name in ("archive", "prediction", "edges"):
        check.add_argument(name, type=Path)
    for command in (make, check):
        weight = command.add_mutually_exclusive_group()
        weight.add_argument("--with-first-weight", dest="weight_records", action="store_const", const=1, default=0,
                            help="include the first 17-beat P_SCOPE record")
        weight.add_argument("--with-two-weights", dest="weight_records", action="store_const", const=2,
                            help="include both 17-beat records of the first drained P_SCOPE pair")
        weight.add_argument("--with-three-weights", dest="weight_records", action="store_const", const=3,
                            help="include the first P_SCOPE pair execution and the third drained weight record")
        weight.add_argument("--through-k0", dest="weight_records", action="store_const", const=K0_WEIGHT_RECORDS,
                            help="include all sixteen K0 P_SCOPE weight records")
        weight.add_argument("--through-k1", dest="weight_records", action="store_const", const=2 * K0_WEIGHT_RECORDS,
                            help="include the first two Q K128 windows and thirty-two weight records")
        weight.add_argument("--through-q", dest="weight_records", action="store_const", const=FULL_Q_WEIGHT_RECORDS,
                            help="include all 256 first Q weight records and the service retirement")
        weight.add_argument("--through-first-kv-offer", dest="weight_records", action="store_const", const=AFTER_Q,
                            help="include post-Q bias and the first KVR1 store offer")
        weight.add_argument("--through-first-kv-store", dest="weight_records", action="store_const", const=THROUGH_KV_STORE,
                            help="include strict DDR writes and retirement of the first KVR1 service")
    args = parser.parse_args()
    if args.operation == "predict":
        result = predict(args.archive, args.binary.resolve(), args.config.resolve(), args.output.resolve(),
                         args.embedding, args.mode, weight_records=args.weight_records)
    else:
        result = compare(args.archive, json.loads(args.prediction.read_bytes()), args.edges,
                         weight_records=args.weight_records)
        result["prediction_sha256"] = file_digest(args.prediction)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
