"""Replay real control images against the stitched, physically sourced netlist."""
import re
from pathlib import Path
import sys

bundle = Path(sys.argv[1])
stitched = Path(sys.argv[2])
kind = sys.argv[3]
design = bundle/"design"
rtl = design/f"cfj_group_{kind}.sv"
netlist = stitched.read_text()
if f"module cfj_group_{kind} " not in netlist and f"module cfj_group_{kind}(" not in netlist:
    raise ValueError("stitched physical top does not match the regression")
rtl.write_text(netlist)
fixture = design/"tb_cfj_local.sv"
bench = fixture.read_text()
begin = bench.index(f"begin: group_{kind}\n")
end = bench.index("    end\n", bench.index("    );", begin))
prefix = bench[:begin]
block = bench[begin:end]
suffix = bench[end:]
block = block.replace(" #(.BLOCK_ID(BLOCK), .TOPOLOGY_ID(TOPOLOGY_ID))", "")
block = re.sub(r"(?m)^\s+\.(late_\w+|verify_\w+)\([^\n]*\),?\n", "", block)
block = block.replace(",\n    );", "\n    );")
if kind != "j":
    # The fixture observes the qualified leaf model's actual OpenRAM content.
    # No verification interface is inserted in the physical controller.
    check = """        reg observed;
        reg [127:0] stored;
        assign check_valid=observed;
        assign check_data=stored;
        always @(posedge clk_i) begin
            if (!rst_ni) observed<=0;
            else if (check_read) begin
                observed<=1;
                case (check_addr[1:0])
BANK_READS
                endcase
            end else if (check_take) observed<=0;
        end
"""
    banks = "\n".join(f"                    {i}: stored<=dut.\\services.store.leaf .storage.banks[{i}].memory.mem[check_addr[9:2]];"
                      for i in range(4))
    index = block.index(f"    cfj_group_{kind} ")
    block = block[:index] + check.replace("BANK_READS", banks) + block[index:]
fixture.write_text(prefix + block + suffix)
pair = design/"tb_native_pair.sv"
pair.write_text(pair.read_text().replace("32'h01930010 + (SINGLE_KIND<0 ? 0 : SINGLE_KIND+1)",
                                         "32'h01930010"))
images = design/"images.py"
images.write_text(images.read_text().replace("TOPOLOGY if kind < 0 else TOPOLOGY + kind + 1", "TOPOLOGY"))
