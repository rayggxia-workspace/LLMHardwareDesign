"""Generate reviewed glue around unmodified main64 controller/service profiles."""
from pathlib import Path
import argparse,json,re
from contract import ROOT,HERE,common_ports


def instance(module,name,pins,params=''):
    return module+(' #('+params+')' if params else '')+' '+name+'(\n'+',\n'.join('    .'+p+'('+v+')' for p,v in pins.items())+'\n);\n'


def endpoint():
    old=(ROOT/'project/control_five_boot_v1/native_control_endpoint.sv').read_text()
    header=old[:old.index('\n);')].replace('module native_control_endpoint #','module main64_endpoint #',1)
    header+=''',
    input wire incoming_valid, output wire incoming_ready,
    input wire [9:0] incoming_addr, input wire [127:0] incoming_data,
    output wire incoming_ack, input wire incoming_ack_ready,
    output wire outgoing_valid, input wire outgoing_ready,
    output wire [9:0] outgoing_addr, output wire [127:0] outgoing_data,
    input wire outgoing_ack, output wire outgoing_ack_ready,
    output wire rx_reserved, output wire [9:0] rx_reserved_addr,
    input wire peer_reserved, input wire [9:0] peer_addr
);
    wire reset=!rst_ni;
    reg [31:0] task_job,task_epoch,task_sequence;
    reg [7:0] native_epoch;
    reg tx_owned;
    always @(posedge clk_i) begin
        if(reset) begin task_job<=0;task_epoch<=0;task_sequence<=0;native_epoch<=0;tx_owned<=0;end
        else begin
            if(release_valid_i && release_ready_o) native_epoch<=release_epoch_i[7:0];
            if(task_valid_i && task_ready_o && task_packet_i[16+:8]==0)begin
                task_job<=task_packet_i[32+:32];task_epoch<=task_packet_i[64+:32];task_sequence<=task_packet_i[96+:32];
            end
            if(outgoing_valid && outgoing_ready)tx_owned<=1;
            if(outgoing_ack && outgoing_ack_ready)tx_owned<=0;
        end
    end
    generate
'''
    common={n:n for n in common_ports()}
    code=header
    for kind,letter in enumerate('ufcpj'):
        code+=('    if' if kind==0 else '    else if')+f'(KIND=={kind})begin: {letter}\n'
        pins=common.copy();params=''
        if kind in (0,3):
            pins.pop('clk_i');pins['clk']='clk_i';pins.update(block_id_i='BLOCK',topology_id_i='TOPOLOGY_ID',late_path_enable="1'b1")
            for direction,name in re.findall(r'(input|output) wire\s*(?:\[\d+:\d+\])?\s*(close_\w+)',(ROOT/'project/control_rtl_min_v0_1/ports.svh').read_text()):
                pins[name]="'0" if direction=='input' else ''
        else:
            params='.BLOCK_ID(BLOCK),.TOPOLOGY_ID(TOPOLOGY_ID)'
            for name in re.findall(r'output wire\s*(?:\[\d+:\d+\])?\s*(trace_\w+)',(ROOT/'project/control_rtl_min_v0_1/ports.svh').read_text()):pins[name]=''
        if kind!=4:
            code+='    assign {fragment_ready_o,fragment_rsp_valid_o,fragment_error_o,native_result_valid_o}=0;\n'
            code+='    assign native_result_packet_o=0;\n    assign native_pending_o=tx_owned || outgoing_valid || incoming_ack;\n'
        if kind==0:
            code+='''    wire data_ready,data_stored,route_valid,route_ready;
    wire [127:0] route_data;
    wire host_write=host_req_valid_i && host_req_write_i;
    assign host_req_ready_o=host_req_write_i && data_ready;
    assign host_rsp_valid_o=data_stored && !incoming_valid;
    assign host_rsp_data_o=0;
    assign incoming_ready=data_ready && !host_write;
    assign incoming_ack=data_stored && !host_write;
'''
            pins.update(incoming_valid='host_write || incoming_valid',incoming_ready='data_ready',
                incoming_addr='host_write ? host_req_address_i : incoming_addr',
                incoming_data='host_write ? host_req_data_i : incoming_data',incoming_ack='data_stored',
                incoming_ack_ready='host_rsp_ready_i || incoming_ack_ready',
                link_rx_reserved='rx_reserved',link_rx_addr='rx_reserved_addr',
                peer_rx_reserved='peer_reserved',peer_rx_addr='peer_addr',
                n_to_e_valid='route_valid',n_to_e_data='route_data',n_to_e_ready='route_ready',
                e_direct_a_valid='route_valid',e_direct_a_data='route_data',e_direct_a_ready='route_ready')
            pins.update({n:n for n in ('outgoing_valid','outgoing_ready','outgoing_addr','outgoing_data','outgoing_ack','outgoing_ack_ready')})
            module='r82_u_pu_u_controlled_64'
        elif kind in (1,2):
            code+='''    wire data_ready,data_stored,verify_valid,route_valid,route_take;
    wire [127:0] verify_data;
    wire [31:0] route_data;
    reg [1:0] read_state;
    reg [9:0] read_address;
    wire host_write=host_req_valid_i && host_req_write_i;
    wire read_take=read_state==2 && host_rsp_ready_i;
    assign host_req_ready_o=read_state==0 && (host_req_write_i ? data_ready : 1'b1);
    assign host_rsp_valid_o=read_state==2 || data_stored && !incoming_valid;
    assign host_rsp_data_o=read_state==2 ? verify_data : 128'b0;
    assign incoming_ready=data_ready && !host_write && read_state==0;
    assign incoming_ack=data_stored && !host_write;
    always @(posedge clk_i)begin
        if(reset)begin read_state<=0;read_address<=0;end
        else case(read_state)
            0:if(host_req_valid_i && host_req_ready_o && !host_req_write_i)begin read_address<=host_req_address_i;read_state<=1;end
            1:if(verify_valid)read_state<=2;
            2:if(read_take)read_state<=0;
            default:read_state<=0;
        endcase
    end
'''
            pins.update(rx_valid='host_write || incoming_valid',rx_ready='data_ready',rx_addr='host_write ? host_req_address_i : incoming_addr',
                rx_data='host_write ? host_req_data_i : incoming_data',rx_stored='data_stored',rx_stored_ready='host_rsp_ready_i || incoming_ack_ready',
                peer_reserved='peer_reserved',peer_addr='peer_addr',rx_reserved='rx_reserved',rx_reserved_addr='rx_reserved_addr',
                verify_read='read_state==1',verify_addr='read_address',verify_take='read_take',verify_valid='verify_valid',verify_data='verify_data',
                late_g_valid='route_valid',late_g_data='route_data',late_g_take='route_take',
                late_e_valid='route_valid',late_e_data='route_data',late_e_take='route_take')
            pins.update({n:n for n in ('outgoing_valid','outgoing_ready','outgoing_addr','outgoing_data','outgoing_ack','outgoing_ack_ready')})
            module=f'r82_{letter}_cfj_group_{letter}'
        elif kind==3:
            code+='''    wire [1:0] io_ready,io_valid;
    wire [255:0] io_data;
    wire route_valid,route_take;
    wire [31:0] route_data;
    assign host_req_ready_o=io_ready[0];assign host_rsp_valid_o=io_valid[0];assign host_rsp_data_o=io_data[127:0];
    assign incoming_ready=io_ready[1] && life_o==5;
    assign incoming_ack=io_valid[1];
    assign rx_reserved=life_o==5;assign rx_reserved_addr=incoming_addr;
    assign {outgoing_valid,outgoing_addr,outgoing_data,outgoing_ack_ready}=0;
'''
            pins.update(io_req_valid='{incoming_valid && life_o==5,host_req_valid_i}',io_req_write="{1'b1,host_req_write_i}",
                io_req_addr='{incoming_addr,host_req_address_i}',io_req_data='{incoming_data,host_req_data_i}',
                io_req_ready='io_ready',io_rsp_valid='io_valid',io_rsp_ready='{incoming_ack_ready,host_rsp_ready_i}',io_rsp_data='io_data',
                m_to_g_valid='route_valid',m_to_g_data='route_data',m_to_g_take='route_take',
                g_from_m_valid='route_valid',g_from_m_data='route_data',g_from_m_take='route_take')
            module='r82_p_pu_p_controlled_64'
        else:
            code+='''    wire [1:0] io_ready,io_valid;
    wire [255:0] io_data;
    wire out_valid,out_take,out_last,route_valid,route_take;
    wire [127:0] out_data,route_data;
    wire [31:0] out_tag;
    wire [9:0] out_index;
    reg [511:0] packet;
    assign {host_req_ready_o,host_rsp_valid_o}=0;assign host_rsp_data_o=0;
    assign {incoming_ready,incoming_ack,outgoing_valid,outgoing_addr,outgoing_data,outgoing_ack_ready,rx_reserved,rx_reserved_addr}=0;
    assign fragment_ready_o=io_ready[0];assign fragment_rsp_valid_o=io_valid[0];
    always @*begin
        packet=0;packet[127:0]=out_data;packet[159:128]=out_tag;packet[169:160]=out_index;packet[170]=out_last;
        packet[202:171]=task_job;packet[234:203]=task_epoch;packet[266:235]=task_sequence;
    end
    native_result_fifo #(.DEPTH(4)) results(.clk_i,.rst_ni,.push_valid_i(out_valid),.push_ready_o(out_take),.push_packet_i(packet),
        .pop_valid_o(native_result_valid_o),.pop_ready_i(native_result_ready_i),.pop_packet_o(native_result_packet_o),.pending_o(native_pending_o));
'''
            pins.update(io_req_valid="{1'b0,fragment_valid_i}",io_req_write="2'b01",io_req_addr="{10'b0,fragment_address_i}",
                io_req_data="{128'b0,fragment_data_i}",io_req_ready='io_ready',io_rsp_valid='io_valid',
                io_rsp_ready="{1'b0,fragment_rsp_ready_i}",io_rsp_data='io_data',active_epoch='native_epoch',
                rx_tag='fragment_tag_i',rx_slot='fragment_slot_i',rx_last='fragment_last_i',rx_error='fragment_error_o',
                out_valid='out_valid',out_take='out_take',out_data='out_data',out_tag='out_tag',out_index='out_index',out_last='out_last',
                late_e_valid='route_valid',late_e_take='route_take',late_e_data='route_data',late_s_valid='route_valid',late_s_take='route_take',late_s_data='route_data')
            module='r82_j_cfj_group_j'
        code+=instance(module,'implementation',pins,params)+'    end\n'
    code+='    endgenerate\nendmodule\n'
    return code


def control_top():
    text=(ROOT/'project/control_five_boot_v1/five_control_top.sv').read_text()
    header,body=text.split('\n);',1)
    pm_decls=[];kept=[]
    for line in header.splitlines():
        if re.search(r'\bpm_\w+',line):pm_decls.append(re.sub(r'\b(?:input|output) wire','wire',line).rstrip(',')+';')
        else:kept.append(line)
    header='\n'.join(kept).replace('module five_control_top #(parameter integer KIND=0)',
        'module main64_control_top #(parameter integer KIND0=0, KIND1=KIND0)')
    text=header+'\n);\n'+'\n'.join(pm_decls)+body
    text=text.replace("mc_min_controller #(.STALL_LIMIT(4096),.NATIVE_ABI_ID(32'h01930001))", "mother_control_64 #(.NATIVE_ABI_ID(32'h01930001))")
    start=text.index('    mother_control_64 #');end=text.index('\n    );',start)
    part=text[start:end];part='\n'.join(l for l in part.splitlines() if not re.search(r'\.pm_\w+',l))
    text=text[:start]+part+text[end:]
    text=text.replace('.KIND(KIND),.TOPOLOGY_ID(32\'h01930011+KIND)) local0', '.KIND(KIND0),.TOPOLOGY_ID(32\'h01938000+KIND0*16+KIND1)) local0')
    text=text.replace('.KIND(KIND),.TOPOLOGY_ID(32\'h01930011+KIND)) local1', '.KIND(KIND1),.TOPOLOGY_ID(32\'h01938000+KIND0*16+KIND1)) local1')
    text=text.replace('native_control_endpoint #','main64_endpoint #')
    for i in range(2):
        start=text.index(f'    main64_endpoint #(.BLOCK(8\'d{i})');end=text.index('\n    );',start)
        part=text[start:end]
        pins=dict(incoming_valid=f'incoming_valid[{i}]',incoming_ready=f'incoming_ready[{i}]',incoming_addr=f'incoming_address[{10*i}+:10]',incoming_data=f'incoming_data[{128*i}+:128]',
            incoming_ack=f'incoming_ack[{i}]',incoming_ack_ready=f'incoming_ack_ready[{i}]',outgoing_valid=f'forward_valid[{i}]',outgoing_ready=f'forward_ready[{i}]',outgoing_addr=f'forward_address[{10*i}+:10]',outgoing_data=f'forward_data[{128*i}+:128]',
            outgoing_ack=f'forward_ack[{i}]',outgoing_ack_ready=f'forward_ack_ready[{i}]',rx_reserved=f'rx_reserved[{i}]',rx_reserved_addr=f'rx_address[{10*i}+:10]',peer_reserved=f'rx_reserved[{1-i}]',peer_addr=f'rx_address[{10*(1-i)}+:10]')
        part+=',\n'+',\n'.join('.'+k+'('+v+')' for k,v in pins.items())
        text=text[:start]+part+text[end:]
    old='    assign link_pending_o=|native_pending_o;\n    assign ack_rejected_o=0;assign commit_count_o=0;assign ack_count_o=0;'
    new='''    for(genvar k=1;k<3;k=k+1)begin: programs
        control_pm #(.USE_SRAM(1'b1)) pm(.clk_i,.rst_ni(core_rst_ni),
            .req_valid_i(pm_req_valid_o[k]),.req_write_i(pm_req_write_o[k]),.req_address_i(pm_req_address_o[k*14+:14]),
            .req_data_i(pm_req_data_o[k*128+:128]),.req_ready_o(pm_req_ready_i[k]),
            .rsp_valid_o(pm_rsp_valid_i[k]),.rsp_ready_i(pm_rsp_ready_o[k]),.rsp_data_o(pm_rsp_data_i[k*128+:128]),.rsp_error_o(pm_rsp_error_i[k]));
    end
    assign {pm_req_valid_o[0],pm_req_write_o[0],pm_rsp_ready_o[0],pm_req_address_o[0+:14],pm_req_data_o[0+:128]}=0;
    assign {pm_req_ready_i[0],pm_rsp_valid_i[0],pm_rsp_error_i[0],pm_rsp_data_i[0+:128]}=0;
    for(genvar k=0;k<2;k=k+1)begin: data_link
        assign incoming_valid[k]=forward_valid[1-k] && run_active;
        assign incoming_address[k*10+:10]=forward_address[(1-k)*10+:10];
        assign incoming_data[k*128+:128]=forward_data[(1-k)*128+:128];
        assign forward_ready[k]=incoming_ready[1-k] && run_active;
        assign forward_ack[k]=incoming_ack[1-k];
        assign incoming_ack_ready[k]=forward_ack_ready[1-k];
    end
    reg [31:0] commits,acks;
    always @(posedge clk_i)begin
        if(reset)begin commits<=0;acks<=0;end
        else begin
            commits<=commits+32'(incoming_ack[0] && incoming_ack_ready[0])+32'(incoming_ack[1] && incoming_ack_ready[1]);
            acks<=acks+32'(forward_ack[0] && forward_ack_ready[0])+32'(forward_ack[1] && forward_ack_ready[1]);
        end
    end
    assign link_pending_o=|native_pending_o || |host_pending || |fragment_pending;
    assign ack_rejected_o=0;assign commit_count_o=commits;assign ack_count_o=acks;'''
    assert text.count(old)==1;text=text.replace(old,new)
    return text


def host_front():
    text=(ROOT/'project/control_five_boot_v1/typed_boot_front.sv').read_text()
    text=text.replace('module typed_boot_front #(parameter integer KIND=0)', 'module main64_host_front #(parameter integer KIND0=0, KIND1=KIND0)')
    anchor='    wire special=cmd_op_i==13'
    start=text.index(anchor);end=text.index('\n    assign cmd_ready_o',start)
    text=text[:start]+'''    wire [2:0] selected_kind=cmd_target_i==2 ? 3'(KIND1) : 3'(KIND0);
    wire data_target=cmd_target_i==1 || cmd_target_i==2;
    wire unsupported_read=data_target && cmd_op_i==11 && (selected_kind==0 || selected_kind==4);
    wire blocked_write=data_target && cmd_op_i==12 && (selected_kind==4 || deployed_i);
    wire bad_epoch=cmd_op_i==0 && (KIND0==4 || KIND1==4) && cmd_data_i[63:32]>255;
    wire bad_topology=cmd_op_i==1 && cmd_target_i<3 && cmd_data_i[111:80]!=(32'h01938000+KIND0*16+KIND1);
    wire special=cmd_op_i==13 || cmd_op_i==14 || unsupported_read || blocked_write || bad_epoch || bad_topology;'''+text[end:]
    text=text.replace('input wire run_active_i,', 'input wire deployed_i,input wire run_active_i,')
    start=text.index('                    if(KIND!=4');end=text.index('                    else if(cmd_target_i',start)
    text=text[:start]+'''                    if(bad_topology)status<=3;
                    else if(bad_epoch)status<=16'h103;
                    else if(unsupported_read || (blocked_write && selected_kind==4))status<=4;
                    else if(blocked_write)status<=16'h106;
                    else if(selected_kind!=4)status<=4;
'''+text[end:]
    return text


def boot_top():
    text=(ROOT/'project/control_five_boot_v1/five_boot_top.sv').read_text()
    text=text.replace('module five_boot_top #(parameter integer KIND=0,parameter bit PM_USE_SRAM=1)',
        'module main64_boot_top #(parameter integer KIND0=0, KIND1=KIND0)')
    text=text.replace('five_control_top #(.KIND(KIND))','main64_control_top #(.KIND0(KIND0),.KIND1(KIND1))')
    text=text.replace('typed_boot_front #(.KIND(KIND))','main64_host_front #(.KIND0(KIND0),.KIND1(KIND1))')
    text=text.replace('.run_active_i(run_active_o),','.deployed_i(deploy_valid_i),.run_active_i(run_active_o),')
    start=text.index('    for(genvar k=0;k<3;');text=text[:start]+'endmodule\n'
    return text


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=HERE);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    for name,build in [('main64_endpoint',endpoint),('main64_control_top',control_top),('main64_host_front',host_front),('main64_boot_top',boot_top)]:
        (a.out/(name+'.sv')).write_text(build(),encoding='utf-8',newline='\n')
    print('PASS generated R8.2 control glue')


if __name__=='__main__':main()
