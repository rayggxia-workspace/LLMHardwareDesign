"""Offline audit of Issue248 follow-up evidence; no model/EDA/server execution."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_runs(root):
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    runs = {}
    count = 0
    for run in index["runs"]:
        encoded = (root / run["archive"]).read_bytes()
        raw = base64.b64decode(b"".join(encoded.split()), validate=True)
        assert digest(raw) == run["archive_SHA256"], run["name"]
        files = {}
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            for member in archive:
                path = PurePosixPath(member.name)
                assert member.isfile() and not path.is_absolute() and ".." not in path.parts
                assert member.name not in files and member.size <= 5 * 1024 * 1024
                files[member.name] = archive.extractfile(member).read()
        assert set(files) == set(run["members_SHA256"]), run["name"]
        for name, expected in run["members_SHA256"].items():
            assert digest(files[name]) == expected, (run["name"], name)
        for line in files["source.sha256"].decode().splitlines():
            expected, name = line.split(maxsplit=1)
            name = name.lstrip("*").replace("\\", "/")
            assert digest(files[name]) == expected, (run["name"], "execution source", name)
        if "collected.json" in files:
            receipt = json.loads(files["collected.json"])
            if "files_SHA256" in receipt:
                assert receipt["all_SHA256_match"]
                hashes = receipt["files_SHA256"]
                if "archive_SHA256" in receipt:
                    assert digest(files["evidence.tar.gz"]) == receipt["archive_SHA256"]
            else:
                hashes = {name: item["sha256"] for name, item in receipt.items()}
            for name, expected in hashes.items():
                assert digest(files[name]) == expected, (run["name"], "collected", name)
        count += len(files)
        runs[run["name"]] = files
    return index, runs, count


def audit(root):
    index, runs, members = load_runs(root)
    assert len(runs) == 11
    inventory = json.loads((root / "inventory.json").read_text(encoding="utf-8"))
    expected_roots = {"issue248-stream-quant-20261110-%02d" % i for i in range(1, 42)}
    expected_roots |= set(runs) | {"issue248-public-w8-20261110-01"}
    assert {r["name"] for r in inventory["remote"]} == expected_roots
    assert len(inventory["coverage"]) == len(expected_roots) == 53
    repository = Path(__file__).resolve().parents[3]
    for record in inventory["coverage"]:
        assert (repository / record["repository_entry"]).exists(), record
    extras = json.loads((root / "early-extra-sha256.json").read_text(encoding="utf-8"))
    for name, expected in extras.items():
        run_name, relative = name.split("/", 1)
        assert digest(runs[run_name][relative]) == expected
    expected_states = {"102035": "FAILED", "102036": "COMPLETED", "102037": "CANCELLED",
                       "102038": "CANCELLED", "102039": "COMPLETED", "102042": "COMPLETED",
                       "102044": "FAILED", "102045": "COMPLETED", "102046": "COMPLETED",
                       "102047": "FAILED", "102048": "COMPLETED"}
    checked_states = {}
    for line in (root / "slurm-rechecked.txt").read_text(encoding="utf-8").splitlines()[1:]:
        fields = line.split("|")
        if len(fields) >= 3:
            checked_states[fields[0]] = fields[1]
    for run in index["runs"]:
        assert run["slurm_state"] == checked_states[run["job_id"]]
        assert run["slurm_state"].startswith(expected_states[run["job_id"]])

    narrow = json.loads(runs["issue248-narrow-20261110-05"]["summary.json"])
    assert len(narrow["profiles"]) == 6 and narrow["all_six_quality_gates_passed"]
    assert all(p["admitted"] and p["clipped"] == 0 and p["decode"]["top1_fraction"] == 1
               for p in narrow["profiles"])
    chosen = next(p for p in narrow["profiles"] if p["state_bits"] == p["mid_bits"] == 32)
    timing = json.loads(runs["issue248-narrow-20261110-02"]["timing.json"])
    assert timing["passed"] and len(timing["cases"]) == 24
    selected_time = next(p for p in narrow["timing"]["cases"] if p["name"] == "S32-extra1-mid1")
    assert selected_time["tokens_s"] == 9.21564723269
    numeric = json.loads(runs["issue248-narrow-20261110-01"]["numeric.json"])
    assert numeric["passed"] and len(numeric["cases"]) == 4
    assert sum(len(c["profiles"]) for c in numeric["cases"]) == 28
    assert numeric["replay_total_values"] == 44032

    tables = json.loads(runs["issue248-small-g-20261110-01"]["summary.json"])
    assert len(tables["rows"]) == 6
    assert [r["entries"] for r in tables["rows"] if r["quality_admitted"]] == [2049, 1025, 513, 257, 129]
    rejected = next(r for r in tables["rows"] if r["entries"] == 65)
    assert not rejected["quality_admitted"] and rejected["decode"]["top1_fraction"] == 15 / 16
    assert next(r for r in tables["rows"] if r["entries"] == 2049)["PPL"] == chosen["PPL"]

    report_count, layout_runs, rows = 0, 0, []
    for suffix in ("02", "03", "05"):
        files = runs["issue248-stream-feed-20261110-" + suffix]
        for name, raw in sorted(files.items()):
            if not name.endswith("/report.json"):
                continue
            report = json.loads(raw)
            assert report["passed"] and not report.get("error")
            micro = report["micro"]["result"]
            assert (micro["logical_read_bytes"], micro["logical_write_bytes"], micro["M_commands"]) == (19968, 768, 16)
            if "layout_check" in report:
                assert report["layout_check"]["passed"] and report["layout_check"]["cases"] == 256
                layout_runs += 1
            report_count += 1
            for case in report["results"]:
                z = case["result"]
                sf = z["stream_feed"]
                for port in sf["ports"]:
                    assert port["reserved_peak_B"] <= report["FIFO_B"]
                    assert port["issued_beats"] == port["arrived_beats"] == port["consumed_beats"]
                rows.append(dict(plan=report["plan"], label=case["label"], bandwidth_GB_s=case["bw_MB_s"] / 1000,
                                 tokens_s=z["tokens_per_second"], ingress_B_cycle=report.get("ingress_B_cycle", 64),
                                 FIFO_B_per_P=report["FIFO_B"], X_mode=report["X_mode"],
                                 A_port_B_cycle=case["X_A_port_B_cycle"], read_B=z["logical_read_bytes"],
                                 write_B=z["logical_write_bytes"], M_commands=z["M_commands"],
                                 FIFO_wait_cycles=sf["FIFO_wait_cycles"], FIFO_starve_events=sf["FIFO_starve_events"],
                                 ports=sf["ports"], FFN_link_B=z["closure"]["link_payload_bytes"],
                                 FFN_ms=z["spans_ticks"].get("FFN_closure", 0) / 300000,
                                 FFN_declared_S_B=z["closure"]["S_peak"],
                                 FFN_budget_with_X_B=z["closure"]["S_peak"] + (4096 if report["X_mode"] == 1 else 0)))
    assert report_count == 20 and layout_runs == 12 and len(rows) == 41
    baseline = {r["bandwidth_GB_s"]: r for r in rows if r["plan"] == "frozen-bank4-Xreg"}
    assert baseline[51.2]["tokens_s"] == selected_time["tokens_s"]
    for row in rows:
        ref = baseline[row["bandwidth_GB_s"]]
        for field in ("read_B", "write_B", "M_commands"):
            assert row[field] == ref[field], (row["plan"], field)

    return dict(
        audited_archives=len(runs), audited_members=members, indexed_server_roots=len(expected_roots),
        historical_failed_jobs=["102035", "102044", "102047"], cancelled_jobs=["102037", "102038"],
        selected_design=dict(external_GB_s=51.2, weight_bits=8, activation_bits=16,
                             persistent_state="S32/Q16", stored_Mid="S32/Q16", private_S_KiB=16,
                             no_S128="New production target; historical wide RTL remains reference only",
                             temporary_S64="Only bounded transient multiplies if necessary; no vector/psum residency",
                             G_LUT_priority_candidate=257, G_LUT_fallback_candidate=513, G_LUT_decision="undecided",
                             dedicated_X_KiB="optional; existing-S residency is conditional candidate",
                             weight_supply="four-bank baseline versus bounded streaming remains undecided"),
        narrow_quality=chosen, all_narrow_quality=narrow["profiles"], narrow_timing=narrow["timing"],
        frozen_FFN_numeric=numeric["cases"],
        small_G=tables["rows"], stream_reports_passed=report_count, stream_micro_cases=report_count,
        proposed_layout_unique_synthetic_cases=256, proposed_layout_repeated_runs=layout_runs,
        stream_full_trace_cases=rows,
        qualification="Historical evidence audited offline; no new ML/RTL/SystemC/P&R execution. Narrow/grouped MLP and G quality only; other projections screening/Norm/Attention/KV retain floating point. No new combined small-G/X-in-S/streaming numerical RTL or physical qualification.")


def case_tables(result):
    lines = ["# Issue248 后续实验全部配置附表", "",
             "由 `followup_report.py --write-summary` 从已核对的原始归档生成。决策、范围和未评估项见[主台账](issue-248-followup-design-ledger.md)。",
             "每项的原始日志、全量指标、执行源和工具/输入引用见 `work/YUZE-LU/248/followup/index.json` 对应包。下表保留所有配置，不只列最佳行。",
             "", "## 四个实际FFN的28种独立窄化对照", "",
             "| 层/batch | 配置 | 最终输出最大绝对误差 | 相对L2 | 逐位相同比例 | gate/up/down最大前缀位数 |",
             "|---|---|---:|---:|---:|---|"]
    for case in result["frozen_FFN_numeric"]:
        for profile in case["profiles"]:
            z = profile["output"]
            bits = "/".join(str(profile[x]["max_prefix_bits"]) if x in profile else "原S128" for x in ("gate", "up", "down"))
            lines.append(f"| {case['layer']}/{case['batch']} | {profile['name']} | {z['max_abs_real']:.12g} | {z['relative_L2']:.12g} | {z['exact_fraction']:.12g} | {bits} |")
    lines += ["", "两遍Mid重放的44032个A16值逐位相同。完整gate/up误差、baseline尺度和部分和流量仍在每个numeric.json原始case中。",
              "", "## 六组完整36层部分语料质量", "",
              "| 持续状态/Mid位数 | PPL | 公开参考top1 | 最差序列cosine | 最大前缀位数 | S32裁剪 | teacher-forced decode |",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for z in result["all_narrow_quality"]:
        lines.append(f"| {z['state_bits']}/{z['mid_bits']} | {z['PPL']:.12f} | {100*z['public_top1_fraction']:.9f}% | {z['public_min_sequence_cosine']:.12f} | {z['max_prefix_bits']} | {z['clipped']} | {z['decode']['top1_fraction']*16:.0f}/16 |")
    lines += ["", "## 全部24种时间消融（51.2 GB/s）", "",
              "Mid模式：0=保存原S64；1=RNE保存S32；2/3=两遍重算的两档显式服务假设，首遍额外34/2拍，第二遍均额外34拍。不是RTL测得的周期。",
              "", "| 名称 | 状态位数 | 每组额外RNE拍 | Mid模式 | token/s |", "|---|---:|---:|---:|---:|"]
    for z in result["narrow_timing"]["cases"]:
        lines.append(f"| {z['name']} | {z['state_bits']} | {z['extra_RNE_cycles_per_group']} | {z['mid_mode']} | {z['tokens_s']:.11f} |")
    lines += ["", "## 全部六种G表", "",
              "| 表项 | 逻辑B | 函数最大绝对误差 | PPL | 公开参考top1 | decode | 质量准入 |", "|---:|---:|---:|---:|---:|---:|---|"]
    for z in result["small_G"]:
        lines.append(f"| {z['entries']} | {z['logical_bytes']} | {z['math_max_abs']:.12g} | {z['PPL']:.12f} | {100*z['public_top1']:.9f}% | {z['decode']['top1_fraction']*16:.0f}/16 | {'通过' if z['quality_admitted'] else '拒绝'} |")
    lines += ["", "## 全部41次完整decode trace", "",
              "X_mode：0=独立4 KiB，1=已有S内4 KiB，2=256 B片段。bank4行的0 B FIFO不表示零权重存储，而是四个完整record银行；其入口是各银行独立服务，不能按单个64 B入口计算。",
              "", "| 方案 | 标签 | DDR GB/s | 入口B/拍 | FIFO B/P | X_mode | A服务B/拍 | token/s | FFN ms | FFN链路B |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for z in result["stream_full_trace_cases"]:
        ingress = "独立bank" if "bank4" in z["plan"] else z["ingress_B_cycle"]
        lines.append(f"| {z['plan']} | {z['label']} | {z['bandwidth_GB_s']} | {ingress} | {z['FIFO_B_per_P']} | {z['X_mode']} | {z['A_port_B_cycle']} | {z['tokens_s']:.11f} | {z['FFN_ms']:.8f} | {z['FFN_link_B']} |")
    lines += ["", "全部配置的逻辑读写和M命令数与对应带宽的冻结基线一致。FIFO预约/到达/消费计数和峰值、通道行冲突/等待、S端口服务与原始继承资源字段保存在包内report.json；可机读摘要另列FIFO等待、各P峰值和X预算，不将跨P等待和简单相加成可消除的token延迟。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("work/YUZE-LU/248/followup"))
    parser.add_argument("--write-summary", action="store_true")
    args = parser.parse_args()
    result = audit(args.root)
    if args.write_summary:
        (args.root / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    else:
        assert json.loads((args.root / "summary.json").read_text(encoding="utf-8")) == result
    table_file = Path(__file__).resolve().parents[3] / "docs/experiments/issue-248-followup-all-cases.md"
    if args.write_summary:
        table_file.write_text(case_tables(result), encoding="utf-8", newline="\n")
    else:
        assert table_file.read_text(encoding="utf-8") == case_tables(result)
    print(json.dumps({key: result[key] for key in ("audited_archives", "audited_members", "stream_reports_passed")}))
    print("PASS: original execution SHA, collected SHA, Slurm states, quality gates, 24 timing cases, and 41 equal-work stream traces")


if __name__ == "__main__":
    main()
