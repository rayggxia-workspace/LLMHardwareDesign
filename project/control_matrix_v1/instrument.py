"""Generate probe-equipped benches without editing the qualified RTL or assertions."""
from pathlib import Path
import argparse
P=Path(__file__).resolve().parents[1]

def probe(name,root,recovery):
 c=root+'.control'
 pair=lambda pin:'{'+c+'.local1.'+pin+','+c+'.local0.'+pin+'}'
 return f'''
 matrix_probe {name}(.clk_i,.rst_ni,.cmd_valid_i,.cmd_ready_o,.reply_valid_o,.reply_ready_i,
 .cmd_op_i,.reply_status_o,.reply_data_o,.run_active_o,.link_pending_o,.image_valid_o,.poison_o,.commit_count_o,.ack_count_o,
 .life({root}.life_o),.seq({c}.seq_o),.recovery_enabled(1'b{int(recovery)}),
 .recovery_phase({root.rsplit('.engine',1)[0]+'.supervisor.state' if recovery else "3'd0"}),
 .native_valid({pair('svc_req_valid_o')}),.native_ready({pair('svc_req_ready_i')}),
 .response_valid({pair('svc_rsp_valid_i')}),.response_ready({pair('svc_rsp_ready_o')}),
 .response_sat({pair('svc_rsp_saturated_i')}),.response_status({pair('svc_rsp_status_i')}),
 .retire({{{c}.local1.control.trace_retire_o,{c}.local0.control.trace_retire_o,{c}.mother.trace_retire_o}}),
 .opcode({{{c}.local1.control.trace_opcode_o,{c}.local0.control.trace_opcode_o,{c}.mother.trace_opcode_o}}));
'''

def faults(root):
 return f'''
 always @(negedge clk_i)begin
  if(!rst_ni)begin
   release {root}.pm_rsp_error_i;release {root}.pm_rsp_data_i;
   release {root}.pm_rsp_valid_i[0];release {root}.pm_rsp_valid_i[1];release {root}.pm_rsp_valid_i[2];injection_done=0;
  end else if(fault_arm && !injection_done)begin
   if(fault_mode==1)begin
    case(fault_index)0:force {root}.pm_rsp_valid_i[0]=0;1:force {root}.pm_rsp_valid_i[1]=0;2:force {root}.pm_rsp_valid_i[2]=0;endcase
    injection_done=1;$display("COV_INJECT mode=%0d target=%0d",fault_mode,fault_index);
   end else if({root}.pm_rsp_valid_i[fault_index] && {root}.pm_rsp_ready_o[fault_index] &&
               (fault_mode!=0 || fault_index==0 || {root}.control.mother.block_accepted==2'b11))begin
    if(fault_mode==0)begin
     case(fault_index)0:force {root}.pm_rsp_error_i=3'b001;1:force {root}.pm_rsp_error_i=3'b010;2:force {root}.pm_rsp_error_i=3'b100;endcase
    end else begin
     case(fault_index)0:force {root}.pm_rsp_data_i[0+:128]=128'd1;1:force {root}.pm_rsp_data_i[128+:128]=128'd1;2:force {root}.pm_rsp_data_i[256+:128]=128'd1;endcase
    end
    injection_done=1;$display("COV_INJECT mode=%0d target=%0d",fault_mode,fault_index);
   end
  end else if(injection_done && fault_mode!=1)begin release {root}.pm_rsp_error_i;release {root}.pm_rsp_data_i;end
 end
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 for folder,stem,root,recovery in [('control_five_boot_v1','tb_five_boot','dut',False),('control_recovery_boot_v1','tb_recovery_boot','dut.engine',True)]:
  s=(P/folder/(stem+'.sv')).read_text();s=s.rsplit('endmodule',1)[0]+probe('coverage_probe',root,recovery)+'\nendmodule\n';(a.out/(stem+'.sv')).write_text(s)
 base=(P/'control_task_compiler_v1/tb_compiled_native.sv').read_text().replace('tb_compiled_native','tb_matrix')
 base=base.replace('integer variant=0,stall=0,position,polls,accepted=0;','integer variant=0,stall=0,position,polls,accepted=0;\n    reg fault_arm=0,injection_done=0;integer fault_index=0,fault_mode=0;')
 old='''            if(cmd[1319:1316]>1)$fatal(1,"unknown host replay mode");
            do begin'''
 new='''            if(cmd[1319:1316]==3)begin
                if(fault_arm && !injection_done)$fatal(1,"PM injection not exercised");
                fault_arm=0;rst_ni=0;cmd_valid_i=0;reply_ready_i=0;repeat(6)tick();rst_ni=1;
                while(!reset_ready_o)tick();repeat(4)tick();continue;
            end
            if(cmd[1319:1316]==4)begin
                fault_index=int'(cmd[1311:1310]);fault_mode=int'(cmd[1047:1040]);fault_arm=1;continue;
            end
            if(cmd[1319:1316]==5)begin
                while(!poison_o[fault_index])begin tick();polls++;if(polls>12000)$fatal(1,"missing PM poison");end
                if(deployment_ready_o)$fatal(1,"poisoned cohort still deployment-ready");continue;
            end
            if(cmd[1319:1316]>2)$fatal(1,"unknown host replay mode");
            do begin'''
 assert old in base;base=base.replace(old,new)
 base=base.replace('if((answer&cmd[1023:512])!==cmd[511:0])$fatal', 'if(cmd[1319:1316]==2 && answer[111:96]==0)$fatal(1,"expected failed RESULT");\n            if((answer&cmd[1023:512])!==cmd[511:0])$fatal')
 base=base.replace('string root;','string root;\n    '+ 'if(LAYOUT==0)begin: coverage_h\n'+probe('p','homogeneous.dut',False)+faults('homogeneous.dut')+'\nend else begin: coverage_d\n'+probe('p','directed.dut.engine',True)+faults('directed.dut.engine')+'\nend\n')
 base=base.replace('$display("PASS compiled-native','$display("PASS matrix-native')
 (a.out/'tb_matrix.sv').write_text(base)
 print('PASS generated instrumentation and retained original test assertions')
if __name__=='__main__':main()
