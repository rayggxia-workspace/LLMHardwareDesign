"""Generate declarations only, never a functional local-controller DUT."""
import argparse
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def contract():
    return json.loads((HERE/"contract.json").read_bytes().decode("utf-8"))


def artifacts():
    c = contract()
    pins = [p for g in c["groups"] for p in g["pins"]]
    assert len({p["name"] for p in pins}) == len(pins)
    assert all(type(p["width"]) is int and p["width"] > 0 for p in pins)
    lines = ["// Generated from contract.json. Declarations only; no controller logic.",
             "interface lc_boundary_v0_1;"]
    for pin in pins:
        width = "" if pin["width"] == 1 else "[%d:0] "%(pin["width"]-1)
        lines.append("  logic "+width+pin["name"]+";")
    for name,invert in [("controller",False),("peer",True)]:
        rows = []
        for pin in pins:
            direction = pin["direction"]
            if invert:
                direction = "output" if direction == "input" else "input"
            rows.append("    "+direction+" "+pin["name"])
        lines += ["  modport "+name+" (",",\n".join(rows),"  );"]
    lines += ["endinterface",""]
    params = ["// Generated research constants; no instruction encoding changes.",
              "package lc_contract_v0_1_pkg;"]
    for family in ("lifecycle","sequencer","cfg_opcodes","service_kinds"):
        for name,value in c[family].items():
            params.append("  localparam int unsigned %s_%s = %d;"%(family.upper(),name,value))
    params += ["endpackage",""]
    md = ["# 局控逻辑端口 v0.1","","由contract.json生成；不是原生宏pin或已通过编译的RTL。","",
          "| group | pin | direction | bits | meaning |","|---|---|---|---:|---|"]
    for g in c["groups"]:
        for pin in g["pins"]:
            md.append("| %s | %s | %s | %d | %s |"%(g["name"],pin["name"],pin["direction"],pin["width"],pin["meaning"]))
    md += ["","payload寄存器预算下界：%dB，不含控制元数据、valid位、适配器和物理实现。"%sum(c["payload_register_budget_bytes"].values()),""]
    return {"lc_boundary_v0_1.sv":"\n".join(lines),"lc_contract_v0_1_pkg.sv":"\n".join(params),"PORTS.md":"\n".join(md)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args = parser.parse_args()
    for name,text in artifacts().items():
        file = HERE/name
        if args.check:
            assert file.read_bytes() == text.encode("utf-8"),name+" differs"
        else:
            file.write_bytes(text.encode("utf-8"))
    c = contract()
    print("PASS declarations",sum(len(g["pins"]) for g in c["groups"]),"pins;",
          sum(c["payload_register_budget_bytes"].values()),"payload register bytes; compiler not executed")


if __name__ == "__main__":
    main()
