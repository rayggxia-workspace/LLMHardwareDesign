"""New abort profile; leave every previously admitted A source unchanged."""
from pathlib import Path
import hashlib
import subprocess

HERE=Path(__file__).resolve().parent
source=(HERE/'rtl/private_a_tile_frontend.sv').read_text()
s=source.replace('module private_a_tile_frontend(', 'module private_a_tile_abort_frontend(',1)
s=s.replace('  input logic clk, reset, halt, flush,', '''  input logic clk, reset, halt, flush,
  // This offer may ONLY originate from a matching, actually accepted native
  // ABORT frame. It cuts the explicitly cancelled A stream, not a normal
  // ready/valid transfer. Retire only after real source/transport drain.
  input logic abort_valid, output logic abort_ready,
  input logic abort_transport_drained,
  input logic [127:0] abort_key,
  input logic abort_slot,
  input logic [15:0] abort_generation,abort_kk,abort_use_sequence,''',1)
anchor='  wire response_match = inflight && response_tag == request_tag;'
s=s.replace(anchor,'''  wire abort_match = state[abort_slot]==READY && abort_key==key[abort_slot] &&
      abort_generation==generation[abort_slot] && abort_kk==kk[abort_slot] &&
      ((issued[abort_slot]!=0 && abort_use_sequence==issued[abort_slot]) ||
       (W_pending[abort_slot] && abort_use_sequence==W_sequence[abort_slot] &&
        abort_use_sequence==issued[abort_slot]+16'd1));
  wire verified_abort_offer=abort_valid && halt && abort_match;
  assign abort_ready=!reset && halt && abort_match && abort_transport_drained &&
      !request_pending && !inflight && source_reads_drained;
'''+anchor,1)
s=s.replace('      (flush && !(halt && quiescent));','      (flush && !(halt && quiescent)) || (abort_valid && (!halt || !abort_match));',1)
s=s.replace('  assign a_valid = !reset && active;', '  assign a_valid = !reset && active && !(verified_abort_offer && active_slot==abort_slot);',1)
s=s.replace('      if(flush && halt && quiescent) begin', '''      if(abort_valid && abort_ready) begin
        // Never invent any missing operand acceptance or completed use.
        if(active && active_slot==abort_slot)active<=0;
        state[abort_slot]<=INVALID;W_pending[abort_slot]<=0;closed[abort_slot]<=1;
      end
      if(flush && halt && quiescent) begin''',1)
s='// Derived original A SHA256 '+hashlib.sha256(source.encode()).hexdigest()+'\n'+s
(HERE/'rtl/private_a_tile_abort_frontend.sv').write_text(s)
# Same12 scale bits; no new A payload and no change to the root's old wrapper.
root=HERE.parents[2]
scaled=subprocess.check_output(['git','show','f17dae750:project/rtl/block_local_native/private_a_scaled_frontend.sv'],cwd=root).decode()
scaled=scaled.replace('module private_a_scaled_frontend(', 'module private_a_scaled_abort_frontend(',1)
scaled=scaled.replace('  input logic clk, reset, halt, flush,','''  input logic clk, reset, halt, flush,
  input logic abort_valid, output logic abort_ready,
  input logic abort_transport_drained,
  input logic [127:0] abort_key,
  input logic abort_slot,
  input logic [15:0] abort_generation,abort_kk,abort_use_sequence,''',1)
scaled=scaled.replace('private_a_tile_frontend data_front','private_a_tile_abort_frontend data_front',1)
(HERE/'rtl/private_a_scaled_abort_frontend.sv').write_text(scaled)
