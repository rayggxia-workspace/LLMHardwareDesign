"""New explicit drained-rearm profile; leave prior A/abort sources unchanged."""
from pathlib import Path
root = Path(__file__).parent / 'rtl'
s = (root / 'private_a_scaled_abort_frontend.sv').read_text()
header = s[:s.index('\n);') + 3].replace('module private_a_scaled_abort_frontend(', 'module private_a_scaled_fenced_frontend(')
header = header.replace('  input logic clk, reset, halt, flush,', '''  input logic clk, reset, halt, flush,
  input logic rearm_valid, output logic rearm_ready,
  input logic [31:0] rearm_epoch,''')
body = '''
  // Only the coordinator that accepted the real M FENCE response may offer
  // this rearm. No active/planned A lease, S request or response may survive.
  // This is a metadata namespace restart, never a fabricated operand ACK.
  logic [31:0] last_rearm_epoch;
  wire rearm_fire=rearm_valid&&rearm_ready;
  assign rearm_ready=!reset&&halt&&quiescent&&source_reads_drained&&live_slots==0&&rearm_epoch>last_rearm_epoch;
  private_a_scaled_abort_frontend data_front(.reset(reset||rearm_fire),.*);
  always_ff @(posedge clk)begin
    if(reset)last_rearm_epoch<=0;
    else if(rearm_fire)last_rearm_epoch<=rearm_epoch;
  end
endmodule
'''
(root / 'private_a_scaled_fenced_frontend.sv').write_text(header + body)
