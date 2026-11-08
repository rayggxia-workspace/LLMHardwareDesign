"""Generate supervised main64 glue; preserve main native cores and service recipes."""
from pathlib import Path
import argparse,re
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];BOOT=ROOT/'project/control_main64_boot_v1'
def sub(text,old,new,count=1):
    assert text.count(old)==count,(old,text.count(old),count)
    return text.replace(old,new)

def endpoint():
    s=(BOOT/'main64_endpoint.sv').read_text().replace('module main64_endpoint #','module main64_recovery_endpoint #',1)
    at=s.index('    input wire clk_i')
    s=s[:at]+"""    input wire halt_i,job_start_i,commit_i,
    output wire safe_o,output reg fault_o,
    output reg [31:0] observed_reads_o,observed_writes_o,
    output reg [130:0] send_identity_o,reserve_identity_o,
    output reg [31:0] join_tag_o,
    output wire [31:0] task_job_o,task_epoch_o,task_sequence_o,
"""+s[at:]
    s=s.replace('implementation(','implementation(\n    .halt_i(halt_i),.request_seen_o(request_seen),.response_seen_o(response_seen),\n    .request_descriptor_o(request_descriptor),.request_identity_o(request_identity),\n    .response_status_o(response_status),.response_reads_o(response_reads),.response_writes_o(response_writes),',5)
    at=s.index('    wire reset=!rst_ni;')
    s=s[:at]+"""    wire request_seen,response_seen;
    wire [1023:0] request_descriptor;wire [130:0] request_identity;
    wire [15:0] response_status;wire [31:0] response_reads,response_writes;
    reg service_active;reg [15:0] active_op;
    assign safe_o=!service_active && !native_pending_o;
    assign task_job_o=task_job;assign task_epoch_o=task_epoch;assign task_sequence_o=task_sequence;
    always @(posedge clk_i)begin
        if(!rst_ni)begin
            service_active<=0;active_op<=0;fault_o<=0;observed_reads_o<=0;observed_writes_o<=0;
            send_identity_o<=0;reserve_identity_o<=0;join_tag_o<=0;
        end else begin
            if(job_start_i)begin fault_o<=0;observed_reads_o<=0;observed_writes_o<=0;end
            else begin
                observed_reads_o<=observed_reads_o+(response_seen ? response_reads : 32'd0);
                observed_writes_o<=observed_writes_o+(response_seen && active_op!=16'h102 ? response_writes : 32'd0)+(commit_i ? 32'd16 : 32'd0);
            end
            if(request_seen)begin
                service_active<=1;active_op<=request_descriptor[47:32];
                if(request_descriptor[47:32]==16'h101 || request_descriptor[47:32]==16'h120)send_identity_o<=request_identity;
                if(request_descriptor[47:32]==16'h103)reserve_identity_o<=request_identity;
                if(request_descriptor[47:32]==16'h120)join_tag_o<=request_descriptor[575:544];
            end
            if(response_seen)begin service_active<=0;if(!halt_i && response_status!=0)fault_o<=1;end
        end
    end
"""+s[at:]
    s=sub(s,'.pop_ready_i(native_result_ready_i)','.pop_ready_i(native_result_ready_i || halt_i)')
    return s

ROUTE_PORTS="""    input wire halt_i,route_update_i,route_direction_i,
    input wire [9:0] route_base_i,input wire [2:0] route_count_i,input wire [31:0] route_first_i,route_tag_i,
    input wire [7:0] route_stride_i,
    output wire quiescent_o,fault_o,output wire [31:0] observed_reads_o,observed_writes_o,
"""
def control():
    s=(BOOT/'main64_control_top.sv').read_text().replace('module main64_control_top #','module main64_recovery_control #',1)
    at=s.index('    input wire clk_i');s=s[:at]+ROUTE_PORTS+s[at:]
    s=s.replace('main64_endpoint #','main64_recovery_endpoint #')
    for k in (0,1):
        at=s.index(f')) local{k}(')+len(f')) local{k}(')
        hooks=f"""
        .halt_i(halt_i),.job_start_i(start_valid_i && start_ready_o),.commit_i(store_commit[{1-k}]),
        .safe_o(endpoint_safe[{k}]),.fault_o(endpoint_fault[{k}]),
        .observed_reads_o(endpoint_reads[{k*32}+:32]),.observed_writes_o(endpoint_writes[{k*32}+:32]),
        .send_identity_o(send_identity[{k*131}+:131]),.reserve_identity_o(reserve_identity[{k*131}+:131]),
        .join_tag_o(join_tags[{k*32}+:32]),.task_job_o(task_jobs[{k*32}+:32]),
        .task_epoch_o(task_epochs[{k*32}+:32]),.task_sequence_o(task_sequences[{k*32}+:32]),"""
        s=s[:at]+hooks+s[at:]
        for name,old,new in [
            ('task_valid_i',f'local_task_valid[{k}]',f'local_task_valid[{k}] && !halt_i'),
            ('event_valid_o',f'local_event_valid[{k}]',f'raw_event_valid[{k}]'),
            ('event_ready_i',f'local_event_ready[{k}]',f'raw_event_ready[{k}]'),
            ('outgoing_valid',f'forward_valid[{k}]',f'native_forward_valid[{k}]'),
            ('outgoing_ready',f'forward_ready[{k}]',f'native_forward_ready[{k}]'),
            ('outgoing_addr',f'forward_address[{k*10}+:10]',f'native_forward_address[{k*10}+:10]'),
            ('outgoing_data',f'forward_data[{k*128}+:128]',f'native_forward_data[{k*128}+:128]'),
            ('outgoing_ack',f'forward_ack[{k}]',f'native_forward_ack[{k}]'),
            ('outgoing_ack_ready',f'forward_ack_ready[{k}]',f'native_forward_ack_ready[{k}]'),
            ('peer_reserved',f'rx_reserved[{1-k}]',f'rx_reserved[{1-k}] || halt_i'),
            ('peer_addr',f'rx_address[{(1-k)*10}+:10]',f"halt_i ? native_forward_address[{k*10}+:10] : (({'KIND1' if k==0 else 'KIND0'}==3) ? route_base[{k}]+10'(route_done[{k}]) : rx_address[{(1-k)*10}+:10])"),
            ('native_result_valid_o',f'native_result_valid_o[{k}+:1]',f'native_result_raw_valid[{k}]'),
            ('native_result_ready_i',f'native_result_ready_i[{k}+:1]',f'native_result_take[{k}]'),
            ('native_result_packet_o',f'native_result_packet_o[{k*512}+:512]',f'native_result_raw_packet[{k*512}+:512]'),
        ]:s=sub(s,f'.{name}({old})',f'.{name}({new})')
    s=sub(s,'    wire [31:0] mc_trace_pc_o;','''    wire [1:0] endpoint_safe,endpoint_fault,store_commit,raw_event_valid,raw_event_ready;
    wire [63:0] endpoint_reads,endpoint_writes,task_jobs,task_epochs,task_sequences,join_tags;
    wire [261:0] send_identity,reserve_identity;
    wire [1:0] native_forward_valid,native_forward_ready,native_forward_ack,native_forward_ack_ready;
    wire [19:0] native_forward_address;
    wire [255:0] native_forward_data;
    wire [1:0] native_result_raw_valid,native_result_take;
    wire [1023:0] native_result_raw_packet;
    wire [31:0] mc_trace_pc_o;''')
    start=s.index('    for(genvar k=0;k<2;k=k+1)begin: data_link')
    s=s[:start]+"""    reg [31:0] current_job,current_epoch,current_sequence,current_generation;
    reg [1:0] route_enabled,j_owned;
    reg [9:0] route_base[0:1];reg [2:0] route_count[0:1],route_done[0:1];
    reg [31:0] route_first[0:1],route_tag[0:1];reg [7:0] route_stride[0:1];
    wire [1:0] link_busy,link_fault,link_ack_valid,link_ack_ready,link_abort,link_committed;
    wire [1023:0] ticket,ack_identity;
    reg [511:0] saved_ticket[0:1];
    reg [31:0] commits,acks;
    reg [1:0] bad_ack;
    assign observed_reads_o=endpoint_reads[31:0]+endpoint_reads[63:32];
    assign observed_writes_o=endpoint_writes[31:0]+endpoint_writes[63:32];
    assign quiescent_o=(&endpoint_safe) && !(|link_busy) && !(|host_pending) && !(|fragment_pending);
    assign fault_o=(|endpoint_fault) || (|poison_o) || mc_trace_aborting_o || (|link_fault) || (|bad_ack) || (|bad_j_packet);
    assign ack_rejected_o=|bad_ack;
    assign commit_count_o=commits;assign ack_count_o=acks;
    assign link_pending_o=|native_pending_o || |host_pending || |fragment_pending || |link_busy;
    wire [1:0] bad_j_packet;
    always @(posedge clk_i)begin
        if(reset)begin
            current_job<=0;current_epoch<=0;current_sequence<=0;current_generation<=0;
            route_enabled<=0;j_owned<=0;commits<=0;acks<=0;bad_ack<=0;
            for(integer i=0;i<2;i=i+1)begin
                route_base[i]<=0;route_count[i]<=0;route_done[i]<=0;route_first[i]<=0;route_stride[i]<=0;route_tag[i]<=0;saved_ticket[i]<=0;
            end
        end else begin
            if(route_update_i)begin
                route_enabled[route_direction_i]<=route_count_i!=0;
                route_base[route_direction_i]<=route_base_i;route_count[route_direction_i]<=route_count_i;
                route_first[route_direction_i]<=route_first_i;route_stride[route_direction_i]<=route_stride_i;route_tag[route_direction_i]<=route_tag_i;
            end
            if(start_valid_i && start_ready_o)begin
                current_job<=start_job_i;current_epoch<=start_epoch_i;current_sequence<=start_sequence_i;current_generation<=start_generation_i;
                route_done[0]<=0;route_done[1]<=0;commits<=0;acks<=0;bad_ack<=0;
            end else begin
                commits<=commits+32'(store_commit[0])+32'(store_commit[1]);
                acks<=acks+32'(link_ack_valid[0] && link_ack_ready[0] && link_committed[0])+32'(link_ack_valid[1] && link_ack_ready[1] && link_committed[1]);
            end
            for(integer i=0;i<2;i=i+1)begin
                if(forward_valid[i] && forward_ready[i])begin saved_ticket[i]<=ticket[i*512+:512];if((i==0 ? KIND0 : KIND1)==4)j_owned[i]<=1;end
                if(link_ack_valid[i] && ack_identity[i*512+:512]!=saved_ticket[i])bad_ack[i]<=1;
                if(link_ack_valid[i] && link_ack_ready[i])begin
                    j_owned[i]<=0;
                    if(link_committed[i])route_done[i]<=route_done[i]+1'b1;
                end
            end
        end
    end
    for(genvar k=0;k<2;k=k+1)begin: links
        localparam integer KIND=k==0 ? KIND0 : KIND1;
        localparam integer PEER=k==0 ? KIND1 : KIND0;
        wire routed=route_enabled[k] && route_done[k]<route_count[k];
        wire [511:0] jpacket=native_result_raw_packet[k*512+:512];
        wire [130:0] identity=send_identity[k*131+:131];
        wire [130:0] destination_identity=PEER==3 ? {current_job,current_epoch,32'b0,32'b0,3'b0} : reserve_identity[(1-k)*131+:131];
        wire [31:0] expected_sequence=route_first[k]+32'(route_done[k])*32'(route_stride[k]);
        wire jgood=jpacket[202:171]==current_job && jpacket[234:203]==current_epoch &&
                   jpacket[266:235]==task_sequences[k*32+:32] && jpacket[159:128]==route_tag[k] &&
                   join_tags[k*32+:32]==route_tag[k] && jpacket[169:160]==10'(route_done[k]) &&
                   jpacket[170]==(route_done[k]+1'b1==route_count[k]);
        assign bad_j_packet[k]=KIND==4 && run_active && routed && native_result_raw_valid[k] && !jgood;
        assign forward_valid[k]=KIND==4 ? routed && !j_owned[k] && native_result_raw_valid[k] && jgood && !halt_i :
            native_forward_valid[k] && (run_active || halt_i);
        assign forward_address[k*10+:10]=KIND==4 ? route_base[k]+10'(route_done[k]) : native_forward_address[k*10+:10];
        assign forward_data[k*128+:128]=KIND==4 ? jpacket[127:0] : native_forward_data[k*128+:128];
        assign native_forward_ready[k]=KIND!=4 && forward_ready[k];
        assign native_forward_ack[k]=KIND!=4 && link_ack_valid[k] && ack_identity[k*512+:512]==saved_ticket[k];
        assign link_ack_ready[k]=(KIND==4 ? j_owned[k] : native_forward_ack_ready[k]) && ack_identity[k*512+:512]==saved_ticket[k];
        assign native_result_take[k]=KIND==4 && route_enabled[k] ? (j_owned[k] && link_ack_valid[k] && link_ack_ready[k]) : native_result_ready_i[k];
        assign native_result_valid_o[k]=native_result_raw_valid[k] && !route_enabled[k];
        assign native_result_packet_o[k*512+:512]=native_result_raw_packet[k*512+:512];
        wire event_blocked=KIND==4 && route_enabled[k] && route_done[k]<route_count[k] && return_packets[k*512+16+:8]>=2 && !halt_i;
        assign local_event_valid[k]=raw_event_valid[k] && !event_blocked;
        assign raw_event_ready[k]=local_event_ready[k] && !event_blocked;
        wire source_legal=routed && identity[130:99]==current_job && identity[98:67]==current_epoch &&
            identity[66:35]==task_sequences[k*32+:32] && identity[34:3]==expected_sequence && identity[2:0]==0 &&
            forward_address[k*10+:10]==route_base[k]+10'(route_done[k]);
        wire destination_reserved=PEER==3 ? life_o[(2-k)*4+:4]==5 :
            rx_reserved[1-k] && rx_address[(1-k)*10+:10]==forward_address[k*10+:10] &&
            destination_identity[130:99]==current_job && destination_identity[98:67]==current_epoch &&
            destination_identity[66:35]==task_sequences[(1-k)*32+:32] && destination_identity[2:0]==0 &&
            destination_identity[34:3]==(route_done[k]==0 ? 32'd0 : route_first[1-k]+32'd2);
        reg [511:0] formed_ticket;
        always @*begin
            formed_ticket=0;formed_ticket[130:0]=identity;formed_ticket[261:131]=destination_identity;
            formed_ticket[293:262]=current_generation;formed_ticket[325:294]=current_sequence;
            formed_ticket[357:326]=32'h01938000+KIND0*16+KIND1;
            formed_ticket[389:358]=k==0 ? image_id0 : image_id1;formed_ticket[421:390]=k==0 ? image_id1 : image_id0;
            formed_ticket[429:422]=8'(k);formed_ticket[437:430]=8'(1-k);
            formed_ticket[447:438]=forward_address[k*10+:10];formed_ticket[479:448]=KIND==4 ? route_tag[k] : 32'd0;
            formed_ticket[489:480]=10'(route_done[k]);
        end
        assign ticket[k*512+:512]=formed_ticket;
        main64_guarded_link transfer(.clk_i,.rst_ni(core_rst_ni),.halt_i,.source_valid(forward_valid[k]),.source_ready(forward_ready[k]),
            .source_legal,.source_address(forward_address[k*10+:10]),.source_data(forward_data[k*128+:128]),.source_identity(ticket[k*512+:512]),
            .destination_reserved,.destination_valid(incoming_valid[1-k]),.destination_ready(incoming_ready[1-k]),
            .destination_address(incoming_address[(1-k)*10+:10]),.destination_data(incoming_data[(1-k)*128+:128]),
            .destination_ack(incoming_ack[1-k]),.destination_ack_ready(incoming_ack_ready[1-k]),
            .ack_valid(link_ack_valid[k]),.ack_ready(link_ack_ready[k]),.ack_identity(ack_identity[k*512+:512]),
            .ack_abort(link_abort[k]),.ack_committed(link_committed[k]),.store_commit(store_commit[k]),.busy(link_busy[k]),.fault_o(link_fault[k]));
    end
endmodule
"""
    return s

def engine():
    s=(BOOT/'main64_boot_top.sv').read_text().replace('module main64_boot_top #','module main64_recovery_engine #',1)
    at=s.index('    input wire clk_i');s=s[:at]+ROUTE_PORTS+'    output wire engine_result_valid_o,\n'+s[at:]
    s=s.replace('main64_control_top #','main64_recovery_control #')
    s=sub(s,' control(.*);',' control(.*);\n    assign engine_result_valid_o=result_valid_o;')
    return s

def supervisor():
    s=(ROOT/'project/control_recovery_boot_v1/recovery_supervisor.sv').read_text().replace(
        'module recovery_supervisor #(parameter integer DRAIN_LIMIT=1024)(',
        'module main64_recovery_supervisor #(parameter integer DRAIN_LIMIT=1024, KIND0=0, KIND1=KIND0)(')
    at=s.index(' input wire clk_i')
    s=s[:at]+""" input wire [2:0] route_image_valid_i,
 output reg route_update_i,route_direction_i,output reg [9:0] route_base_i,
 output reg [2:0] route_count_i,output reg [31:0] route_first_i,route_tag_i,output reg [7:0] route_stride_i,
"""+s[at:]
    s=sub(s,'   saved_reads<=0;',"""   route_update_i<=0;route_direction_i<=0;route_base_i<=0;route_count_i<=0;route_first_i<=0;route_tag_i<=0;route_stride_i<=0;
   saved_reads<=0;""")
    s=sub(s,'  end else begin\n   if(response_fire)', '  end else begin\n   route_update_i<=0;\n   if(response_fire)')
    anchor='       default:response_status<=16\'h101;'
    insert="""       4:begin
        if(state!=NORMAL || run_active_o || engine_result_valid_o || |route_image_valid_i || link_pending_o)response_status<=16'h106;
        else if(cmd_data_i[255:94]!=0 || cmd_data_i[21:19]>4 ||
                ({1'b0,cmd_data_i[18:9]}+{8'b0,cmd_data_i[21:19]})>1024)response_status<=16'h103;
        else if(cmd_data_i[21:19]!=0 && !(KIND0==0 && KIND1==0 && cmd_data_i[21:19]==2 && cmd_data_i[61:54]==3 ||
                 !cmd_data_i[8] && KIND1==3 && (KIND0==0 || KIND0==1 || KIND0==2) && cmd_data_i[61:54]==1 ||
                 !cmd_data_i[8] && KIND0==4 && KIND1==3 && cmd_data_i[61:54]==0))response_status<=16'h103;
        else begin
         route_update_i<=1;route_direction_i<=cmd_data_i[8];route_base_i<=cmd_data_i[18:9];route_count_i<=cmd_data_i[21:19];
         route_first_i<=cmd_data_i[53:22];route_stride_i<=cmd_data_i[61:54];route_tag_i<=cmd_data_i[93:62];
        end
       end
"""
    s=sub(s,anchor,insert+anchor)
    # Existing cancel/status commands use only 144 low bits. Route config also fits.
    return s

def top():
    s=(ROOT/'project/control_recovery_boot_v1/recovery_boot_top.sv').read_text()
    s=s.replace('module recovery_boot_top #(parameter integer KIND=0,parameter bit PM_USE_SRAM=1)',
                'module main64_recovery_top #(parameter integer KIND0=0,KIND1=KIND0,DRAIN_LIMIT=1024)')
    s=s.replace('recovery_engine #(.KIND(KIND),.PM_USE_SRAM(PM_USE_SRAM))',
                'main64_recovery_engine #(.KIND0(KIND0),.KIND1(KIND1))')
    s=s.replace('    recovery_supervisor supervisor(','    main64_recovery_supervisor #(.DRAIN_LIMIT(DRAIN_LIMIT),.KIND0(KIND0),.KIND1(KIND1)) supervisor(')
    anchor='    wire inner_rst_ni,halt_i,quiescent_o,fault_o,engine_result_valid_o;'
    s=sub(s,anchor,anchor+"""
    wire route_update_i,route_direction_i;wire [9:0] route_base_i;wire [2:0] route_count_i;
    wire [31:0] route_first_i,route_tag_i;wire [7:0] route_stride_i;""")
    pins='''        .route_update_i,.route_direction_i,.route_base_i,.route_count_i,.route_first_i,.route_tag_i,.route_stride_i,
'''
    s=sub(s,'    main64_recovery_engine #(.KIND0(KIND0),.KIND1(KIND1)) engine(\n','    main64_recovery_engine #(.KIND0(KIND0),.KIND1(KIND1)) engine(\n'+pins)
    s=sub(s,' supervisor(\n',' supervisor(\n'+pins+'        .route_image_valid_i(image_valid_o),\n')
    return s

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    for name,fn in [('main64_recovery_endpoint',endpoint),('main64_recovery_control',control),('main64_recovery_engine',engine),('main64_recovery_supervisor',supervisor),('main64_recovery_top',top)]:
        data=fn();path=HERE/(name+'.sv')
        if a.check:assert path.read_text()==data,name
        else:path.write_text(data,encoding='utf-8',newline='\n')
    print('PASS generated R8.4 supervised main64 glue')
if __name__=='__main__':main()

