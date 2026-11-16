"""Generate an ONNX native graph, compile binary images, run real MC/two U LCs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil

from control_backend import capabilities,compile_control,images
from frontend import import_onnx
from leaf_catalog import read_profiles

REFERENCE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-193-local-control/acceptance-02')


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def example(path):
    import onnx
    from onnx import helper,TensorProto
    values={n:helper.make_tensor_value_info(n,TensorProto.INT16,[8]) for n in ('x','y','z','sum','out')}
    graph=helper.make_graph([
        helper.make_node('Add',['x','y'],['sum'],name='sum',domain='llmhardware.native'),
        helper.make_node('Mul',['sum','z'],['out'],name='product',domain='llmhardware.native')],
        'native-control-gate',[values[n] for n in ('x','y','z')],[values['out']],value_info=[values['sum']])
    model=helper.make_model(graph,opset_imports=[helper.make_opsetid('',18),helper.make_opsetid('llmhardware.native',1)])
    helper.set_model_props(model,{'llmhardware.native_formats':json.dumps(
        {n:{'bits':16,'exponent':0,'lanes':8} for n in values})})
    onnx.save(model,path)


def stage_fixture(root):
    source=root/'control-source';directory=source/'project/experiments/pu_leaf_base'
    env={**os.environ,'PU_INSTRUCTION_BITS':'64'}
    subprocess.run([sys.executable,str(directory/'control_replay.py'),str(source),str(root/'fixture'),'U'],
                   check=True,env=env)
    return root/'fixture'


def install_current_mother(root,fixture):
    source=root/'control-source/project/rtl/mother_control_v1'
    lock=json.loads((source/'upstream-lock.json').read_text())
    for name,expected in lock['files_sha256'].items():
        if hashlib.sha256((source/Path(name).name).read_bytes()).hexdigest()!=expected:
            raise ValueError('current mother differs from its upstream source lock')
    ctrl=fixture/'staged/project/control_rtl_min_v0_1'
    for name in ('mc_min_controller.sv','mc_ports.svh','instruction_fetch.svh'):
        shutil.copyfile(source/name,ctrl/name)
    for name in ('control_pm.sv','mother_control_64.sv'):
        if (fixture/'design'/name).exists():raise ValueError('mother module name collision')
        shutil.copyfile(source/name,fixture/'design'/name)
    file=ctrl/'tb_network_mc_wires.svh';text=file.read_text()
    start=text.index('mc_min_controller #')
    text=text[:start]+"mother_control_64 #(.NATIVE_ABI_ID(32'h01930001)) dut(.*);\n"
    file.write_text(text)
    file=fixture/'design/tb_native_pair.sv';text=file.read_text()
    start=text.index('    network_pm #(.BYTES(4736)) pm(');end=text.index(';',start)+1
    signals=('pm_req_valid_o','pm_req_write_o','pm_req_address_o','pm_req_data_o','pm_req_ready_i',
             'pm_rsp_valid_i','pm_rsp_data_i','pm_rsp_error_i','pm_rsp_ready_o')
    aliases='\n'.join('    assign '+n+'=dut.'+n+';' for n in signals)
    file.write_text(text[:start]+aliases+text[end:])
    return {'top':'mother_control_64','upstream_lock':lock,
            'pm':'actual 16 KiB program SRAM; no network_pm stand-in for mother',
            'wrapper_sha256':hashlib.sha256((source/'mother_control_64.sv').read_bytes()).hexdigest()}


MONITOR=r'''
    reg [1:0] pending_write=0;
    reg [127:0] captured[2];
    reg [9:0] captured_addr[2];
    integer commits=0, pm_requests=0;
    reg job_started=0;
    reg [1:0] local_started=0;
    for(genvar s=0;s<2;s=s+1) begin: generated_monitor
        localparam integer p=1-s;
        wire held_valid=local_block[s].endpoint.programmable_u.implementation.tx_valid;
        wire held_take=local_block[s].endpoint.programmable_u.implementation.tx_take;
        wire [127:0] held_data=local_block[s].endpoint.programmable_u.implementation.tx_data;
        reg was_held;
        reg [127:0] last_data;
        always @(posedge clk_i) begin
            if(!rst_ni) begin was_held<=0;last_data<=0;end
            else begin
                if(was_held && (!held_valid || held_data!==last_data))
                    $fatal(1,"generated source changed before ACK block=%0d",s);
                if(held_take && !(link_ack[p] && accept_ack && link_ack_ready[s]))
                    $fatal(1,"generated source released without remote write ACK");
                if(held_valid && !held_take) $display("HOLD block=%0d cycle=%0d",s,cycle);
                if(held_take) $display("RELEASE block=%0d cycle=%0d",s,cycle);
                was_held<=held_valid && !held_take;last_data<=held_data;
            end
        end
    end
    always @(posedge clk_i) begin
        if(!rst_ni) begin pending_write<=0;commits<=0;pm_requests<=0;job_started<=0;local_started<=0;end
        else begin
            if(start_valid_i && start_ready_o) begin job_started<=1;$display("START cycle=%0d",cycle);end
            if(task_valid_o && task_ready_i) local_started[task_target_o[0]]<=1;
            if(job_started && pm_req_valid_o && pm_req_ready_i && !pm_req_write_o) begin
                pm_requests<=pm_requests+1;$display("FETCH kind=MC addr=%0d cycle=%0d",pm_req_address_o,cycle);
            end
            for(integer d=0;d<2;d=d+1) begin
                if(link_valid[1-d] && link_ready[d] && accept_request) begin
                    if(pending_write[d]) $fatal(1,"overlapping generated store");
                    pending_write[d]<=1;captured[d]<=link_data[1-d];captured_addr[d]<=link_addr[1-d];
                    $display("WRITE src=%0d dst=%0d addr=%0d data=%032h cycle=%0d",1-d,d,link_addr[1-d],link_data[1-d],cycle);
                end
                if(link_ack[d] && link_ack_ready[1-d] && accept_ack) begin
                    if(!pending_write[d]) $fatal(1,"ACK without destination write");
                    pending_write[d]<=0;commits<=commits+1;
                    $display("COMMIT src=%0d dst=%0d addr=%0d data=%032h cycle=%0d",1-d,d,captured_addr[d],captured[d],cycle);
                end
            end
        end
    end
    for(genvar l=0;l<2;l=l+1) begin: fetch_monitor
        always @(posedge clk_i) if(rst_ni && local_started[l] &&
            local_block[l].endpoint.pm_req_valid_o && local_block[l].endpoint.pm_req_ready_i &&
            !local_block[l].endpoint.pm_req_write_o)
            $display("FETCH kind=LC block=%0d addr=%0d cycle=%0d",l,local_block[l].endpoint.pm_req_address_o,cycle);
    end
'''


def modify_bench(fixture,compiled,seeds):
    design=fixture/'design';file=design/'tb_native_pair.sv';text=file.read_text()
    anchor='.KIND(i==0 ? (SINGLE_KIND<0 ? 2 : SINGLE_KIND) : 0)'
    if text.count(anchor)!=1:raise ValueError('fixture local-kind anchor changed')
    text=text.replace(anchor,'.KIND(0)')
    text=text.replace('task automatic configure_and_start;','task automatic configure_and_start;\n        $display("EPOCH_BEGIN cycle=%0d",cycle);')
    begin=text.index('        case (SINGLE_KIND)\n',text.index('task automatic configure_and_start'))
    end=text.index('        endcase',begin)+len('        endcase')
    lines=[]
    for name,row in compiled['initial'].items():
        word=sum((x&65535)<<(16*i) for i,x in enumerate(seeds[name]));block=compiled['hardware']['control_groups'][row['group']]['block_id']
        lines.append(f"        seed({block},10'd{row['address']},128'h{word:032x});")
    text=text[:begin]+'\n'.join(lines)+text[end:]
    text=text.replace('transfers!=(SINGLE_KIND<0 ? 2 : 0)',f"transfers!={len(compiled['moves'])}")
    confirmed=16*(len(compiled['model']['tasks'])+len(compiled['moves']))
    text=text.replace('(fault!=0 ? 48 : 80)',str(confirmed))
    begin=text.index('        case (SINGLE_KIND)\n',text.index('while(!result_valid_o)'))
    end=text.index('        endcase',begin)+len('        endcase')
    text=text[:begin]+f'''        if(commits!={len(compiled['moves'])} || |pending_write || pm_requests==0)
            $fatal(1,"generated program did not retire real writes/fetches");
        $display("GENERATED_CONTROL_PASS cycles=%0d commits=%0d confirmed_bytes=%0d pm_requests=%0d",cycle,commits,result_confirmed_write_bytes_o,pm_requests);
'''+text[end:]
    text=text.replace('endmodule',MONITOR+'\nendmodule')
    # PM is the unchanged accepted bus model; exercise fetch backpressure too.
    text=text.replace('.stall_i(32\'d0)',".stall_i(32'(stall))")
    file.write_text(text)
    local=design/'tb_native_local.sv';text=local.read_text()
    text=text.replace(".stall_i(32'd0)",'.stall_i(generated_pm_stall)')
    text=text.replace('endmodule',r'''
    integer generated_pm_stall=0;
    initial void'($value$plusargs("STALL=%d",generated_pm_stall));
endmodule''')
    local.write_text(text)


def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('qualification',type=Path)
    p.add_argument('--current-mother',action='store_true');a=p.parse_args()
    root=a.root;out=root/'generated';out.mkdir()
    fixture=stage_fixture(root);cap=capabilities(root/'control-source',REFERENCE)
    if a.current_mother:cap['mother_target']=install_current_mother(root,fixture)
    else:cap['mother_target']={'top':'#214 compatibility mc_min_controller','pm':'accepted network_pm bus model'}
    example(out/'model.onnx');model=import_onnx(out/'model.onnx')
    seeds={'x':[1,-2,3,-4,100,-100,200,-200],'y':[2,3,-4,5,100,-100,200,-200],
           'z':[4,-3,2,-5,2,2,-2,-2]}
    h={'topology_id':0x01930010,'abi_id':0x01930001,'sites':{},'nets':{},'resources':{},
       'control_groups':{},'initial_placement':{'x':'U0','y':'U0','z':'U1'},
       'placement_constraints':{'sum':'U0','product':'U1'},'output_placement':{'out':'U0'},'verification_echo':True}
    for i,g in enumerate(('U0','U1')):
        h['sites'][g+'.S']={'words':cap['local_words']}
        h['control_groups'][g]={'block_id':i,'site':g+'.S','s_io_ticks':3}
        h['resources'].update({g+'.E':1,g+'.LC':1,g+'.S.IO':1})
        for d in ('read','write'):h['nets'][g+'.E.'+d]={'cost':1,'fixed':True}
    for net in ('U0->U1','U1->U0'):h['nets'][net]={'cost':1,'fixed':False}
    profile=read_profiles([(a.qualification/f'native-{n}.log').read_text() for n in range(3)])
    compiled=compile_control(model,h,cap,profile)
    manifest={'custom_links':compiled['connections'],'preconnected_demands':compiled['preconnected_demands'],
              'control_links':compiled['control_links'],'all_plan_demands':compiled['plan']['nets']}
    for name,value in [('compiled',compiled),('capabilities',cap),('input-data',seeds),('connections',manifest)]:write(out/(name+'.json'),value)
    assembly=fixture/'staged/project/control_p_compute_v0_1';sys.path.insert(0,str(assembly))
    sys.path.insert(0,str(root/'control-source/project/experiments/pu_leaf_base'))
    from run_a2 import assemble,mem
    from compact64 import compact_image
    for name,image in images(compiled,assemble,compact_image).items():
        (out/(name+'.bin')).write_bytes(image);mem(out/(name+'.mem'),image)
    modify_bench(fixture,compiled,seeds)
    consumed={str(f.relative_to(fixture)):hashlib.sha256(f.read_bytes()).hexdigest()
              for f in sorted(fixture.rglob('*')) if f.is_file() and f.suffix in ('.sv','.svh','.vlt','.py')}
    write(out/'rtl-source-sha256.json',consumed)
    runner=(fixture/'design/run.sh').read_text();runner=runner[:runner.index('run_case() {')]
    runner+='''
for scenario in normal stalled reset; do
 stall=0; reset=0
 if [[ $scenario != normal ]]; then stall=1;fi
 if [[ $scenario == reset ]]; then reset=1;fi
 for initial in 1:143 2:143 2:144; do
  name="$scenario-${initial/:/-}"
  "${runtime[@]}" ./obj/Vtb_native_pair \\
   "+MOTHER=../../generated/mother.mem" "+MWORDS=MOTHER_WORDS" \\
   "+LOCAL0=../../generated/local0.mem" "+WORDS0=LOCAL0_WORDS" \\
   "+LOCAL1=../../generated/local1.mem" "+WORDS1=LOCAL1_WORDS" \\
   "+STALL=$stall" "+FAULT=0" "+RESET_TRIAL=$reset" \\
   "+verilator+rand+reset+${initial%:*}" "+verilator+seed+${initial#*:}" > "$name.log" 2>&1
  grep -q GENERATED_CONTROL_PASS "$name.log"
 done
done
'''
    # Results live at ROOT/fixture/results, so generated images are two levels up.
    for name in ('mother','local0','local1'):
        runner=runner.replace(name.upper()+'_WORDS',str((out/(name+'.bin')).stat().st_size//16))
    (fixture/'design/generated-run.sh').write_text(runner)
    subprocess.run(['bash',str(fixture/'design/generated-run.sh'),str(fixture),str(fixture/'results'),'-1'],check=True)
    from control_verify import verify_replay
    report=verify_replay(compiled,seeds,fixture/'results')
    report['mother_target']=cap['mother_target']
    report['inputs']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [out/'model.onnx',root/'control-source/index.json']}
    write(out/'report.json',report);print(json.dumps(report))


if __name__=='__main__':main()
