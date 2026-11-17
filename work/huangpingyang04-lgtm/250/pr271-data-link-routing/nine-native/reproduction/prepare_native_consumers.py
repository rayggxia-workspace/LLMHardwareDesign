"""Extend existing C operand and P A-load clients; no independent reader FSM."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import sys

ROOT = Path(sys.argv[1]).resolve()
assert ROOT.parent == Path('/public/home/yuzelu/PingyangHuang')
C = Path('/public/home/yuzelu/project-circuit/issue250-c-native-frame-20261112-01')
P = Path('/public/home/yuzelu/project-circuit/blockv2-p-cross-owner-XaVdUk')
PL = Path('/public/home/yuzelu/project-circuit/issue250-p-lc-coplacement-20261111-07/mapped/generated/p_lc')

def replace(s, old, new):
    assert s.count(old) == 1, (old, s.count(old))
    return s.replace(old, new)

def ports(prefix):
    return f'''    output wire {prefix}_valid, input wire {prefix}_ready,
    output wire [9:0] {prefix}_address,
    output wire [31:0] {prefix}_tag,
    input wire {prefix}_rsp_valid, output wire {prefix}_rsp_ready,
    input wire [31:0] {prefix}_rsp_tag,
    input wire [127:0] {prefix}_rsp_data,
'''

def connect(prefix):
    return ', '.join('.'+prefix+'_'+n for n in
                    ('valid','ready','address','tag','rsp_valid','rsp_ready','rsp_tag','rsp_data'))+',\n'

out = ROOT/'C'
out.mkdir()
for p in C.iterdir():
    if p.suffix in ('.sv','.lef','.tcl','.sdc') or p.name in ('config.mk','run.sh'):
        shutil.copyfile(p, out/p.name)

for name in ('cfj_group_c.sv','cfj_group_c_legacy.sv','block_cfj_cf.sv'):
    s = (out/name).read_text()
    marker = '    input wire late_e_valid,' if name=='block_cfj_cf.sv' else '    input wire  late_e_valid,'
    s = replace(s, marker, ports('projection_s')+marker)
    if name == 'cfj_group_c.sv':
        s = replace(s, '        .late_e_valid,', '        '+connect('projection_s')+'        .late_e_valid,')
    elif name == 'cfj_group_c_legacy.sv':
        s = replace(s, '.LANES(CLIENTS-2)', ".LANES(CLIENTS-2), .REMOTE_E32(1'b1)")
        s = replace(s, '        .late_e_valid(late_e_valid),', '        '+connect('projection_s')+'        .late_e_valid(late_e_valid),')
    else:
        s = replace(s, '        ucf_s_compute_client client (', '''        wire remote_valid, remote_ready, remote_rsp_valid, remote_rsp_ready;
        wire [9:0] remote_address;
        wire [31:0] remote_tag, remote_rsp_tag;
        wire [127:0] remote_rsp_data;
        if (i==0 && E32_ENABLE) begin: direct_projection_port
            assign projection_s_valid=remote_valid;
            assign projection_s_address=remote_address;
            assign projection_s_tag=remote_tag;
            assign projection_s_rsp_ready=remote_rsp_ready;
            assign remote_ready=projection_s_ready;
            assign remote_rsp_valid=projection_s_rsp_valid;
            assign remote_rsp_tag=projection_s_rsp_tag;
            assign remote_rsp_data=projection_s_rsp_data;
        end else begin: local_operands
            assign remote_ready=1'b0;
            assign remote_rsp_valid=1'b0;
            assign remote_rsp_tag=32'd0;
            assign remote_rsp_data=128'd0;
        end
        ucf_s_compute_client #(.REMOTE_A(E32_ENABLE && i==0)) client (
            .remote_valid, .remote_ready, .remote_address, .remote_tag,
            .remote_rsp_valid, .remote_rsp_ready, .remote_rsp_tag, .remote_rsp_data,''')
    (out/name).write_text(s)

name='ucf_native_service.sv'
s=(out/name).read_text()
s=replace(s,'parameter integer LANES=2','parameter integer LANES=2, parameter bit REMOTE_E32=0')
s=replace(s,'native2[31:19]!=0','(native2[31:20]!=0 || (native2[19] && !REMOTE_E32))')
s=replace(s,'if (native0[1:0]==0) meta[62]<=e32;',
          'if (native0[1:0]==0) begin meta[62]<=e32; if (REMOTE_E32 && e32) meta[61]<=native2[19]; end')
# Remote A remains a real read and is included in the native read-byte accounting.
(out/name).write_text(s)
name='ucf_s_compute_client.sv'
s=(out/name).read_text()
s=replace(s,'module ucf_s_compute_client (','module ucf_s_compute_client #(parameter bit REMOTE_A=0) (\n'+ports('remote').replace('remote_address','remote_address'))
s=replace(s,'    reg store_result;', '''    // Reuse the operand client's existing READ_REQ/READ_RSP states.
    wire remote_a = REMOTE_A && exec_meta[62] && exec_meta[61] && source_index==0;
    reg [31:0] remote_sequence;
    assign remote_valid = !reset && phase==READ_REQ && remote_a;
    assign remote_address = addresses[9:0];
    assign remote_tag = remote_sequence;
    assign remote_rsp_ready = !reset && phase==READ_RSP && remote_a;
    wire remote_match = remote_rsp_tag==remote_sequence;
    wire read_ready = remote_a ? remote_ready : s_req_ready;
    wire read_response = remote_a ? remote_rsp_valid && remote_match : s_rsp_valid;
    wire [127:0] read_data = remote_a ? remote_rsp_data : s_rsp_data;
    reg store_result;''')
s=replace(s,'(phase == READ_REQ || phase == WRITE_REQ)','((phase == READ_REQ && !remote_a) || phase == WRITE_REQ)')
s=replace(s,'(phase == READ_RSP || phase == WRITE_RSP)','((phase == READ_RSP && !remote_a) || phase == WRITE_RSP)')
s=replace(s,'            phase <= IDLE;','            phase <= IDLE;\n            remote_sequence <= 0;')
s=replace(s,'READ_REQ: if (s_req_ready)','READ_REQ: if (read_ready)')
s=replace(s,'READ_RSP: if (s_rsp_valid) begin','READ_RSP: if (read_response) begin\n                    if (remote_a) remote_sequence <= remote_sequence + 1;')
s=s.replace('exec_a <= s_rsp_data','exec_a <= read_data').replace('exec_b <= s_rsp_data','exec_b <= read_data').replace('exec_c <= s_rsp_data','exec_c <= read_data')
(out/name).write_text(s)

out=ROOT/'P'
out.mkdir()
sources=[Path(x) for x in (P/'sources.f').read_text().splitlines() if x]
for p in sources:
    assert not (out/p.name).exists(),p.name
    shutil.copyfile(p,out/p.name)
names=('p0_native_ffn_coplacement.sv','p_native_lc_coplacement.sv','p_native_coplacement_node.sv')
for name in names:
    s=(out/name).read_text()
    # This is a physically separate P2 variant. P0/P1 retain their original view.
    marker='  input logic clk,' if name==names[0] else ('  input logic clk,' if '  input logic clk,' in s else ' input logic clk,reset,')
    s=replace(s,marker,ports('down_s')+marker)
    if name==names[0]:
        marker='    .cp_valid(cp_valid),'
        if marker not in s:
            marker='    .scope_offer'
        assert '.cp_valid(cp_valid)' in s
        s=replace(s,'    .cp_valid(cp_valid),','    '+connect('down_s')+'    .cp_valid(cp_valid),')
    elif name==names[1]:
        s=replace(s,'    .cp_valid(cp_valid),','    '+connect('down_s')+'    .cp_valid(cp_valid),')
    else:
        # Route the native A-load client to the remote S owner. The existing
        # window, committed-prefix, tag, drain and M accumulation logic remains.
        s=s.replace('ar_valid&&allow_req', "1'b0")
        s=s.replace('(native_phase?ar_valid:aux_valid)&&allow_req', '(!native_phase&&aux_valid)&&allow_req')
        s=replace(s,' assign ar_ready=native_phase&&s_client_ready[2]&&allow_req;',
                    ' assign ar_ready=down_s_ready;\n assign down_s_valid=ar_valid;\n assign down_s_address=ar_address;\n assign down_s_tag=ar_tag;\n assign down_s_rsp_ready=ar_rsp_ready;')
        s=replace(s,' assign ar_rsp_valid=native_phase&&v[2]&&allow_rsp;',' assign ar_rsp_valid=down_s_rsp_valid;')
        s=replace(s,' assign ar_rsp_tag=tag[95:64];',' assign ar_rsp_tag=down_s_rsp_tag;')
        s=replace(s,' assign ar_rsp_data=data;',' assign ar_rsp_data=down_s_rsp_data;')
        s=s.replace('P reads before actual COPY acknowledgment','P reads before remote producer committed-prefix')
    (out/name).write_text(s)
(out/'sources.f').write_text('\n'.join(str(out/p.name) for p in sources)+'\n')
mapping=(P/'map250.ys').read_text()
for p in sources: mapping=mapping.replace(str(p),str(out/p.name))
(out/'map250.ys').write_text(mapping)
shutil.copyfile(P/'map250.sh',out/'map250.sh')
shutil.copyfile(P/'prepare_place250.py',out/'prepare_place250.py')
manifest={}
for kind in ('C','P'):
    manifest[kind]={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/kind).glob('*.sv')}
(ROOT/'native-source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Prepared native clients in C/P; added no reader module or top-level reader block.')
