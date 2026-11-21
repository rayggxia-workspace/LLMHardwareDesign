"""Generate the corrected Exp recipe as real accepted compact MC/LC images.

Stage only into a fresh task directory. No accepted DUT is edited. The old
U64 public configuration/PM/handshake fixture drives two U targets: the first
executes E13/N and sends the packet and answer; the second reserves/stores
both. External PM remains the qualified behavioral fixture, not a physical PM.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


BUILD='''def build(assemble, fault=False, kind=-1):
    if fault or kind!=-1: raise ValueError('Exp fixture requires two normal U targets')
    ops=[
        [command(0,13,(8,),9),dict(native_op=SEND,native0=9 | 41<<10),
         command(1,0),command(1,0x21,(9,)),command(1,2),command(1,0x13,(9,),10),
         dict(native_op=SEND,native0=10 | 43<<10)],
        [dict(native_op=RESERVE,native0=41),dict(native_op=RECEIVE),
         dict(native_op=RESERVE,native0=43),dict(native_op=RECEIVE)]]
    mother=assemble('mother',[dict(op='G_CALL',a=0,b=2,c=0),dict(op='G_CALL',a=1,b=3,c=0),
        dict(op='G_WAIT',x=12),dict(op='G_END')],{},19300,0,ABI,TOPOLOGY)
    local=[]
    for block,rows in enumerate(ops):
        program=[]
        for i,row in enumerate(rows):
            program += [dict(op='L_EXEC',a=0,b=0,c=i),dict(op='L_WAIT',x=1)]
            row.update(resource=0,service=0,native_abi_id=ABI)
        program += [dict(op='L_END')]
        task=dict(block_type=0,entry_pc=0,max_steps=len(program),required_resources=1,
            program_image_id=19301+block,topology_id=TOPOLOGY,native_abi_id=ABI)
        local.append(assemble('local',program,dict(task=[task],execution=rows),
            19301+block,1,ABI,TOPOLOGY))
    return (mother,*local)


'''


MONITOR='''
    integer exp_input,exp_expected,exp_sent=0,clock_phase=0,edge_ps,previous_ps=-1;
    time runtime_start_ps;
    always @(posedge clk_i) begin
        edge_ps=$time;
        if(previous_ps>=0 && edge_ps-previous_ps!=3333 && edge_ps-previous_ps!=3334)
            $fatal(1,"Exp LC clock is not rational300MHz");
        previous_ps=edge_ps;
        if(rst_ni && link_valid[0] && link_ready[1] && accept_request) begin
            if(exp_sent==0 && (link_addr[0]!=41 || link_data[0]!=={112'd0,16'(exp_input)}))
                $fatal(1,"LC E13 packet differs from full[x,0] word");
            if(exp_sent==1 && (link_addr[0]!=43 || link_data[0]!=={96'd0,32'(exp_expected)}))
                $fatal(1,"LC N Exp answer differs from independent native oracle");
            if(exp_sent>=2) $fatal(1,"unexpected additional LC SEND");
            exp_sent<=exp_sent+1;
        end
    end
'''


def replace_once(text,old,new):
    if text.count(old)!=1:
        raise ValueError('accepted fixture anchor changed: '+old[:80])
    return text.replace(old,new)


def main():
    p=argparse.ArgumentParser()
    for name in ('accepted_source','output'):
        p.add_argument(name,type=Path)
    a=p.parse_args();r=json.loads((a.accepted_source/'source-receipt.json').read_text())
    if r['archive_sha256']!='dae3b8274296970865dfd13bb4d72014f6c8590ea3cd94bb15720fa6b36b22f7':
        raise ValueError('wrong accepted U64 source')
    for name,row in r['selected_files'].items():
        if sha(a.accepted_source/name)!=row['sha256']:
            raise ValueError('accepted source changed: '+name)
    original=a.accepted_source/'gate/normal'
    a.output.mkdir(exist_ok=False);shutil.copytree(original,a.output/'bundle')
    design=a.output/'bundle/design'
    text=(design/'images.py').read_text()
    start=text.index('def build(');end=text.index('def main():',start)
    (design/'images.py').write_text(text[:start]+BUILD+text[end:])
    text=(design/'tb_native_pair.sv').read_text()
    text=replace_once(text,'    always #5 clk_i=~clk_i;', '''    always begin
        if(clock_phase==2) #1666; else #1667;
        clk_i=~clk_i;clock_phase=(clock_phase+1)%3;
    end''')
    text=replace_once(text,'i==0 ? (SINGLE_KIND<0 ? 2 : SINGLE_KIND) : 0','0')
    start=text.index('        case (SINGLE_KIND)',text.index('task automatic configure_and_start'))
    end=text.index('        endcase',start)+len('        endcase')
    text=text[:start]+"        seed(0,8,{96'd0,32'(exp_input)});"+text[end:]
    text=replace_once(text,'        start_job_i=7;', '        runtime_start_ps=$time;\n        start_job_i=7;')
    text=replace_once(text,'        configure_and_start();\n        while(!result_valid_o)', '''        if(!$value$plusargs("EXP_INPUT=%d",exp_input) || !$value$plusargs("EXP_EXPECTED=%d",exp_expected))
            $fatal(1,"missing independent Exp fixture");
        if(exp_input< -32768 || exp_input>32767 || exp_expected<0 || exp_expected>32768 || fault!=0 || reset_trial!=0)
            $fatal(1,"unsupported Exp LC fixture");
        configure_and_start();
        while(!result_valid_o)''')
    text=replace_once(text,'(fault!=0 ? 48 : 80)','64')
    start=text.index('        case (SINGLE_KIND)',text.index('while(!result_valid_o)'))
    end=text.index('        endcase',start)+len('        endcase')
    text=text[:start]+'''        if(exp_sent!=2 || result_confirmed_read_bytes_o!=80)
            $fatal(1,"incomplete LC Exp services/traffic");
        $display("PASS N_EXP_LC x=%0d expected=%0d elapsed_ps=%0d",exp_input,exp_expected,$time-runtime_start_ps);
'''+text[end:]
    text=replace_once(text,'    initial begin #1000000;', '    initial begin #1000000000;')
    text=replace_once(text,'endmodule\n',MONITOR+'endmodule\n')
    (design/'tb_native_pair.sv').write_text('`timescale 1ps/1ps\n'+text)
    (a.output/'generation.json').write_text(json.dumps({'scope':__doc__,
        'accepted_source_receipt_sha256':sha(a.accepted_source/'source-receipt.json'),
        'accepted_U64_archive_sha256':r['archive_sha256'],'hardware_changed':False,
        'changed_test_files':['design/images.py','design/tb_native_pair.sv'],
        'instrumented_testbench_sha256':sha(design/'tb_native_pair.sv'),
        'image_generator_sha256':sha(design/'images.py'),
        'LC_instructions':'L_EXEC / L_WAIT per native service, then L_END; compactv2, unchanged assembler',
        'PM_scope':'existing behavioral network_pm; no physical program-memory qualification'},indent=2)+'\n')


if __name__=='__main__':
    main()
