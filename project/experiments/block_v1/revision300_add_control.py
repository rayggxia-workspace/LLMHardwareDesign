"""Prove the actual RTL grouped-adder function for every pair of64-bit inputs."""
import json
import re
from pathlib import Path


def control(root,out,cpus,run):
    from io_slots import file_sha
    assert cpus==16
    rtl=root/'project/rtl/block_library_v1/block_v1_m.sv'
    text=rtl.read_text()
    match=re.search(r' function automatic \[64:0\] add_s64_grouped;.*? endfunction',text,re.S)
    assert match is not None and text.count('function automatic [64:0] add_s64_grouped;')==1
    function=match.group(0)
    module='module adder_check(input [63:0] a,b,output ok);\n'+function+'\n'
    module+='wire [64:0] result=add_s64_grouped(a,b);\n'
    module+='wire [64:0] expected=$signed({a[63],a})+$signed({b[63],b});\n'
    module+='assign ok=(result==expected);\nendmodule\n'
    (out/'adder-check.sv').write_text(module)
    script='read_verilog -sv adder-check.sv\nprep -top adder_check\nflatten\nsat -verify -prove ok 1 -show a,b\n'
    (out/'prove.ys').write_text(script)
    run(['yosys','-s',out/'prove.ys'],'prove.log')
    proof=(out/'prove.log').read_text()
    assert 'SUCCESS!' in proof and 'SAT proof finished - no model found' in proof
    (out/'revision300-m-add-control.json').write_text(json.dumps(dict(
        passed=True,rtl_sha256=file_sha(rtl),function_sha256=__import__('hashlib').sha256(function.encode()).hexdigest(),
        harness_sha256=file_sha(out/'adder-check.sv'),proof_log_sha256=file_sha(out/'prove.log'),
        symbolic_input_bits=128,result_bits=65,all_input_assignments=True,qualified_hard_macro=False,
        scope='Combinational SAT proof of the actual extracted RTL function against signed65-bit addition; no assumptions, no restricted magnitude, no latency or physical qualification.'),indent=2)+'\n')
