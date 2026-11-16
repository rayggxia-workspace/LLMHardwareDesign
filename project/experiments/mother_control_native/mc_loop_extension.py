"""Text derivation of image-v3 bounded loop/64-bit pointer arithmetic."""

def extend(core):
    marker="  wire [32:0] read_sum="
    assert marker in core
    core=core.replace(marker,"""  wire addi64_fields=movi_fields&&ia<7&&!ia[0];
  wire [64:0] pointer_sum={1'b0,registers[{ia[2:1],1'b1}],registers[{ia[2:1],1'b0}]}+
      {33'b0,ireg[63:32]};
  wire loop_fields=movi_fields&&ia>=2;
  wire loop_target_ok=ireg[63:32]>=header[128+:32]&&ireg[63:32]<pc&&ireg[63:32]<inst_count;
  wire loop_count_ok=registers[ia[2:0]]!=0&&registers[ia[2:0]]<=32'd65535;
"""+marker)
    marker="          8'h1f: begin"
    assert marker in core
    core=core.replace(marker,"""          8'h16: begin
            if(!addi64_fields||pointer_sum[64]) fault(18);
            else begin
              registers[{ia[2:1],1'b0}]<=pointer_sum[31:0];
              registers[{ia[2:1],1'b1}]<=pointer_sum[63:32];
              ireg_valid<=0;pc<=pc+1;steps<=steps+1;seq<=FETCH_REQ;
            end
          end
          8'h17: begin
            if(!loop_fields||!loop_target_ok||!loop_count_ok) fault(19);
            else begin
              registers[ia[2:0]]<=registers[ia[2:0]]-1'b1;
              pc<=registers[ia[2:0]]>1?ireg[63:32]:pc+1;
              ireg_valid<=0;steps<=steps+1;seq<=FETCH_REQ;
            end
          end
"""+marker)
    # READY belongs to a CALL's full task sequence, not once for the whole job.
    # Re-arm only the static binding of the target being allocated again.
    marker="              cancel_sent[ia[3:0]]<=0; block_token[ia[3:0]]<=ib[3:0]; context_packet[ia[3:0]]<=call_word;"
    assert marker in core
    core=core.replace(marker,marker+"""
              for(bj=0;bj<9;bj=bj+1)if(bj<binding_count&&event_cache[bj][8+:8]==ia)
                binding_consumed[bj]<=0;""")
    return core
