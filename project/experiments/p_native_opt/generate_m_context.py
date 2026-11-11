"""Issue247 isolated native M context experiment; never edits production sources."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_REPO = HERE.parent.parent / '242/r-load-bounds/repo'
RTL = 'project/rtl/block_v2/block_v2_m.sv'
TEST = 'project/experiments/block_v2/test_m.cpp'
FROZEN = {
    RTL: '5825adcd3364d4315afd1aa4addae85379fb36df2802ca8ab60026e0b0f44d1e',
    TEST: '0db48afc86db47246b5f8e50e3d102971df8e0307302d0ee43a3283e487c10f9',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_sources(repo, expected=None):
    expected = FROZEN if expected is None else expected
    actual = {name:sha(Path(repo)/name) for name in expected}
    if actual != expected:
        raise ValueError('frozen native source mismatch: ' + repr(actual))
    return actual


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError('native source anchor drift: ' + repr(old[:100]))
    return text.replace(old, new, 1)


def candidate(text):
    text = replace(text, 'module block_v2_m(',
                   'module block_v2_m_context #(parameter integer CONTEXTS=8)(')
    text = replace(text, ' reg execution_bank,fmt_a,fmt_b,clear_result;', ''' // New mode reuses the existing eight result rows as eight N8 contexts.
 // No new operand, partial, preview, or S64 result payload arrays are added.
 localparam [1:0] CTX_FREE=0,CTX_ACTIVE=1,CTX_COMPLETE=2;
 reg [1:0] context_state[0:7],context_format[0:7];
 reg [15:0] context_next_k[0:7],context_tag[0:7];
 wire [7:0] context_live;
 for(genvar c=0;c<8;c=c+1)begin: context_liveness
  assign context_live[c]=context_state[c]!=CTX_FREE;
 end
 reg context_execution,context_final;
 reg [2:0] context_source_row;
 reg [15:0] context_end_k,context_group_tag;
 wire [2:0] operand_row=context_execution?context_source_row:issue_row;
 initial begin
  if(CONTEXTS!=1&&CONTEXTS!=2&&CONTEXTS!=8)$fatal(1,"CONTEXTS must be 1, 2, or 8");
 end
 reg execution_bank,fmt_a,fmt_b,clear_result;''')
    text = replace(text, 'wire start=cmd_valid&&cmd_ready&&cmd_op==10;',
                   'wire start=cmd_valid&&cmd_ready&&(cmd_op==10||cmd_op==13);')
    anchor = ' reg signed [7:0] lhs[0:63],rhs[0:63];'
    addition = ''' // op13: index={operand_bank,2'b0,destination_context}.
 // data: Awide[0],Bwide[1],first[2],final[3],lastK[7:4],N[11:8],
 // tiles[14:12],sourceArow[17:15],Koffset[33:18],group_tag[49:34].
 // A/B payload and bank locks are exactly those of the original native M.
 reg context_descriptor_ok;
 reg [16:0] context_end;
 always @* begin
  context_end={1'b0,cmd_data[33:18]}+
   (({14'd0,cmd_data[14:12]}-17'd1)<<3)+{13'd0,cmd_data[7:4]};
  context_descriptor_ok=cmd_index[4:3]==0&&32'(cmd_index[2:0])<CONTEXTS&&
   cmd_data[63:50]==0&&cmd_data[7:4]>=1&&cmd_data[7:4]<=8&&
   cmd_data[11:8]>=1&&cmd_data[11:8]<=8&&cmd_data[14:12]>=1&&cmd_data[14:12]<=4&&
   !context_end[16];
  for(integer t=0;t<4;t=t+1)if(t<cmd_data[14:12])begin
   if(bv[{cmd_index[5],t[1:0]}]!=3||bf[{cmd_index[5],t[1:0]}]!=cmd_data[1])context_descriptor_ok=0;
   if(!av[{cmd_index[5],cmd_data[17:15],t[1:0]}]||
      af[{cmd_index[5],cmd_data[17:15],t[1:0]}]!=cmd_data[0])context_descriptor_ok=0;
  end
  if(cmd_data[2])begin
   if(context_state[cmd_index[2:0]]!=CTX_FREE||cmd_data[33:18]!=0)context_descriptor_ok=0;
  end else begin
   if(context_state[cmd_index[2:0]]!=CTX_ACTIVE||
      context_next_k[cmd_index[2:0]]!=cmd_data[33:18]||context_tag[cmd_index[2:0]]!=cmd_data[49:34]||
      context_format[cmd_index[2:0]]!=cmd_data[1:0]||
      !merged_valid[cmd_index[2:0]]||result_n[cmd_index[2:0]]!=cmd_data[11:8])context_descriptor_ok=0;
  end
 end

'''
    text = replace(text, anchor, addition + anchor)
    text = replace(text, "32'(issue_row)*32+32'(issue_tile)*8+k]",
                   "32'(operand_row)*32+32'(issue_tile)*8+k]")
    text = replace(text, '   for(i=0;i<8;i=i+1)begin bv[i]<=0;result_n[i]<=0;end', '''   context_execution<=0;context_final<=0;context_source_row<=0;context_end_k<=0;context_group_tag<=0;
   for(i=0;i<8;i=i+1)begin
    bv[i]<=0;result_n[i]<=0;context_state[i]<=CTX_FREE;context_format[i]<=0;context_next_k[i]<=0;context_tag[i]<=0;
   end''')
    text = replace(text, 'merged_valid[srow]<=1;result_n[srow]<=active_n;', '''merged_valid[srow]<=1;result_n[srow]<=active_n;
      // Advance metadata only on the original atomic S64 row commit.
      // Overflow leaves the entire previous payload and lifecycle unchanged.
      if(context_execution)begin
       context_state[srow]<=context_final?CTX_COMPLETE:CTX_ACTIVE;
       context_next_k[srow]<=context_end_k;context_tag[srow]<=context_group_tag;
       context_format[srow]<={fmt_b,fmt_a};
      end''')
    text = replace(text, '3:if(merged_valid[cmd_index[5:3]]&&',
                   '3:if(context_state[cmd_index[5:3]]!=CTX_ACTIVE&&merged_valid[cmd_index[5:3]]&&')
    text = replace(text, '5:if(merged_valid[cmd_index[5:3]]&&',
                   '5:if(context_state[cmd_index[5:3]]!=CTX_ACTIVE&&merged_valid[cmd_index[5:3]]&&')
    text = replace(text, 'av<=0;for(i=0;i<8;i=i+1)bv[i]<=0;merged_valid<=0;partial_valid<=0;',
                   'av<=0;for(i=0;i<8;i=i+1)begin bv[i]<=0;context_state[i]<=CTX_FREE;end merged_valid<=0;partial_valid<=0;')
    text = replace(text, '10:if(!descriptor_ok)respond(0,1,0);else begin',
                   '10:if((|context_live)||!descriptor_ok)respond(0,1,0);else begin\n      context_execution<=0;')
    anchor = '     11:if(cmd_index[5:1]!=0||cmd_data!=0)respond(0,1,0);else begin'
    addition = '''     13:if(!context_descriptor_ok)respond(0,1,0);else begin
      context_execution<=1;context_source_row<=cmd_data[17:15];context_final<=cmd_data[3];
      context_end_k<=context_end[15:0];context_group_tag<=cmd_data[49:34];
      execution_bank<=cmd_index[5];fmt_a<=cmd_data[0];fmt_b<=cmd_data[1];clear_result<=cmd_data[2];
      last_k<=cmd_data[7:4];active_n<=cmd_data[11:8];tiles<={1'b0,cmd_data[14:12]};rows<=1;
      issue_row<=0;issue_bank<=0;issue_tile<=0;issue_a<=0;issue_b<=0;
      bank_busy<=1;bank_done<=0;bank_fault<=0;partial_valid<=0;bank_owner[0]<=cmd_index[2:0];
      for(i=0;i<8;i=i+1)partial[i]<=0;
      scale_bank<=0;scale_pair<=0;committed<=0;fault_rows<=0;row_error<=0;state<=ISSUE;
     end
     // op14 explicitly releases a completed context or aborts a live one.
     // A matching tag is mandatory even on abort; no outstanding execute can exist in IDLE.
     14:if(cmd_index[5:3]!=0||32'(cmd_index[2:0])>=CONTEXTS||cmd_data[63:17]!=0||
       context_state[cmd_index[2:0]]==CTX_FREE||context_tag[cmd_index[2:0]]!=cmd_data[16:1]||
       (!cmd_data[0]&&context_state[cmd_index[2:0]]!=CTX_COMPLETE))respond(0,1,0);
      else begin context_state[cmd_index[2:0]]<=CTX_FREE;merged_valid[cmd_index[2:0]]<=0;respond(0,0,0);end
'''
    text = replace(text, anchor, addition + anchor)
    return '// Isolated Issue247 candidate; original op10 eight-row mode is preserved.\n' + text


def generate(repo, out):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    verified = verify_sources(repo)
    out.mkdir(parents=True, exist_ok=False)
    original = (repo / RTL).read_text(encoding='utf-8')
    test = (repo / TEST).read_text(encoding='utf-8')
    (out / 'block_v2_m.sv').write_bytes((repo / RTL).read_bytes())
    (out / 'block_v2_m_context.sv').write_text(candidate(original), encoding='utf-8', newline='\n')
    (out / 'test_m.cpp').write_bytes((repo / TEST).read_bytes())
    transformed = test.replace('Vblock_v2_m', 'Vblock_v2_m_context')
    (out / 'test_legacy_candidate.cpp').write_text(transformed, encoding='utf-8', newline='\n')
    head = transformed[:transformed.index('static void numeric(){')]
    # Keep only helpers used by the new independent context test. The complete
    # unmodified original program above remains the separate compatibility test.
    begin = head.index('static void reference(')
    end = head.index('static I128 rne(', begin)
    head = head[:begin] + head[end:]
    head = head.replace('static uint64_t measured_cycles[4]{};\n', '')
    head = head.replace('if(!shift)return x;I128 q=', 'if(!shift){return x;}\n I128 q=')
    (out / 'test_context.cpp').write_text(head + (HERE / 'context_tests.cpp.inc').read_text(encoding='utf-8'),
                                           encoding='utf-8', newline='\n')
    result = dict(issue=247, source_sha256=verified,
                  generator_sha256=sha(__file__), tests_sha256=sha(HERE/'context_tests.cpp.inc'),
                  added_payload_bits=0, context_metadata_bits=288, execute_metadata_bits=37,
                  context_limit_options=[1,2,8], physical_qualified=False)
    result['generated_sha256']={p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out/'generation.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=DEFAULT_REPO)
    p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    print(json.dumps(generate(args.repo,args.out)))
