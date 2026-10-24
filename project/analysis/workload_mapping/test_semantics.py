"""Counterexamples for generic typed contracts, independent of fixture acceptance."""
import copy
import json
import tempfile
from pathlib import Path
import unittest

from project.analysis.workload_mapping import core, v2_bridge
from project.analysis.workload_mapping.semantics import validate_semantics, apply_semantics
from project.analysis.workload_mapping.consumer import verify_mapping
from project.analysis.workload_mapping.cli import main


class SemanticTests(unittest.TestCase):
    def data(self, state=False):
        name = "graph2_state_commit" if state else "graph1_reduce_rq"
        config = v2_bridge._load_upstream().read_json(v2_bridge.UPSTREAM/"fixtures"/(name+".input.json"))
        return v2_bridge.convert(config,"failure_retry" if state else "normal")

    def test_missing_duplicate_groups_units_and_dimension(self):
        for mutation in ("missing","duplicate","unit","shape"):
            g,b,s = self.data()
            r = s["reductions"][0]
            if mutation == "missing":
                r["partials"].pop()
            elif mutation == "duplicate":
                r["partials"][1] = r["partials"][0]
            elif mutation == "unit":
                next(f for f in s["tensor_formats"] if f["tensor"] == r["partials"][0])["unit"] = 2
            else:
                next(t for t in g["tensors"] if t["id"] == r["partials"][0])["shape"] = [1]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_semantics(s,g,b)

    def test_early_rq_and_false_complete_certificate(self):
        for mutation in ("early","certificate"):
            g,b,s = self.data()
            r = s["reductions"][0]
            if mutation == "early":
                r["rq_call"] = next(t["producer"] for t in g["tensors"] if t["id"] == r["partials"][0])
            else:
                next(f for f in s["tensor_formats"] if f["tensor"] == r["complete"])["stage"] = "PARTIAL"
            with self.assertRaises(ValueError):
                validate_semantics(s,g,b)

    def test_owner_epoch_version_and_lost_feedback(self):
        for field,value in (("owner","S"),("epoch",1),("expected_version",2),("previous","absent")):
            g,b,s = self.data(True)
            s["transactions"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_semantics(s,g,b)

    def test_failed_publication_and_private_transfer_are_rejected(self):
        g,b,s = self.data(True)
        tx = s["transactions"][1]
        tx["published"] = s["transactions"][2]["published"]
        with self.assertRaisesRegex(ValueError,"aborted"):
            validate_semantics(s,g,b)
        g,b,s = self.data(True)
        g["transfers"].append({"tensor":s["transactions"][1]["shadow"]})
        with self.assertRaisesRegex(ValueError,"leaked"):
            validate_semantics(s,g,b)

    def test_ram_bank_rom_and_fifo_cannot_be_pooled(self):
        for kind in ("private_ram","shared_bank","fifo"):
            g,b,s = self.data(True)
            next(d for d in s["memory_domains"] if d["kind"] == kind)["capacity_bytes"] = 1
            for r in b["resources"]:
                r["capacity_bytes"] = 1000000
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError,"memory capacity"):
                validate_semantics(s,g,b)
        g,b,s = self.data(True)
        sid = next(t["storage"] for t in g["tensors"] if t["producer"] is not None)
        next(d for d in s["storage_domains"] if d["storage"] == sid)["kind"] = "rom"
        with self.assertRaisesRegex(ValueError,"ROM"):
            validate_semantics(s,g,b)

    def test_bank_access_seriality_and_storage_are_checked(self):
        for mutation in ("duplicate","storage","direction"):
            g,b,s = self.data(True)
            if mutation == "duplicate":
                s["bank_accesses"][1]["slot"] = 0
            elif mutation == "storage":
                s["bank_accesses"][0]["storage"] = "not-a-slot"
            else:
                s["bank_accesses"][0]["op"] = "write"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_semantics(s,g,b)

    def test_independent_reader_rejects_rehashed_semantics_and_derived_report(self):
        g,b,s = self.data(True)
        result = core.build(g,b)
        apply_semantics(result,g,b,s)
        mapping = result["mapping_request"]
        for mutation in ("guard","transition","domain"):
            bad = copy.deepcopy(mapping)
            if mutation == "guard":
                bad["semantics"]["transactions"][0]["guard_pass"] = False
                bad["semantics_sha256"] = core.digest(bad["semantics"])
            elif mutation == "transition":
                bad["semantic_report"]["transitions"][1]["version"] += 1
            else:
                bad["semantic_report"]["domain_peak_bytes"][0]["bytes"] -= 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                verify_mapping(bad)

    def test_unknown_required_unit_has_structured_blocked_exit(self):
        g,b,s = self.data()
        part = s["reductions"][0]["partials"][0]
        next(f for f in s["tensor_formats"] if f["tensor"] == part)["unit"] = None
        root = Path(__file__).resolve().parents[3]/".local/tmp"
        root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            tmp = Path(tmp)
            for name,value in (("g",g),("b",b),("s",s)):
                (tmp/(name+".json")).write_bytes(core.canonical(value))
            code = main(["build","--graph",str(tmp/"g.json"),"--blocks",str(tmp/"b.json"),
                         "--semantics",str(tmp/"s.json"),"--root",str(tmp),"--output-dir",str(tmp/"out")])
            self.assertEqual(code,3)
            report = json.loads((tmp/"out/summary.json").read_text())
            self.assertEqual(report["status"],"blocked")
            self.assertFalse(report["mapping_accepted"])

    def test_source_and_unknown_sidecar_fields_are_rejected(self):
        g,b,s = self.data()
        s["source"]["commit"] = "floating-main"
        with self.assertRaises(ValueError):
            validate_semantics(s,g,b)
        g,b,s = self.data()
        s["ignore_errors"] = True
        with self.assertRaises(ValueError):
            validate_semantics(s,g,b)


if __name__ == "__main__":
    unittest.main()
