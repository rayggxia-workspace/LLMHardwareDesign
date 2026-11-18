"""Create an EXEC-only ready guard from the frozen C639 M leaf template."""

from pathlib import Path
import re
import sys


template = Path(sys.argv[1])
source = template.read_text()
match = re.search(r"   EXEC:if\((.*?)\)begin command_bad=1;command_error=5;end\n", source, re.S)
if match is None or not match.group(1).startswith("!exec_owner"):
    raise ValueError("frozen EXEC validation expression missing")

old_guard = " wire A_wait_bind=command_pending&&op==EXEC&&a_session==session&&!command_bad;"
if source.count(old_guard) != 1:
    raise ValueError("frozen A-ready guard missing")

new_guard = " wire A_wait_bind=command_pending&&a_session==session&&exec_bind_ok;"
exec_check = f""" wire exec_fields_bad={match.group(1)};
 reg exec_bind_ok;
 always @* begin
  exec_bind_ok=0;
  case(op)
   EXEC:begin
    exec_bind_ok=!common_bad;
    if(!same_scope)exec_bind_ok=0;
    if(exec_fields_bad)exec_bind_ok=0;
   end
   default:exec_bind_ok=0;
  endcase
 end
"""
candidate = (
    source[:match.start()] + "   EXEC:if(exec_fields_bad)begin command_bad=1;command_error=5;end\n"
    + source[match.end():]
)
candidate = candidate.replace(old_guard, new_guard)
declaration = " reg command_bad;reg [7:0] command_error;"
if candidate.count(declaration) != 1:
    raise ValueError("frozen command validator declaration missing")
template.write_text(candidate.replace(declaration, exec_check + declaration))

# The other opcode validators can produce either result. All other inputs to
# the original and candidate ready controls are independent symbolic bits.
proof = Path(sys.argv[2])
opcodes = re.search(r"localparam \[3:0\] (BEGIN_SCOPE=[^;]*FENCE=\d+);", source)
if opcodes is None:
    raise ValueError("frozen M opcodes missing")
proof.write_text("""module exec_ready_guard(
 input [3:0] op, input common_bad, same_scope, exec_fields_bad, other_fields_bad,
 input command_pending, session_match, a_valid, a_live_match, local_space, native_ready,
 output equal
);
 localparam [3:0] @OPCODES@;
 reg command_bad, exec_bind_ok;
 always @* begin
  command_bad=common_bad;
  if(op!=BEGIN_SCOPE&&op!=FENCE&&!same_scope)command_bad=1;
  case(op)
   EXEC:if(exec_fields_bad)command_bad=1;
   default:if(other_fields_bad)command_bad=1;
  endcase
 end
 always @* begin
  exec_bind_ok=0;
  case(op)
   EXEC:begin
    exec_bind_ok=!common_bad;
    if(!same_scope)exec_bind_ok=0;
    if(exec_fields_bad)exec_bind_ok=0;
   end
   default:exec_bind_ok=0;
  endcase
 end
 wire old_wait=command_pending&&op==EXEC&&session_match&&!command_bad;
 wire new_wait=command_pending&&session_match&&exec_bind_ok;
 wire old_bad_a=a_valid&&!old_wait&&!a_live_match;
 wire new_bad_a=a_valid&&!new_wait&&!a_live_match;
 wire old_ready=old_wait?1'b0:(old_bad_a?local_space:native_ready);
 wire new_ready=new_wait?1'b0:(new_bad_a?local_space:native_ready);
 assign equal=(old_wait==new_wait)&&(old_bad_a==new_bad_a)&&(old_ready==new_ready);
endmodule
""".replace("@OPCODES@", opcodes.group(1)))
