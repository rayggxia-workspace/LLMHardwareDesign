"""Build a real private-S/E13/N relative-Exp packet-construction fixture.

Existing U-group public-port tasks and all their SRAM/ACK checks are reused.
This demonstrates an additional service recipe, not emitted LC instructions,
physical timing qualification, a DP speedup or a change to functional hardware.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    for name in ('repository', 'native_fixtures', 'output'):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    original = a.repository/'project/experiments/pu_leaf_base/tb_pu_u_group.sv'
    text = original.read_text()
    start = text.index('    initial begin\n')
    text = text[:start]+'''    integer fixture, count=0, x, expected, status;
    integer phase_clock=0;
    string fixture_path;
    initial begin
        if(!$value$plusargs("FIXTURES=%s",fixture_path)) $fatal(1,"missing packet fixtures");
        fixture=$fopen(fixture_path,"r");
        if(!fixture) $fatal(1,"cannot open packet fixtures");
        repeat(3) tick();reset=0;
        while(!$feof(fixture)) begin
            status=$fscanf(fixture,"%d %d",x,expected);
            if(status!=2) begin
                if(!$feof(fixture)) $fatal(1,"malformed packet fixture");
            end else begin
                if(x< -32768 || x>32767 || expected<0 || expected>32768)
                    $fatal(1,"invalid packet fixture");
                // Canonical scalar record: signed S32 in the low word.
                write_word(8,{96'd0,32'(x)});
                // E13 shift0 narrows four S32 slots to four S16 lanes.
                // The other three canonical S32 slots were explicitly zero.
                execute(0,64'hd,1,30'd8,1,9,answer);
                if(answer!=={112'd0,16'(x)} || done_saturated[0])
                    $fatal(1,"E13 packet format/flags incorrect");
                expect_word(9,{112'd0,16'(x)});
                execute(1,0,0,0,0,0,answer);
                execute(1,64'h21,1,30'd9,0,0,answer);
                execute(1,2,0,0,0,0,answer);
                execute(1,64'h13,1,30'd9,1,10,answer);
                if(answer!=={96'd0,32'(expected)} || done_saturated[1])
                    $fatal(1,"N Exp differs from native reference");
                expect_word(10,{96'd0,32'(expected)});
                count=count+1;
            end
        end
        $fclose(fixture);
        if(count!=11) $fatal(1,"incomplete packet fixtures");
        $display("PASS N_EXP_PACKET services=%0d clock_hz=300000000 elapsed_ps=%0d",count,$time);
        $finish;
    end
    initial begin #1000000000; $fatal(1,"N Exp packet timeout");end
    integer previous_edge_ps=-1,edge_ps;
    always @(posedge clk) begin
        edge_ps=$time;
        if(previous_edge_ps>=0 && edge_ps-previous_edge_ps!=3333 && edge_ps-previous_edge_ps!=3334)
            $fatal(1,"packet fixture clock is not rational300MHz: edge=%0d previous=%0d",edge_ps,previous_edge_ps);
        previous_edge_ps=edge_ps;
    end
endmodule
'''
    if text.count('module tb_pu_u_group;') != 1 or text.count('always #5 clk=~clk;') != 1:
        raise ValueError('unexpected original public-port fixture')
    text = text.replace('module tb_pu_u_group;', 'module tb_n_exp_packet;')
    text = text.replace('always #5 clk=~clk;', '''always begin
        if(phase_clock==2) #1666; else #1667;
        clk=~clk;phase_clock=(phase_clock+1)%3;
    end''')
    marker = '        value=done_data[128*lane+:128];\n        done_ready[lane]=1;'
    if text.count(marker) != 1:
        raise ValueError('unexpected original completion check')
    text = text.replace(marker, '''        value=done_data[128*lane+:128];
        repeat(3) begin
            tick();
            if(!done_valid[lane] || done_error[lane] || done_data[128*lane+:128]!==value)
                $fatal(1,"unstable packet service completion under backpressure");
        end
        done_ready[lane]=1;''')
    (a.output/'tb_n_exp_packet.sv').write_text('`timescale 1ps/1ps\n'+text)
    fixtures = []
    for line in a.native_fixtures.read_text().splitlines():
        mode, pack, length, expected, *values = map(int, line.split())
        if mode == 0:
            if length != 1 or len(values) != 1:
                raise ValueError('expected one scalar Exp input')
            fixtures.append((values[0], expected))
    if len(fixtures) != 11:
        raise ValueError('complete native Exp fixture set required')
    (a.output/'packet-fixtures.tsv').write_text(''.join('%d %d\n'%row for row in fixtures))
    (a.output/'generation.json').write_text(json.dumps({'scope': __doc__,
        'original_public_port_fixture_sha256': sha(original),
        'native_fixture_sha256': sha(a.native_fixtures), 'fixture_count': len(fixtures),
        'instrumented_fixture_sha256': sha(a.output/'tb_n_exp_packet.sv'),
        'packet_fixtures_sha256': sha(a.output/'packet-fixtures.tsv'),
        'hardware_changed': False, 'LC_program_generated': False,
        'service_recipe': 'canonical S32 S[8] -> E13 shift0 -> packed [x,0] S[9] -> N Begin/Stats2/Finalize/Exp1 -> S[10]'},indent=2)+'\n')


if __name__ == '__main__':
    main()
