"""Strict bench derivatives; frozen historical sources are never edited."""
import hashlib
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('bench anchor not unique: ' + repr(old))
    return text.replace(old, new)


COMPAT_OBSERVER = r'''
 // Read-only observers: compare actual cycle and every public ready/valid
 // transition, with operand/command/IO payload whenever valid is asserted.
 always @(posedge clk)if(!reset)begin
  $display("COMPAT_EVENT cycle=%0d kind=C flags=%h",cycle,
   {cold_reset,cfg_valid,cfg_ready,cfg_done,cfg_take,cfg_error,fill_valid,fill_ready,fill_done,fill_take,fill_error,
    object_valid,load_valid,load_ready,load_done,load_take,load_error,cmd_valid,cmd_ready,cmd_done,cmd_take,cmd_error,cmd_saturated,
    wide_write_req,wide_write_ready,wide_write_valid,wide_write_take,io_req_valid,io_req_ready,io_rsp_valid,io_rsp_ready,
    gate_valid,gate_ready,gate_done,gate_take,gate_error,m_to_g_valid,m_to_g_take,g_from_m_valid,g_from_m_take});
  for(integer q=0;q<4;q++)if(io_req_valid[q]||io_rsp_valid[q])
   $display("COMPAT_EVENT cycle=%0d kind=IO p=%0d req=%h rsp=%h",cycle,q,
    {io_req_valid[q],io_req_ready[q],io_req_write[q],io_req_addr[q*10+:10],io_req_valid[q]?io_req_data[q*128+:128]:128'd0},
    {io_rsp_valid[q],io_rsp_ready[q],io_rsp_valid[q]?io_rsp_data[q*128+:128]:128'd0});
  for(integer q=0;q<2;q++)if(cmd_valid[q]||cmd_done[q])
   $display("COMPAT_EVENT cycle=%0d kind=CMD p=%0d req=%h rsp=%h",cycle,q,
    {cmd_valid[q],cmd_ready[q],cmd_op[q*4+:4],cmd_index[q*6+:6],cmd_data[q*64+:64]},
    {cmd_done[q],cmd_take[q],cmd_error[q],cmd_saturated[q],cmd_done[q]?cmd_result[q*128+:128]:128'd0});
 end
 for(genvar q=0;q<2;q++)begin: compat_observers
  always @(posedge clk)if(!reset)begin
   if(dut.groups[q].block_p.a_valid)
    $display("COMPAT_EVENT cycle=%0d kind=A p=%0d beat=%h",cycle,q,
     {dut.groups[q].block_p.a_valid,dut.groups[q].block_p.a_ready,dut.groups[q].block_p.a_bank,
      dut.groups[q].block_p.a_row,dut.groups[q].block_p.a_tile,dut.groups[q].block_p.a_wide,dut.groups[q].block_p.a_data});
   if(dut.groups[q].block_p.b_valid)
    $display("COMPAT_EVENT cycle=%0d kind=B p=%0d beat=%h",cycle,q,
     {dut.groups[q].block_p.b_valid,dut.groups[q].block_p.b_ready,dut.groups[q].block_p.b_bank,
      dut.groups[q].block_p.b_tile,dut.groups[q].block_p.b_wide,dut.groups[q].block_p.b_half,dut.groups[q].block_p.b_data});
  end
 end
'''


def generate(repo, out):
    repo, out = Path(repo), Path(out)
    out.mkdir(parents=True, exist_ok=False)
    old = repo / 'project/experiments/shared32_native'
    p = (old / 'tb_shared_pool.sv').read_text(encoding='utf8')
    p = once(p, 'module tb_shared_pool;', 'module tb_a32_pool #(parameter integer WORDS=2);')
    p = once(p, 'wire [1:0] p_cmd_ready,p_done,p_error,a_valid,a_bank,a_wide;',
             'wire [1:0] p_cmd_ready,p_done,p_error,a_bank,a_wide;\n wire [2*WORDS-1:0] a_valid;')
    for before, after in [('wire [5:0] a_row;', 'wire [6*WORDS-1:0] a_row;'),
                          ('wire [3:0] a_tile;', 'wire [4*WORDS-1:0] a_tile;'),
                          ('wire [255:0] a_data;', 'wire [256*WORDS-1:0] a_data;'),
                          ('shared_a_pool32 dut(.*);', 'shared_a_pool32 #(.A_WORDS_PER_BEAT(WORDS)) dut(.*);'),
                          ('reg [134:0] held_data[0:1];', 'reg [134*WORDS+1:0] held_data[0:1];\n integer dual_beats=0,single_beats=0,matrix_cases=0;')]:
        p = once(p, before, after)
    begin = p.index('    if(held[m])must(')
    end = p.index('    if(p_cmd_valid[m]', begin)
    p = p[:begin] + '''    if(held[m])must((|a_valid[m*WORDS+:WORDS])&&
     {a_valid[m*WORDS+:WORDS],a_bank[m],a_row[m*3*WORDS+:3*WORDS],a_tile[m*2*WORDS+:2*WORDS],a_wide[m],a_data[m*128*WORDS+:128*WORDS]}==held_data[m],"stalled A changed");
    held[m]=(|a_valid[m*WORDS+:WORDS])&&!a_ready[m];
    held_data[m]={a_valid[m*WORDS+:WORDS],a_bank[m],a_row[m*3*WORDS+:3*WORDS],a_tile[m*2*WORDS+:2*WORDS],a_wide[m],a_data[m*128*WORDS+:128*WORDS]};
    if(WORDS==2)must(a_valid[m*WORDS+:WORDS]!=WORDS'(2),"illegal high-only mask");
''' + p[end:]
    begin = p.index('    if(a_valid[m]&&a_ready[m])begin')
    end = p.index('    if(p_done[m])begin', begin)
    p = p[:begin] + '''    if((|a_valid[m*WORDS+:WORDS])&&a_ready[m])begin
     if(WORDS==2&&a_valid[m*WORDS+:WORDS]==WORDS'(3))dual_beats=dual_beats+1;else single_beats=single_beats+1;
     for(integer lane=0;lane<WORDS;lane=lane+1)if(a_valid[m*WORDS+lane])begin
      must(expected_live[m],"unexpected data from invalid/inactive descriptor");
      must(seen[m]<expected_total[m],"too many A containers");
      must(a_data[(m*WORDS+lane)*128+:128]==word_value(expected_base[m]+seen[m],generation),"SRAM data/address mismatch");
      must(a_bank[m]==expected_bank[m]&&a_wide[m]==expected_wide[m],"A bank/format tag mismatch");
      must(int'(a_row[(m*WORDS+lane)*3+:3])==seen[m]%expected_rows[m]&&int'(a_tile[(m*WORDS+lane)*2+:2])==seen[m]/expected_rows[m],"A row/tile order mismatch");
      seen[m]=seen[m]+1;a_words=a_words+1;
     end
    end
''' + p[end:]
    p = once(p, '!p_cmd_ready[m]&&!a_valid[m]', '!p_cmd_ready[m]&&!(|a_valid[m*WORDS+:WORDS])')
    anchor = '  mark=cycles;read_mark=reads;word_mark=a_words;\n  launch(3,2047,2,1,17,0,1,1,16,3);'
    p = once(p, anchor, '''  mark=cycles;read_mark=reads;word_mark=a_words;
  for(integer ri=0;ri<4;ri=ri+1)for(integer nt=1;nt<=4;nt=nt+1)for(integer off=0;off<4;off=off+1)begin
   integer nr;nr=ri==0?1:ri==1?3:ri==2?7:8;
   launch(3,off,nr,nt,17,64+off,nr,nt,17,0);drain(3,1);retire(3);matrix_cases=matrix_cases+1;
  end
  must(matrix_cases==64&&single_beats>0&&(WORDS==1||dual_beats>0),"lane/shape coverage missing");
  $display("POOL_MEASURE scenario=lane_matrix cycles=%0d reads=%0d a_words=%0d cases=%0d dual_beats=%0d single_beats=%0d",cycles-mark,reads-read_mark,a_words-word_mark,matrix_cases,dual_beats,single_beats);
  mark=cycles;read_mark=reads;word_mark=a_words;
  launch(3,2047,2,1,17,0,1,1,16,3);''')
    p = once(p, 'repeat(30000)@(posedge clk);', 'repeat(100000)@(posedge clk);')
    (out / 'tb_a32_pool.sv').write_bytes(p.encode('utf8'))
    # Baseline and candidate use one unchanged historical workload, including
    # lifecycle/lease checks. It is compatibility evidence, not a speed ratio.
    pair = (old / 'tb_shared_pair.sv').read_text(encoding='utf8')
    original = pair
    observed = once(original, 'endmodule', COMPAT_OBSERVER + '\nendmodule')
    pair = observed
    pair = once(pair, '.M_CONTEXTS(8)) dut(.*);', '.M_CONTEXTS(8),.A_WORDS_PER_BEAT(1)) dut(.*);')
    (out / 'tb_compat_candidate.sv').write_bytes(pair.encode('utf8'))
    (out / 'tb_compat_baseline.sv').write_bytes(observed.encode('utf8'))
    wide = once(original, '.M_CONTEXTS(8)) dut(.*);', '.M_CONTEXTS(8),.A_WORDS_PER_BEAT(2)) dut(.*);')
    wide = once(wide, 'if(dut.pool_a_valid[p]&&dut.pool_a_ready[p])shared_count[p]<=shared_count[p]+1;',
                "if((|dut.pool_a_valid[p*2+:2])&&dut.pool_a_ready[p])shared_count[p]<=shared_count[p]+int'(dut.pool_a_valid[p*2])+int'(dut.pool_a_valid[p*2+1]);")
    wide = once(wide, 'if(dut.groups[p].block_p.a_valid&&dut.groups[p].block_p.a_ready)a_count[p]<=a_count[p]+1;',
                "if((|dut.groups[p].block_p.a_valid)&&dut.groups[p].block_p.a_ready)a_count[p]<=a_count[p]+int'(dut.groups[p].block_p.a_valid[0])+int'(dut.groups[p].block_p.a_valid[1]);")
    (out / 'tb_lifecycle32.sv').write_bytes(wide.encode('utf8'))
    header = original[:original.index(' integer cycle=')]
    header = once(header, 'module tb_shared_pair #(parameter integer SHARED=1, TRUE_RW=1);',
                  'module tb_a32_pair #(parameter integer WORDS=2, CONTEXTS=8);')
    header = once(header, '.ENABLE_SHARED(SHARED),.ENABLE_LOCAL_RW(TRUE_RW)', '.ENABLE_SHARED(1),.ENABLE_LOCAL_RW(1)')
    header = once(header, '.M_CONTEXTS(8)) dut(.*);', '.M_CONTEXTS(CONTEXTS),.A_WORDS_PER_BEAT(WORDS)) dut(.*);')
    (out / 'tb_a32_pair.sv').write_bytes((header + (Path(__file__).parent/'pair_body.sv.inc').read_text(encoding='utf8')).encode('utf8'))
    return dict(frozen_benches={name: sha(old/name) for name in ('tb_shared_pool.sv', 'tb_shared_pair.sv')},
                generated_sha256={p.name: sha(p) for p in out.iterdir()})
