"""Independent Issue68 causal range/rescale receiver.

No producer arithmetic is imported. Python integers implement every product,
complete K reduction and signed nearest-even operation. Floating references are
diagnostics, never the input to a guard or a retry.
"""
import argparse
import copy
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import time
import zipfile

import numpy as np

I64 = (1 << 63) - 1


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def save_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for data in iter(lambda: f.read(8 << 20), b""):
            h.update(data)
    return h.hexdigest()


def digest_array(value):
    x = np.ascontiguousarray(value)
    return hashlib.sha256(str(x.dtype).encode() + str(x.shape).encode() + x.tobytes()).hexdigest()


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def rne(value, shift):
    """Signed integer nearest-even; Python integers avoid machine overflow."""
    n, s = int(value), int(shift)
    if s <= 0:
        return n << -s
    sign = -1 if n < 0 else 1
    q, r = divmod(abs(n), 1 << s)
    return sign * (q + (2 * r > 1 << s or (2 * r == 1 << s and q & 1)))


def bounds(bits):
    if bits == 16:
        return -32768, 32767
    if bits == 32:
        # Same physical endpoints as S16. INT32_MAX would silently expand range.
        return -(1 << 31), 32767 << 16
    raise ValueError("S16/S32 only")


def load_npz(path):
    with np.load(path, allow_pickle=False) as z:
        return {key: z[key] for key in z.files}


def artifact(path):
    return dict(bytes=Path(path).stat().st_size, sha256=sha(path))


def manifest(folder):
    folder = Path(folder)
    m = read_json(folder / "manifest.json")
    require(m.get("status") == "PASS", "execution manifest status")
    checked = {}
    for name, wanted in m["artifacts"].items():
        require(not Path(name).is_absolute() and ".." not in Path(name).parts, "safe artifact name")
        checked[name] = artifact(folder / name)
        require(checked[name] == {k: wanted[k] for k in ("bytes", "sha256")}, "artifact SHA/bytes " + name)
    return m, checked


def oracle_step(state, q, k, v, decay, beta, units, value_units, bits, fraction):
    """One complete token, returning unclipped proposal and hypothetical clipped output.

    The receiver compares a guard against the unclipped proposal before any
    publication. The output of a rejected proposal is never committed.
    """
    s = np.asarray(state)
    H, K, V = s.shape
    require(np.shape(q) == (H, K) and np.shape(k) == (H, K)
            and np.shape(v) == (H, V), "operand/state shape")
    require(fraction in (15, 31), "decay fraction")
    low, high = bounds(bits)
    require(np.all((s >= low) & (s <= high)), "stored state code bounds")
    for label, a, lo, hi in (("Q", q, -32767, 32767), ("K", k, -32767, 32767),
                              ("V", v, -32767, 32767), ("beta", beta, 0, 32768),
                              ("decay", decay, 0, 1 << fraction)):
        require(np.issubdtype(np.asarray(a).dtype, np.integer)
                and np.all((np.asarray(a) >= lo) & (np.asarray(a) <= hi)), "operand domain " + label)
    proposal = np.empty(s.shape, np.int64)
    output = np.empty((H, V), np.int64)
    maximum = {}

    def observe(label, n):
        n = int(n)
        require(-I64 <= n <= I64, "observed I64 " + label)
        maximum[label] = max(maximum.get(label, 0), abs(n))
        return n

    for h in range(H):
        d, b = int(decay[h]), int(beta[h])
        kk, qq = list(map(int, k[h])), list(map(int, q[h]))
        decayed = [[observe("decayed_state", rne(observe("decay_product", int(s[h, i, j]) * d), fraction))
                    for j in range(V)] for i in range(K)]
        for j in range(V):
            pdot = observe("prediction_dot", sum(decayed[i][j] * kk[i] for i in range(K)))
            pred = observe("prediction", rne(pdot, 15))
            val = observe("aligned_value", rne(int(v[h, j]), int(units[h]) - int(value_units[h])))
            residual = observe("residual", val - pred)
            delta = observe("correction", rne(observe("beta_product", residual * b), 15))
            for i in range(K):
                update = rne(observe("outer_product", kk[i] * delta), 15)
                proposal[h, i, j] = observe("state_sum", decayed[i][j] + update)
            total = observe("output_dot", sum(max(low, min(high, int(proposal[h, i, j]))) * qq[i] for i in range(K)))
            output[h, j] = rne(total, 15)
    guard = [int(np.count_nonzero((head < low) | (head > high))) for head in proposal]
    return proposal, np.clip(proposal, low, high).astype(np.int64), output, guard, maximum


def rescale(state, units, bad_heads):
    """Exactly one causal shift per bad head; repeated retries keep repeated RNE."""
    result = np.asarray(state, np.int64).copy()
    new_units = np.asarray(units, np.int16).copy()
    for h, bad in enumerate(bad_heads):
        if bad:
            require(int(new_units[h]) < 127, "unit rescale domain")
            for i in np.ndindex(result[h].shape):
                result[(h,) + i] = rne(int(result[(h,) + i]), 1)
            new_units[h] += 1
    return result, new_units


def metric(actual, reference):
    a, b = np.asarray(actual, np.float64), np.asarray(reference, np.float64)
    require(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all(), "metric shape/finiteness")
    return dict(relative_rmse=float(np.linalg.norm(a - b) / max(float(np.linalg.norm(b)), 1e-30)),
                max_abs=float(np.max(np.abs(a - b))))


def write_npz(path, arrays):
    with zipfile.ZipFile(path, "x", zipfile.ZIP_DEFLATED) as z:
        for name, array in sorted(arrays.items()):
            buf = io.BytesIO()
            np.save(buf, array, allow_pickle=False)
            info = zipfile.ZipInfo(name + ".npy", (2026, 10, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, buf.getvalue())


def stamp(state, units, epoch, version, position, sequence):
    return dict(state_sha256=digest_array(np.asarray(state, np.int64)), units=list(map(int, units)),
                epoch=int(epoch), version=int(version), position=int(position), sequence=str(sequence))


def verify_case(folder, row, source_folder, source_row):
    """Replay one predeclared condition, including rejection and transaction costs."""
    folder, source_folder = Path(folder), Path(source_folder)
    z = load_npz(source_folder / source_row["artifact"]["name"])
    a = load_npz(folder / row["artifact"]["name"])
    trace = read_json(folder / row["transaction_trace"]["name"])
    require(row["protocol_version"] == "causal-range/1" and row["max_rescale_retries"] == 8, "range protocol/retry bound")
    require(row["source_artifact"] == source_row["artifact"] and row["format"] == source_row["format"], "unchanged source artifact/format")
    require(row["quality_accepted"] is False and row["hardware_implemented"] is False, "execution versus quality/hardware separation")
    policy = row["policy"]
    require(policy in ("static_sat", "static_guard", "guard_rescale"), "range profile")
    bits, fraction = row["format"]["state_bits"], row["format"]["decay_fraction"]
    initial = z["state_initial"].astype(np.int64)
    units, vu = z["state_units"].astype(np.int16), z["value_units"].astype(np.int16)
    T = len(z["q"])
    H, K, V = initial.shape
    require((H, K, V) == (2, 128, 128) and T == (32 if row["role"] == "native" else 256), "predeclared full heads/window")
    require(row["requested_tokens"] == trace["requested_tokens"] == T, "requested token count")
    start = int(source_row["execution"]["final_position"]) - T
    sequence = source_row["format"]["sequence"]
    require(a["state_trace"].dtype == np.dtype("int16" if bits == 16 else "int32")
            and a["state_units_trace"].dtype == np.int8 and a["epoch_trace"].dtype == np.uint32
            and a["output_codes"].dtype == np.int64 and a["output_units"].dtype == np.int8, "typed state/scale/epoch/output containers")
    current, committed_units, epoch, version = initial.copy(), units.copy(), 0, 0
    require(np.array_equal(a["state_trace"][0], current) and np.array_equal(a["state_units_trace"][0], units)
            and int(a["epoch_trace"][0]) == 0, "initial published code/unit/epoch")
    observed, expected_events = {}, []
    physical_outputs, physical_states = [], [np.ldexp(current.astype(np.float64), units[:, None, None])]
    published_sats, rejection = 0, None
    products = dict(decay=0, prediction=0, beta=0, outer=0, output=0)
    for t in range(T):
        require(t < len(trace["tokens"]), "missing token transaction")
        before = stamp(current, committed_units, epoch, version, start + version, sequence)
        token = trace["tokens"][t]
        require(token["token"] == t and token["before"] == before, "published token predecessor/position")
        trial, trial_units, trial_epoch = current.copy(), committed_units.copy(), epoch
        committed = False
        for n in range(9):
            require(n < len(token["attempts"]), "missing proposal attempt")
            attempt = token["attempts"][n]
            require(attempt["attempt"] == n and attempt["trial_old_sha256"] == digest_array(trial)
                    and attempt["units"] == list(map(int, trial_units)) and attempt["epoch"] == trial_epoch,
                    "trial state/unit/epoch continuity")
            proposed, new, y, guard, maxima = oracle_step(trial, z["q"][t], z["k"][t], z["v"][t],
                                                        z["decay"][t], z["beta"][t], trial_units, vu, bits, fraction)
            bad = [bool(c) for c in guard]
            can_commit = not any(bad) or policy == "static_sat"
            if not can_commit:
                maxima.pop("output_dot")
            require(attempt["guard_count_by_head"] == guard and attempt["guard_count"] == sum(guard), "current proposal range guard")
            require(attempt["proposed_state_sha256"] == digest_array(proposed), "unclipped proposed integer state")
            require(attempt["output_work_performed"] == can_commit, "range guard before output work")
            require(attempt["observed_absolute_max"] == maxima, "proposal intermediate integer maxima")
            require(attempt["observed_signed_bits"] == {k: max(1, int(v).bit_length() + 1) for k, v in maxima.items()}, "observed conservative signed bits")
            for key, value in maxima.items():
                observed[key] = max(observed.get(key, 0), value)
            for key in ("decay", "prediction", "outer"):
                products[key] += H * K * V
            products["beta"] += H * V
            if can_commit:
                products["output"] += H * K * V
                require(attempt["outcome"] == "COMMIT" and len(token["attempts"]) == n + 1, "successful proposal terminates retry")
                after = stamp(new, trial_units, trial_epoch, version + 1, start + version + 1, sequence)
                expected_commit = dict(old=before, new=after, output_sha256=digest_array(y),
                                       publication="state/output/units/epoch one token commit")
                require(token["outcome"] == "COMMITTED" and token["commit"] == expected_commit, "atomic state/output/scale/epoch publication")
                version += 1
                require(np.array_equal(a["state_trace"][version], new), "integer state oracle")
                require(np.array_equal(a["output_codes"][version - 1], y), "integer output oracle")
                require(np.array_equal(a["state_units_trace"][version], trial_units)
                        and np.array_equal(a["output_units"][version - 1], trial_units)
                        and int(a["epoch_trace"][version]) == trial_epoch, "committed state/output unit epoch oracle")
                current, committed_units, epoch = new.copy(), trial_units.copy(), trial_epoch
                physical_outputs.append(np.ldexp(y.astype(np.float64), trial_units[:, None]))
                physical_states.append(np.ldexp(current.astype(np.float64), trial_units[:, None, None]))
                published_sats += sum(guard) if policy == "static_sat" else 0
                committed = True
                break
            require(attempt["outcome"] == "ABORT_RANGE", "guard failure abort")
            if policy != "guard_rescale" or n == 8:
                rejection = dict(token=t, reason="state range guard", attempt=n)
                break
            if any(int(trial_units[h]) >= 127 for h in range(H) if bad[h]) or trial_epoch + 1 >= 1 << 32:
                rejection = dict(token=t, reason="exponent/epoch domain guard", attempt=n)
                break
            previous, old_units = trial.copy(), trial_units.copy()
            trial, trial_units = rescale(trial, trial_units, bad)
            trial_epoch += 1
            changed_heads = [h for h, value in enumerate(bad) if value]
            cells = len(changed_heads) * K * V
            count_nonexact = sum(int(previous[h, i, j]) != 2 * int(trial[h, i, j])
                                 for h in changed_heads for i in range(K) for j in range(V))
            expected_events.append(dict(token=t, after_attempt=n, heads=changed_heads, trial_epoch=trial_epoch,
                old_units=list(map(int, old_units)), new_units=list(map(int, trial_units)),
                old_trial_state_sha256=digest_array(previous), recoded_trial_state_sha256=digest_array(trial),
                state_scan_elements=cells, RNE_elements=cells, nonexact_halvings=count_nonexact,
                state_read_bytes=cells * (bits // 8), state_write_bytes=cells * (bits // 8),
                scale_descriptor_write_bytes=len(changed_heads), epoch_descriptor_write_bytes=4,
                published=False, cause="current token proposal range/I64 guard only"))
        if not committed:
            require(len(token["attempts"]) == rejection["attempt"] + 1, "rejection terminates retry")
            require(token["outcome"] == "REJECTED" and token["after"] == before, "abort retains published state/unit/epoch/version")
            require(len(trace["tokens"]) == t + 1, "no later token after causal rejection")
            break
    require(trace["rescale_events"] == expected_events, "causal recode read/write/RNE/metadata events")
    require(trace["rejection"] == row["rejection"] == rejection, "rejection status")
    status = "REJECTED_GUARD" if rejection else "EXECUTED"
    require(row["status"] == trace["status"] == status and row["committed_tokens"] == trace["committed_tokens"] == version, "execution/rejection count")
    require(a["state_trace"].shape == (version + 1, H, K, V) and a["state_units_trace"].shape == (version + 1, H)
            and a["epoch_trace"].shape == (version + 1,) and a["output_codes"].shape == (version, H, V)
            and a["output_units"].shape == (version, H), "complete committed prefix only")
    final = stamp(current, committed_units, epoch, version, start + version, sequence)
    require(row["final"] == trace["final"] == final, "final published state")
    require(trace["saturations_published"] == row["saturations_published"] == published_sats, "published saturation count")
    require(trace["observed_absolute_max"] == observed and trace["observed_signed_bits"] == row["observed_signed_bits"]
            == {k: max(1, int(v).bit_length() + 1) for k, v in observed.items()}, "whole-run integer widths")
    attempts = sum(len(token["attempts"]) for token in trace["tokens"])
    cost = dict(state_bytes=H * K * V * (bits // 8), minimum_old_new_atomic_payload_bytes=2 * H * K * V * (bits // 8),
        software_trial_copy_not_free_hardware=True, guard_scan_elements=attempts * H * K * V,
        integer_products_executed=products, width_rejected_attempts_cost_unqualified=0,
        rescale_scan_elements=sum(e["state_scan_elements"] for e in expected_events),
        rescale_RNE_elements=sum(e["RNE_elements"] for e in expected_events),
        rescale_state_read_bytes=sum(e["state_read_bytes"] for e in expected_events),
        rescale_state_write_bytes=sum(e["state_write_bytes"] for e in expected_events),
        rescale_scale_epoch_write_bytes=sum(e["scale_descriptor_write_bytes"] + 4 for e in expected_events),
        commit_metadata_candidate_bytes_per_token=64 + H + 4, attempts=attempts,
        schedule_scope="logical stage/product/event counts only; materialize/recompute and real ports/shadow supplied by service experiment; rejected width attempts unqualified")
    require(row["cost"] == trace["cost"] == cost, "independent scan/product/metadata/atomic storage costs")
    require(row["rescale_waves"] == len(expected_events) and row["rescaled_head_events"] == sum(len(e["heads"]) for e in expected_events), "recode wave/head count")
    if policy == "static_sat":
        require(np.array_equal(a["state_trace"], z["state_trace"]) and np.array_equal(a["output_codes"], z["output_codes"])
                and row["static_original_bitexact"] is True, "original static baseline retained bitwise")
    else:
        require(row["static_original_bitexact"] is False, "baseline flag scope")
    metrics = []
    if version:
        y, s = np.stack(physical_outputs), np.stack(physical_states)
        for n in sorted({1, min(8, version), min(32, version), version}):
            sample = dict(steps=n, output_vs_native=metric(y[:n], z["native_output"][:n]),
                          state_vs_FP64_replay=metric(s[n], z["FP64_state_reference"][n]))
            if "native_state_reference" in z:
                sample["state_vs_native_capture"] = metric(s[n], z["native_state_reference"][n])
            metrics.append(sample)
        require(len(metrics) == len(row["error_by_length"]), "length diagnostic coverage")
        for actual, wanted in zip(row["error_by_length"], metrics):
            require(actual["steps"] == wanted["steps"], "length diagnostic identity")
            for field in wanted:
                if field == "steps":
                    continue
                for stat, value in wanted[field].items():
                    require(math.isclose(actual[field][stat], value, rel_tol=1e-8, abs_tol=1e-10), "independent physical unit metric")
    else:
        require(row["error_by_length"] == [], "no metric for uncommitted output")
    return dict(id=row["id"], execution_pass=True, range_pass=version == T and published_sats == 0,
                quality_accepted=False, hardware_implemented=False, requested_tokens=T, committed_tokens=version,
                saturations_published=published_sats, rescale_waves=len(expected_events),
                complete_K_Pythonint_oracle=True, error_by_length=metrics, cost=cost,
                abort_preserves_published_state_unit_epoch=True)


def selected(row):
    if row["role"] == "native":
        return row["source_id"] in ("evaluation.S16.D31", "evaluation.S32.D31")
    return row["source_id"] in ("layer0-end8192.S16.D31", "layer0-end8192.S32.D31")


def rehashed_negative(folder, row, out, mutation):
    """Rewrite a real NPZ and its two descriptor layers before semantic rejection."""
    folder, out = Path(folder), Path(out)
    out.mkdir()
    meta = read_json(folder / "manifest.json")
    rows = read_json(folder / "range-results.json")
    target = next(r for r in rows if r["id"] == row["id"])
    name = target["artifact"]["name"]
    for filename in meta["artifacts"]:
        if filename in (name, "range-results.json"):
            continue
        try:
            (out / filename).hardlink_to(folder / filename)
        except OSError:
            shutil.copyfile(folder / filename, out / filename)
    arrays = load_npz(folder / name)
    if mutation == "output":
        arrays["output_codes"][0, 0, 0] += 1
    elif mutation == "epoch":
        arrays["epoch_trace"][1] += 1
    else:
        raise ValueError("negative mutation")
    write_npz(out / name, arrays)
    target["artifact"].update(artifact(out / name))
    meta["artifacts"][name] = artifact(out / name)
    save_json(out / "range-results.json", rows)
    meta["artifacts"]["range-results.json"] = artifact(out / "range-results.json")
    save_json(out / "manifest.json", meta)
    manifest(out)
    return target


def execute(integer, repeat, native, legacy, out, binding=None):
    begin = time.monotonic()
    integer, repeat, native, legacy, out = map(Path, (integer, repeat, native, legacy, out))
    require(not out.exists(), "new audit output directory")
    out.mkdir(parents=True)
    m, receipts = manifest(integer)
    m2, receipts2 = manifest(repeat)
    require(m["schema"] == m2["schema"] == "issue68-range/1" and m["suite"] == m2["suite"], "range source schema/suite")
    require(receipts == receipts2 and m["source"] == m2["source"], "two-round scientific bytes and source identity")
    source = dict(receive_range_sha256=sha(__file__))
    if binding:
        b = read_json(binding)
        require(b["receive_range_sha256"] == source["receive_range_sha256"], "independent receiver source binding")
        source.update(commit=b["commit"], binding_sha256=sha(binding))
    original = {}
    for role, source_folder in (("native", native), ("legacy", legacy)):
        if role not in m["source"]:
            continue
        original_m, original_receipts = manifest(source_folder)
        require(sha(source_folder / "manifest.json") == m["source"][role]["manifest_sha256"]
                and sha(source_folder / "state-results.json") == m["source"][role]["records_sha256"], "original Issue66 input source binding")
        original[role] = (source_folder, {r["id"]: r for r in read_json(source_folder / "state-results.json")})
    rows = read_json(integer / "range-results.json")
    checks = []
    for row in rows:
        for field in ("artifact", "transaction_trace"):
            name = row[field]["name"]
            require(row[field] == dict(name=name, **receipts[name]), "row artifact descriptor " + field)
        if selected(row):
            folder, lookup = original[row["role"]]
            checks.append(verify_case(integer, row, folder, lookup[row["source_id"]]))
    expected = 6 * len(original)
    require(len(checks) == expected, "predeclared both precision/allthree profile oracle coverage")
    negatives = []
    good = next(row for row in rows if selected(row) and row["policy"] == "guard_rescale" and ".S32.D31." in row["id"])
    source_folder, lookup = original[good["role"]]
    for mutation, label in (("output", "integer output oracle"), ("epoch", "committed state/output unit epoch oracle")):
        target = out / ("rehashed-" + mutation)
        negative_row = rehashed_negative(integer, good, target, mutation)
        try:
            verify_case(target, negative_row, source_folder, lookup[good["source_id"]])
        except AssertionError as exc:
            require(label in str(exc), "negative rejected for intended semantics: " + str(exc))
            negatives.append(dict(mutation=mutation, artifact_SHA_passed=True, status="REJECTED_INDEPENDENT_SEMANTICS", error=str(exc)))
        else:
            raise AssertionError("rehashed actual negative accepted")
    receipt = dict(status="PASS_INDEPENDENT_ARITHMETIC", source=source, integer_manifest_sha256=sha(integer / "manifest.json"),
        two_rounds=dict(all_scientific_SHA_identical=True, artifacts=len(receipts), arithmetic_rounds=1),
        selected_conditions=checks, negative_checks=negatives, conditions_SHA_checked=len(rows),
        selection="native evaluation S16/S32 D31 full32 and legacy layer0/end8192 S16/S32 D31 full256, allthree causal profiles; other conditions SHA only",
        seconds=time.monotonic() - begin, quality_accepted=False, hardware_implemented=False,
        limitation="Software integer arithmetic and causal transaction evidence, no RTL/PPA, no whole-model quality or throughput; Issue66 source encodings reused without requalifying source floating bridges")
    save_json(out / "audit.json", receipt)
    print(json.dumps(dict(status=receipt["status"], conditions=len(checks), negatives=len(negatives))), flush=True)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for option in ("integer", "repeat", "native", "legacy", "out"):
        p.add_argument("--" + option, type=Path, required=True)
    p.add_argument("--binding", type=Path)
    args = p.parse_args()
    execute(args.integer, args.repeat, args.native, args.legacy, args.out, args.binding)


if __name__ == "__main__":
    main()
