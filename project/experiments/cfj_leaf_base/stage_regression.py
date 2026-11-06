#!/usr/bin/env python3
"""Adapt the immutable #195 regression bundle to exercise the new C/F/J RTL."""
import hashlib
import shutil
import sys
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[3]
source = Path(sys.argv[1])
bundle = Path(sys.argv[2])
if hashlib.sha256(source.read_bytes()).hexdigest() != "3387aa6f05f5fdd658e0ce326fce70fd694200c1882a4a5941c4fa6ddafea281":
    raise ValueError("unexpected #195 bundle digest")
bundle.mkdir(parents=True, exist_ok=False)
with tarfile.open(source) as archive:
    archive.extractall(bundle, filter="data")

design = bundle / "design"
native = bundle / "staged/native"
pj = bundle / "staged/pj/project/rtl"
for name in ("block_feed_s16k_sram.sv", "local_s_base.sv"):
    shutil.copyfile(root / "project/rtl/s_sram" / name, native / name)
shutil.copyfile(root / "project/rtl/block_v2/block_v2_e_compact.sv", native / "block_v2_e_compact.sv")
for rtl in (root / "project/rtl/block_cfj_v1").glob("*.sv"):
    if rtl.name in ("pj_mem_port.sv", "pj_sram_client.sv"):
        target = pj / "block_pj_v1" / rtl.name
    elif rtl.name.startswith("ucf_"):
        target = native / rtl.name
    else:
        target = design / rtl.name
    shutil.copyfile(rtl, target)
bench = design / "tb_native_local.sv"
text = bench.read_text()
start = text.index("        block_ucf16 #(.KIND(KIND))")
end = text.index("\n\n", start)
bind = text[start:end]
text = text[:start] + (
    "        if (KIND==0) begin: old_u_reference\n" + bind +
    "\n        end else begin: compact_cf\n" + bind.replace("block_ucf16", "block_cfj_cf") +
    "\n        end"
) + text[end:]
bench.write_text(text)
bench = design / "tb_pj_endpoint.sv"
text = bench.read_text()
assert text.count("block_j16 block") == 1
text = text.replace("block_j16 block", """wire late_e_valid, late_s_take;
        wire [127:0] late_e_data;
        block_cfj_j #(.LATE_E_WRITEBACK(1)) block""")
start = text.index("block_cfj_j #")
end = text.index(");", start)
text = text[:end] + """,
            .late_e_valid,.late_e_data,.late_e_take(late_s_take),
            .late_s_valid(late_e_valid),.late_s_data(late_e_data),.late_s_take""" + text[end:]
bench.write_text(text)

# Add a real-SRAM comparison of local replay and a separately wired G/E edge.
bench = native / "tb_block_ucf16.sv"
text = bench.read_text()
text = text[:text.index("module tb_block_ucf16;")]
text = text.replace("block_ucf16 #(.KIND(KIND)) dut (.*);", """wire late_g_valid, late_e_take;
    wire [31:0] late_g_data;
    block_cfj_cf #(.KIND(KIND), .LATE_G_E(1)) dut (.*,
        .late_g_take(late_e_take), .late_e_valid(late_g_valid), .late_e_data(late_g_data));""")
text = text.replace("            if (KIND == 2) begin", """            execute(1,64'h8000000000000000,1,30'd17,0,0,answer);
            repeat (5) begin
                tick();
                if (!late_g_valid || late_g_data !== 32'h02ed02ed)
                    $fatal(1, "G late endpoint did not retain an unaccepted word");
            end
            execute(0,64'h800000000000001a,0,0,1,20,answer);
            expect_word(20,128'h01760176);
            if (late_g_valid) $fatal(1, "late input was not consumed");
            if (KIND == 2) begin""")
text += """
module tb_cfj_direct;
    reg clk=0;
    always #5 clk=!clk;
    wire c, f;
    ucf_case #(.KIND(2)) c_case(clk,c);
    ucf_case #(.KIND(1)) f_case(clk,f);
    initial begin
        wait (c && f);
        $display("PASS C/F G-to-E late endpoint and SRAM replay");
        $finish;
    end
    initial begin
        #50000;
        $fatal(1, "timeout");
    end
endmodule
"""
(design / "tb_cfj_direct.sv").write_text(text)
bench.unlink()
