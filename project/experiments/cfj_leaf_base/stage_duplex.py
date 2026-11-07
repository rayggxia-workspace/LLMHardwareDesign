"""Use real mother/local images to reserve, send and receive in both groups."""
from pathlib import Path
import sys

design = Path(sys.argv[1]) / "design"
image_path = design / "images.py"
images = image_path.read_text()
begin = images.index("    ops = [")
end = images.index("    mother_program =", begin)
images = images[:begin] + """    ops = [
        [dict(native_op=RESERVE, native0=41),
         dict(native_op=SEND, native0=40 | 41 << 10),
         dict(native_op=RECEIVE)],
        [dict(native_op=RESERVE, native0=41),
         dict(native_op=SEND, native0=40 | 41 << 10),
         dict(native_op=RECEIVE)],
    ]
""" + images[end:]
images = images.replace("(2 if kind < 0 else kind) if block == 0 else 0", "(2, 1)[block]")
image_path.write_text(images)

pair_path = design / "tb_native_pair.sv"
pair = pair_path.read_text()
old = "i==0 ? (SINGLE_KIND<0 ? 2 : SINGLE_KIND) : 0"
if pair.count(old) != 1:
    raise ValueError("native pair type expression changed")
pair = pair.replace(old, "i==0 ? 2 : 1")
# Both senders must offer before either receiver accepts a word. This makes
# simultaneous TX ownership deterministic despite program-loading skew.
pair = pair.replace("    wire accept_request = stall==0 || cycle%7==1;", """    reg [1:0] offered=0;
    always @(posedge clk_i) begin
        if (!rst_ni) offered<=0;
        else offered<=offered | link_valid;
    end
    wire accept_request = (&offered) && (stall==0 || cycle%7==1);
""")
pair = pair.replace("transfers<=transfers+1;", "transfers<=transfers+int'(link_ack[0] && link_ack_ready[1])+int'(link_ack[1] && link_ack_ready[0]);")
begin = pair.index("    task automatic verify(")
end = pair.index("    endtask", begin)
verify = pair[begin:end]
verify = verify.replace("input [127:0] expected);", "input [127:0] expected, input integer side_id=0);")
verify = verify.replace("[0]", "[side_id]")
pair = pair[:begin] + verify + pair[end:]
begin = pair.index("            default: begin", pair.index("task automatic configure_and_start"))
end = pair.index("            end", begin) + len("            end")
pair = pair[:begin] + """            default: begin
                seed(0,40,INPUT_WORD); seed(0,41,SENTINEL);
                seed(1,40,128'h123456789abcdef0_123456789abcdef0);
                seed(1,41,SENTINEL);
            end""" + pair[end:]
pair = pair.replace("(fault!=0 ? 48 : 80)", "32")
begin = pair.index("            default: begin", pair.index("case (SINGLE_KIND)", pair.index("while(!result_valid_o)")))
end = pair.index("            end", begin) + len("            end")
pair = pair[:begin] + """            default: begin
                verify(40,INPUT_WORD);
                verify(41,128'h123456789abcdef0_123456789abcdef0);
                verify(40,128'h123456789abcdef0_123456789abcdef0,1);
                verify(41,INPUT_WORD,1);
            end""" + pair[end:]
pair_path.write_text(pair)
runner = design / "run.sh"
text = runner.read_text()
old = 'if [[ $kind == -1 ]]; then cases+=("stalled 1 0 0" "fault 0 1 0" "stalled-fault 1 1 0" "reset 1 0 1"); fi'
if text.count(old) != 1:
    raise ValueError("native case enumeration changed")
runner.write_text(text.replace(old, 'if [[ $kind == -1 ]]; then cases+=("stalled 1 0 0" "reset 1 0 1"); fi'))
