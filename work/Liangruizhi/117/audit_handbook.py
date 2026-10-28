"""Read-only offline checks for Issue117 documentation and frozen source bytes.

This never imports model/RTL tooling, runs experiments, or accesses the network.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from fractions import Fraction
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[3]
DOC = ROOT / "docs/research-handbook"
WORK = Path(__file__).resolve().parent

# Paired excerpts: source fragment, document fragment. The source and narrative
# may differ in presentation (e.g. ratios versus percentages), never in scope.
CLAIMS = [
    ("s23", "54次正例", "03-attention-model-experiments.md", "54次正例"),
    ("s23", "2.64645e-5", "03-attention-model-experiments.md", "2.64645e-5"),
    ("s23", "10.5MiB", "03-attention-model-experiments.md", "10.5MiB"),
    ("s33", "6.88%", "03-attention-model-experiments.md", "6.88%"),
    ("s39", "42.5905%", "03-attention-model-experiments.md", "42.5905%"),
    ("s39", "4.0788%", "03-attention-model-experiments.md", "4.0788%"),
    ("s47", "0.0179797327", "03-attention-model-experiments.md", "1.7980%"),
    ("s47", "0.0190307204", "03-attention-model-experiments.md", "1.9031%"),
    ("s53", "687.28", "03-attention-model-experiments.md", "687.28"),
    ("s53", "1696.88", "03-attention-model-experiments.md", "1696.88"),
    ("s53", "各有17项", "03-attention-model-experiments.md", "各17项"),
    ("s32r", "6.671", "03-attention-model-experiments.md", "6.671"),
    ("s32r", "95.5811%", "03-attention-model-experiments.md", "95.5811%"),
    ("s61", "27.45%", "03-attention-model-experiments.md", "27.45%"),
    ("s61", "3.37%", "03-attention-model-experiments.md", "3.37%"),
    ("s61", "12.50%", "03-attention-model-experiments.md", "12.50%"),
    ("s56", "99.84%", "03-attention-model-experiments.md", "99.84%"),
    ("s56", "28950/43520", "03-attention-model-experiments.md", "28,950个"),
    ("s59", "91.83%", "03-attention-model-experiments.md", "91.83%"),
    ("s59", "7.36%", "03-attention-model-experiments.md", "7.36%"),
    ("s59", "5.39%", "03-attention-model-experiments.md", "5.39%"),
    ("s64", "4.8113%", "03-attention-model-experiments.md", "4.8113%"),
    ("s64", "4.9264%", "03-attention-model-experiments.md", "4.9264%"),
    ("s61", "28.40%", "03-attention-model-experiments.md", "28.40%"),
    ("s61", "34.47%", "03-attention-model-experiments.md", "34.47%"),
    ("s61", "1.74%", "03-attention-model-experiments.md", "1.74%"),
    ("s61", "1149763584B", "03-attention-model-experiments.md", "1,149,763,584B"),
    ("s61", "0.000141144", "03-attention-model-experiments.md", "0.000141144"),
    ("s93", "356038", "03-attention-model-experiments.md", "356,038"),
    ("s32r", "0.0670345", "04-state-and-moe-experiments.md", "0.0670345"),
    ("s32r", "0.00015652", "04-state-and-moe-experiments.md", "0.00015652"),
    ("s66", "36 / 1", "04-state-and-moe-experiments.md", "36/1"),
    ("s66", "3.513", "04-state-and-moe-experiments.md", "3.513%"),
    ("s66", "0.05667%", "04-state-and-moe-experiments.md", "0.05667%"),
    ("s68", "1508次", "04-state-and-moe-experiments.md", "1508次"),
    ("s68", "262144B", "04-state-and-moe-experiments.md", "262,144B"),
    ("s104", "73,441,693", "04-state-and-moe-experiments.md", "73,441,693"),
    ("s104", "30,763,438", "04-state-and-moe-experiments.md", "30,763,438"),
    ("s104", "position7950/version14", "04-state-and-moe-experiments.md", "position7950、version14"),
    ("s70", "16.8128%", "04-state-and-moe-experiments.md", "16.8128%"),
    ("s72", "9535", "04-state-and-moe-experiments.md", "9535"),
    ("s72", "3.0289%", "04-state-and-moe-experiments.md", "3.0289%"),
    ("s72", "1.6733%", "04-state-and-moe-experiments.md", "1.6733%"),
    ("s99", "148,909,146", "04-state-and-moe-experiments.md", "148,909,146"),
    ("s70", "2.9802e-8", "04-state-and-moe-experiments.md", "2.9802e-8"),
    ("s72", "720（10.4167%）", "04-state-and-moe-experiments.md", "720"),
    ("s74", "8.6287%", "04-state-and-moe-experiments.md", "8.6287%"),
    ("s74", "1.0196%", "04-state-and-moe-experiments.md", "1.0196%"),
    ("s76", "14,224", "04-state-and-moe-experiments.md", "14,224"),
    ("s76", "0.0008405", "04-state-and-moe-experiments.md", "0.0008405"),
    ("s80", "69,215,400", "07-circuit-evidence.md", "69,215,400"),
    ("s80", "38,740,445", "07-circuit-evidence.md", "38,740,445"),
    ("s80", "44.029%", "07-circuit-evidence.md", "44.029%"),
    ("s82", "258244", "07-circuit-evidence.md", "258,244"),
    ("s82", "61492", "07-circuit-evidence.md", "61,492"),
    ("s82", "2.166%", "07-circuit-evidence.md", "2.166%"),
    ("s84", "9,061,831", "07-circuit-evidence.md", "9,061,831"),
    ("s84", "5,919,175", "07-circuit-evidence.md", "5,919,175"),
    ("s84", "-17.3806%", "07-circuit-evidence.md", "−17.3806%"),
    ("s85", "1.52715%", "07-circuit-evidence.md", "1.52715%"),
    ("s93", "54,810.630", "07-circuit-evidence.md", "54,810.630"),
    ("s97", "6,003,222", "07-circuit-evidence.md", "6,003,222"),
    ("s97", "32,962,560", "07-circuit-evidence.md", "32,962,560"),
    ("s106", "17,103,407", "07-circuit-evidence.md", "17,103,407"),
    ("s109", "27900245", "07-circuit-evidence.md", "27,900,245"),
    ("s109", "32753641", "07-circuit-evidence.md", "32,753,641"),
    ("s109", "163901.220", "07-circuit-evidence.md", "163,901.220"),
    ("s110", "126,029.470", "07-circuit-evidence.md", "126,029.470"),
    ("s110", "125,009.626", "07-circuit-evidence.md", "125,009.626"),
    ("s110", "0.80921%", "07-circuit-evidence.md", "0.80921%"),
    ("s11", "44/96", "08-physical-and-mapping.md", "44/96"),
    ("s13", "71/96", "08-physical-and-mapping.md", "71/96"),
    ("s16", "6785", "08-physical-and-mapping.md", "6785"),
    ("s19", "3032", "08-physical-and-mapping.md", "3032"),
    ("s15", "484240.4", "08-physical-and-mapping.md", "484,240.4"),
    ("s15", "7.142%", "08-physical-and-mapping.md", "7.142%"),
    ("s15", "+0.102306", "08-physical-and-mapping.md", "+0.102306"),
    ("s31", "6,645,428.82", "08-physical-and-mapping.md", "6,645,428.82"),
    ("s98", "76964.174", "08-physical-and-mapping.md", "76,964.174"),
    ("s98", "+3.680569", "08-physical-and-mapping.md", "+3.680569"),
    ("s98", "+0.036780", "08-physical-and-mapping.md", "+0.036780"),
    ("s98", "59619.910", "08-physical-and-mapping.md", "59,619.910"),
    ("s98", "58359", "08-physical-and-mapping.md", "58,359"),
]


def canon(s: str) -> str:
    return re.sub(r"\s+", "", s).replace(",", "").replace("−", "-")


def full_expected(chapters: list[Path]) -> str:
    text = [
        "# 从真实模型到Block电路：完整研究总报告", "",
        "2026-10-26；Liangruizhi；Issue117。本文由11章原文完整拼接，没有删节。",
        "章节分别阅读见[阅读入口](README.md)。章节内交叉链接保留到同目录独立文件，便于定位；本全文已包含其全部正文。",
        "这是一份已有证据的整理与教学分析；原实验、当前候选和制造验收严格分开，本次没有重新跑模型或电路。", "",
    ]
    for i, path in enumerate(chapters, 1):
        title = path.read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
        text.append(f"{i}. [{title}](#full-ch{i:02})")
    text.append("")
    for i, path in enumerate(chapters, 1):
        text.extend(["---", "", f'<a id="full-ch{i:02}"></a>', "", path.read_text(encoding="utf-8").rstrip(), ""])
    return "\n".join(text).rstrip() + "\n"


def main() -> None:
    m = json.loads((DOC / "source-index.json").read_text(encoding="utf-8"))
    assert m["repository"] == "rayggxia-workspace/LLMHardwareDesign"
    sources = {s["id"]: s for s in m["sources"]}
    assert len(sources) == len(m["sources"])
    cap = m["capsule"]
    archive = (DOC / cap["path"]).resolve()
    assert archive.parent == WORK
    raw = archive.read_bytes()
    assert len(raw) == cap["bytes"] and hashlib.sha256(raw).hexdigest() == cap["sha256"]
    texts = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        assert len(names) == len(set(names)) == cap["members"]
        assert set(names) == {s["capsule_member"] for s in sources.values()}
        assert all(".." not in Path(n).parts and not n.startswith(("/", "\\")) for n in names)
        for sid, s in sources.items():
            b = z.read(s["capsule_member"])
            assert len(b) == s["bytes"] and hashlib.sha256(b).hexdigest() == s["sha256"], sid
            if s["git_blob"]:
                assert hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest() == s["git_blob"], sid
                assert re.fullmatch("[0-9a-f]{40}", s["head"])
                assert "/blob/" + s["head"] + "/" in s["url"]
            texts[sid] = b.decode("utf-8")
    files = sorted(DOC.glob("*.md"))
    chapters = sorted(DOC.glob("[0-9][0-9]-*.md"))
    assert len(chapters) == 11
    docs = {p.name: p.read_text(encoding="utf-8") for p in files}
    assert docs["FULL_REPORT.md"] == full_expected(chapters), "Full edition differs from chapters"
    link_count = 0
    table_count = 0
    for path in files:
        s = docs[path.name]
        assert "\r" not in s and "\ufffd" not in s and not s.startswith("\ufeff"), path
        assert s.count("```") % 2 == 0, (path, "unclosed code fence")
        ids = re.findall(r'<a id="([^"]+)"></a>', s)
        assert len(ids) == len(set(ids)), (path, "duplicate explicit anchor")
        visible = re.sub(r"```.*?```", "", s, flags=re.S)
        width = None
        for line in visible.splitlines():
            if line.startswith("|") and line.endswith("|"):
                cells = re.split(r"(?<!\\)\|", line)[1:-1]
                if width is None:
                    width = len(cells)
                    table_count += 1
                assert len(cells) == width, (path.name, "table columns", line)
            else:
                width = None
        for target in re.findall(r"\[[^\]\n]+\]\(([^\s)]+)\)", visible):
            u = urlsplit(target)
            if u.scheme:
                assert u.scheme in {"https", "http"}, (path, target)
                continue
            dest = (path.parent / unquote(u.path)).resolve() if u.path else path
            assert dest.is_file(), (path.name, target)
            assert dest.is_relative_to(ROOT), (path, target)
            if u.fragment:
                content = dest.read_text(encoding="utf-8")
                assert re.search(r'\bid=[\"\']' + re.escape(unquote(u.fragment)) + r'[\"\']', content), (path, target)
            link_count += 1
    for sid, sf, name, df in CLAIMS:
        assert canon(sf) in canon(texts[sid]), (sid, "source fragment", sf)
        assert canon(df) in canon(docs[name]), (name, "claim missing", df)
    # Independently recompute actual published communication CSV aggregates.
    base = [r for r in csv.DictReader(io.StringIO(texts["s63c"])) if r["category"] == "main"]
    strong = list(csv.DictReader(io.StringIO(texts["s63g"])))
    assert len(base) == len(strong) == 12 and {r["case"] for r in base} == {r["case"] for r in strong}
    sums = {k: sum(int(r[k + "_wire_bytes"]) for r in base) for k in ["fixed", "greedy", "beam"]}
    sums["strong"] = sum(int(r["strong_greedy_wire_bytes"]) for r in strong)
    assert sums == {"fixed": 10119300544, "greedy": 9135129664, "beam": 9012513536, "strong": 8673527488}
    assert len([r for r in strong if int(r["strong_greedy_wire_bytes"]) < int(r["beam_wire_bytes"])]) == 10
    # Check derived numbers and pedagogical examples without model execution.
    assert round((126029.470 - 125009.626) / 126029.470 * 100, 5) == 0.80921
    assert round((9061831 - 5919175) / 9061831 * 100, 4) == 34.6801
    assert 10240 + 1024 + 512 + 4096 == 15872
    assert 659600 + 32 * 1568 == 709776
    assert 40 * 64 * 2 == 5120 and 40 * 128 * 2 == 10240
    assert 8192 * 127 ** 2 == 132128768
    assert round(Fraction(1, 2)) + round(Fraction(1, 2)) == 0 and round(Fraction(2, 2)) == 1
    p = 1 / (1 + math.exp(-1))
    assert round(2 * p, 4) == 1.4621 and round(4 * (1 - p), 4) == 1.0758
    assert round((3 / (1 + math.exp(-3)) * 2) / 4 + 2, 6) == 3.428861
    assert round(3 / math.sqrt(12.5), 6) == 0.848528
    assert round(4 / math.sqrt(12.5) * 2, 6) == 2.262742
    assert round(3 * p - 1, 4) == 1.1932
    # Every 64-hex digest printed in manually authored chapters is sourced.
    combined_sources = "\n".join(texts.values())
    digests = set()
    for path in chapters[:9]:
        for digest in re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", docs[path.name]):
            assert digest in combined_sources, (path, "unsourced digest", digest)
            digests.add(digest)
    snapshot = json.loads((WORK / "task-snapshot.json").read_text(encoding="utf-8"))
    ledger = docs["11-work-ledger.md"]
    assert all(f"### Issue{x['number']} ·" in ledger for x in snapshot["issues"])
    assert "封存" in docs["03-attention-model-experiments.md"]
    assert "本次未查询服务器新终态" in docs["08-physical-and-mapping.md"]
    unique_narrative = "\n".join(docs[p.name] for p in chapters[:9])
    result = {
        "status": "PASS_DOCUMENTATION_ONLY",
        "sources": len(sources),
        "git_blobs_rehashed": sum(bool(s["git_blob"]) for s in sources.values()),
        "capsule_members": cap["members"],
        "local_links_and_explicit_fragments": link_count,
        "markdown_tables_including_full_edition": table_count,
        "paired_key_source_excerpt_checks": len(CLAIMS),
        "independently_summed_csv_main_cases": 12,
        "manual_digest_checks": len(digests),
        "issues_covered": len(snapshot["issues"]),
        "chapters": len(chapters),
        "unique_narrative_cjk_characters": len(re.findall(r"[\u4e00-\u9fff]", unique_narrative)),
        "unique_narrative_utf8_bytes": len(unique_narrative.encode("utf-8")),
        "full_edition_utf8_bytes": (DOC / "FULL_REPORT.md").stat().st_size,
        "numeric_csv_aggregate": sums,
        "not_executed": ["model inference", "quantization producers or original receivers", "RTL/gate simulation", "SAT/synthesis/STA/physical implementation", "server state query"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
