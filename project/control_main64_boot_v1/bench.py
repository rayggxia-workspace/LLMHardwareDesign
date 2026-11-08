"""Derive the new top's host-only deployment bench, retaining prior checks."""
from contract import ROOT,HERE


def build():
    text=(ROOT/'project/control_five_boot_v1/tb_five_boot.sv').read_text()
    text=text.replace('module tb_five_boot;', 'module tb_main64_boot;')
    text=text.replace('parameter integer KIND=0;parameter bit PM_USE_SRAM=1;', 'parameter integer KIND0=0,KIND1=KIND0;localparam KIND=KIND0;localparam PM_USE_SRAM=1;')
    text=text.replace('five_boot_top #(.KIND(KIND),.PM_USE_SRAM(PM_USE_SRAM))', 'main64_boot_top #(.KIND0(KIND0),.KIND1(KIND1))')
    text=text.replace('counts[0:4]', 'counts[0:5]')
    text=text.replace('reg [31:0] epoch=1;', '''reg [31:0] epoch=1;
    reg [127:0] flows0[0:3],flows1[0:3];
    reg [31:0] flow_counts[0:1];
    integer observed0=0,observed1=0;
    reg [31:0] base_commits,base_acks;
    always @(posedge clk_i)begin
        if(!rst_ni)begin observed0<=0;observed1<=0;base_commits<=0;base_acks<=0;end
        else if(dut.start_valid_i && dut.start_ready_o)begin
            observed0<=0;observed1<=0;base_commits<=commit_count_o;base_acks<=ack_count_o;
        end else begin
            if(dut.control.forward_valid[0] && dut.control.forward_ready[0])begin
                if(observed0>=flow_counts[0] || dut.control.forward_data[0+:128]!==flows0[observed0])$fatal(1,"main64 outgoing0 mismatch index=%0d",observed0);
                observed0<=observed0+1;
            end
            if(dut.control.forward_valid[1] && dut.control.forward_ready[1])begin
                if(observed1>=flow_counts[1] || dut.control.forward_data[128+:128]!==flows1[observed1])$fatal(1,"main64 outgoing1 mismatch index=%0d",observed1);
                observed1<=observed1+1;
            end
        end
    end''')
    text=text.replace('$readmemh({folder,"/checks.mem"},checks,0,counts[4]-1);', '''$readmemh({folder,"/checks.mem"},checks,0,counts[4]-1);
        $readmemh({folder,"/flow-counts.mem"},flow_counts);
        if(flow_counts[0])$readmemh({folder,"/flows0.mem"},flows0,0,flow_counts[0]-1);
        if(flow_counts[1])$readmemh({folder,"/flows1.mem"},flows1,0,flow_counts[1]-1);''')
    # Wrong-version, CRC, generation and reply-hold checks remain unchanged.
    text=text.replace('dut.pm_rsp_data_i','dut.control.pm_rsp_data_i')
    text=text.replace('            request(1,2\'(c),0,manifest(c,epoch),0);', '            v=manifest(c,epoch);v[111:80]^=1;request(1,2\'(c),0,v,3);\n            request(1,2\'(c),0,manifest(c,epoch),0);')
    text=text.replace('        request(7,3,0,epoch,0);\n        if(image_valid_o!=7)$fatal(1,"five deployment");', '        // Deployment and its image_valid assertion follow host initialization.')
    begin=text.index('        if(mode==4)begin\n            v=manifest(1,epoch+1);')
    end=text.index('\n        end',begin)+len('\n        end')
    text=text[:begin]+text[end:]
    # Initial seeding precedes DEPLOY because main CF rejects unreserved writes
    # while deployed. Output tests remain on actual S/T interfaces.
    text=text.replace('if(mode==1)begin load_case(1,0);seed_data();run_job(8,2,0);end', 'if(mode==1)begin run_job(8,2,0);end')
    text=text.replace('if(mode==1)begin run_job(8,2,0);end', '''if(mode==1)begin
            // J joins consume their fragment lease. Refill only J fragments;
            // ordinary CF/P/U seeding remains forbidden while deployed.
            for(integer n=0;n<counts[3];n++)if(seeds[n][275:272]==14)
                request(14,seeds[n][271:270],seeds[n][269:256],seeds[n][255:0],0);
            run_job(8,2,0);
        end''')
    text=text.replace('seed_data();run_job(', 'seed_data();request(7,3,0,epoch,0);if(image_valid_o!=7)$fatal(1,"main64 deploy");run_job(')
    text=text.replace('$readmemh({folder,"/checks.mem"},checks,0,counts[4]-1);','if(counts[4])$readmemh({folder,"/checks.mem"},checks,0,counts[4]-1);')
    begin=text.index('        case(KIND)0:write_bytes=');end=text.index('\n',begin)
    text=text[:begin]+'        write_bytes=counts[5];'+text[end:]
    # J checks are selected by the actual target type, including J/P.
    text=text.replace('if(KIND==4 && (answer[202:171]', 'if((checks[n][1039:1038]==1 ? KIND0==4 : KIND1==4) && (answer[202:171]')
    text=text.replace('request(13,1,0,0,16\'h105);request(13,2,0,0,16\'h105);', "request(13,1,0,0,16'h105);if(KIND1==4)request(13,2,0,0,16'h105);")
    text=text.replace('        if(|poison_o)', '''        if(!fault)begin
            if(observed0!=flow_counts[0] || observed1!=flow_counts[1])$fatal(1,"main64 missing transfer");
            if(commit_count_o-base_commits!=flow_counts[0]+flow_counts[1] || ack_count_o-base_acks!=flow_counts[0]+flow_counts[1])$fatal(1,"main64 ACK/commit count");
        end
        if(|poison_o)''')
    text=text.replace('PASS five-boot kind=%0d backend=%0d mode=%0d negatives=%0d', 'PASS main64-boot kind=%0d backend=%0d mode=%0d negatives=%0d')
    # The new fault image injects native_op=0xffff. main's unmodified adapters
    # reject that opcode with BAD_DESCRIPTOR=5; the old fault image used 0x101
    # and was intercepted as unsupported=4 by the old research endpoint.
    text=text.replace('fault ? 4 : 0','fault ? 5 : 0')
    text=text.replace('if(polls>4000)$fatal(1,"five job stalled");', 'if(polls>4000)$fatal(1,"main64 job stalled life=%h seq=%h mc_pc=%0d task=%b/%b lc=%b/%b",dut.life_o,dut.seq_o,dut.control.mc_trace_pc_o,dut.control.mc_task_valid_o,dut.control.mc_task_ready_i,dut.control.local_task_valid,dut.control.local_task_ready);')
    # The main U wrapper deliberately has no ordinary host-read port.
    text=text.replace('        seed_data();request(7', '        if(KIND0==0)request(11,1,0,0,4);\n        seed_data();request(7',1)
    return text


if __name__=='__main__':
    (HERE/'tb_main64_boot.sv').write_text(build(),encoding='utf-8',newline='\n')
    print('PASS generated R8.2 host-only deployment bench')
