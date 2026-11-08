"""Generate only wiring and observation packing; never generate DUT decisions."""
import json
import pathlib
HERE = pathlib.Path(__file__).resolve().parent
CONTRACT = HERE.parent / "control_rtl_contract_v0_1" / "contract.json"


def pins():
    return [p for g in json.loads(CONTRACT.read_text(encoding="utf-8"))["groups"] for p in g["pins"]]


def outputs():
    ps = pins()
    def width(p):
        return "[{}:0] ".format(p["width"]-1) if p["width"]>1 else ""
    ports = ",\n".join("  {} wire {}{}".format(p["direction"],width(p),p["name"]) for p in ps)+"\n"
    wires = "\n".join("  {} {}{};".format("reg" if p["direction"]=="input" else "wire",width(p),p["name"]) for p in ps)+"\n"
    instance = "lc_min_controller dut (\n"+",\n".join("    .{}({})".format(p["name"],p["name"]) for p in ps)+"\n);\n"
    init = "\n".join("    {}=0;".format(p["name"]) for p in ps if p["direction"]=="input" and p["name"]!="clk_i")+"\n"
    logger = '  always @(posedge clk_i) begin\n    $display("T %0d %h", cycle, {'+", ".join(p["name"] for p in ps)+'});\n    cycle=cycle+1;\n  end\n'
    return {"ports.svh":ports,"tb_wires.svh":wires+instance,"tb_init.svh":init,"tb_trace.svh":logger}


if __name__ == "__main__":
    for name,data in outputs().items():
        (HERE/name).write_text(data,encoding="utf-8")
