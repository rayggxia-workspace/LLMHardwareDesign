"""Native short/long output-path counterexample for max-only model export."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess

from audit import file_sha, require
from native_control import sdc
from native_pair import run, verify, tcl_list, native_log_diagnostics


def inputs(depth):
    require(type(depth) is int and depth >= 0, "output control buffer depth")
    nodes = [f"n{i}" for i in range(depth+1)]
    netlist = "module qa_probe(input clk,d,output q);\nwire "+", ".join(nodes)+";\n"
    netlist += "DFF_X1 ff(.CK(clk),.D(d),.Q(n0));\n"
    for i in range(depth):
        netlist += f"BUF_X1 b{i}(.A(n{i}),.Z(n{i+1}));\n"
    netlist += f"NOR2_X1 merge(.A1(n0),.A2(n{depth}),.ZN(q));\nendmodule\n"
    text = '''*SPEF "IEEE 1481-1998"
*DESIGN "qa_probe"
*DATE "fixed output-path control"
*VENDOR "LLMHardwareDesign"
*PROGRAM "QA127 output-path control"
*VERSION "1"
*DESIGN_FLOW "PIN_CAP NONE"
*DIVIDER /
*DELIMITER :
*BUS_DELIMITER [ ]
*T_UNIT 1 NS
*C_UNIT 1 FF
*R_UNIT 1 OHM
*L_UNIT 1 UH
*PORTS
clk I
d I
q O
'''
    nets = [("clk", [("P", "clk", "I"), ("I", "ff:CK", "I")]),
            ("d", [("P", "d", "I"), ("I", "ff:D", "I")])]
    for i, name in enumerate(nodes):
        connections = [("I", "ff:Q" if i == 0 else f"b{i-1}:Z", "O")]
        if i == 0:
            connections.append(("I", "merge:A1", "I"))
        if i == depth:
            connections.append(("I", "merge:A2", "I"))
        else:
            connections.append(("I", f"b{i}:A", "I"))
        nets.append((name, connections))
    nets.append(("q", [("I", "merge:ZN", "O"), ("P", "q", "O")]))
    for name, connections in nets:
        text += f"*D_NET {name} {len(connections)}\n*CONN\n"
        text += "".join(f"*{kind} {node} {direction}\n" for kind, node, direction in connections)
        text += "*CAP\n"+"".join(f"{i+1} {node} 1\n" for i, (_, node, _) in enumerate(connections))
        text += "*RES\n"+"".join(f"{i} {connections[0][1]} {node} 1\n" for i, (_, node, _) in enumerate(connections[1:], 1))+"*END\n"
    return netlist, text


def scenario_sdc(driver, output_load_ff):
    require(driver in ('BUF_X1','BUF_X2') and isinstance(output_load_ff,(int,float))
            and not isinstance(output_load_ff,bool) and math.isfinite(output_load_ff) and output_load_ff >= 0,
            'output control driver/load scenario')
    original = sdc(driver)
    require(original.count('set_load 2 [get_ports q]') == 1, 'control SDC load command identity')
    return original.replace('set_load 2 [get_ports q]',f'set_load {output_load_ff:.12g} [get_ports q]')


def execute(executable, library, output, min_executable=None, min_probe_receipt=None, driver='BUF_X2', output_load_ff=2):
    executable, library, output = Path(executable).resolve(), Path(library).resolve(), Path(output).resolve()
    constraints = scenario_sdc(driver,output_load_ff)
    output.mkdir(parents=True, exist_ok=False)
    summary = {"schema": "block-v1-native-output-path-control/1", "passed": False, "cases": [],
               "executable_sha256": file_sha(executable), "library_sha256": file_sha(library),
               "control_sha256": file_sha(Path(__file__)), "qualified_hard_macro": False}
    summary['scenario'] = {'input_driver':driver,'output_load_ff':output_load_ff}
    require((min_executable is None) == (min_probe_receipt is None), "min probe tool/build receipt pair")
    if min_executable is not None:
        min_executable, min_probe_receipt = Path(min_executable).resolve(), Path(min_probe_receipt).resolve()
        proof = json.loads(min_probe_receipt.read_text())
        require(proof["schema"] == "block-v1-min-output-probe-build/1" and proof["passed"] is True
                and proof["original_inputs_unchanged"] is True and min_executable != executable,
                "min probe build proof")
        require(proof["outputs"][min_executable.name] == file_sha(min_executable)
                and proof["original_inputs"].get(str(executable)) == file_sha(executable), "min probe tool identity")
        summary.update(macro_delay_model="split-min-max", min_executable_sha256=file_sha(min_executable),
                       min_probe_receipt_sha256=file_sha(min_probe_receipt))
    (output / "output_path_control.py").write_bytes(Path(__file__).read_bytes())
    try:
        for depth in (0, 8):
            folder = output / f"depth-{depth}"
            folder.mkdir()
            netlist, spef = inputs(depth)
            for name, value in (("flat.v", netlist), ("source.spef", spef), ("same.sdc", constraints),
                                ("parent.v", "module qa_parent(input clk,d,output q); QA127_OUTPUT block(.clk(clk),.d(d),.q(q)); endmodule\n")):
                (folder / name).write_text(value)
            script = "read_liberty "+tcl_list([library])+"\nread_verilog flat.v\nlink_design qa_probe\nread_sdc same.sdc\nread_spef source.spef\nset_propagated_clock [all_clocks]\nwrite_timing_model -library_name QA127_OUTPUT_LIB -cell_name QA127_OUTPUT model.lib\n"
            script = "if {[catch {\n"+script+"} problem options]} {puts stderr $problem;puts stderr [dict get $options -errorinfo];exit 1}\nexit 0\n"
            (folder / "export.tcl").write_text(script)
            argv = [str(executable), "-no_init", "-exit", "export.tcl"]
            with (folder / "export.log").open("w") as log:
                code = subprocess.run(argv, cwd=folder, env=dict(os.environ, OMP_NUM_THREADS="1"), stdout=log, stderr=subprocess.STDOUT).returncode
            require(code == 0 and native_log_diagnostics(folder / "export.log")["native_error_count"] == 0, "native output-path model export failed")
            export_receipt = {"argv": argv, "returncode": code,
                              "inputs": {name: file_sha(folder / name) for name in ("flat.v", "source.spef", "same.sdc", "export.tcl")},
                              "outputs": {name: file_sha(folder / name) for name in ("model.lib", "export.log")},
                              "library_sha256": file_sha(library), "executable_sha256": file_sha(executable)}
            (folder / "export-receipt.json").write_text(json.dumps(export_receipt, indent=2)+"\n")
            if min_executable is not None:
                min_script = script.replace('QA127_OUTPUT_LIB', 'QA127_OUTPUT_MIN_LIB').replace('model.lib', 'model-min.lib')
                (folder / 'export-min.tcl').write_text(min_script)
                min_argv = [str(min_executable), '-no_init', '-exit', 'export-min.tcl']
                with (folder / 'export-min.log').open('w') as log:
                    min_code = subprocess.run(min_argv,cwd=folder,env=dict(os.environ,OMP_NUM_THREADS='1'),stdout=log,stderr=subprocess.STDOUT).returncode
                require(min_code == 0 and native_log_diagnostics(folder/'export-min.log')['native_error_count'] == 0, 'native min-output probe export failed')
                min_receipt = {'argv':min_argv,'returncode':min_code,
                    'inputs':{name:file_sha(folder/name) for name in ('flat.v','source.spef','same.sdc','export-min.tcl')},
                    'outputs':{name:file_sha(folder/name) for name in ('model-min.lib','export-min.log')},
                    'executable_sha256':file_sha(min_executable),'library_sha256':file_sha(library),
                    'probe_build_receipt_sha256':summary['min_probe_receipt_sha256']}
                (folder/'export-min-receipt.json').write_text(json.dumps(min_receipt,indent=2)+'\n')
            paths = {"flat_verilog": folder / "flat.v", "flat_spef": folder / "source.spef", "sdc": folder / "same.sdc",
                     "abstract_verilog": folder / "parent.v", "macro_lib": folder / "model.lib", "base_lib_0": library}
            request = {"schema": "block-v1-native-boundary-request/1", "evidence_kind": "native-control", "abstract_parent_interconnect": "ideal",
                       "flat_top": "qa_probe", "abstract_top": "qa_parent", "expected_ports": {"clk": "input", "d": "input", "q": "output"},
                       "time_tolerance_ns": .001, "slew_tolerance_ns": .001,
                       "files": {r: {"path": str(p), "sha256": file_sha(p)} for r, p in paths.items()}}
            if min_executable is not None:
                request['macro_delay_model'] = 'split-min-max'
                request['files']['macro_min_lib'] = {'path':str(folder/'model-min.lib'),'sha256':file_sha(folder/'model-min.lib')}
            request_path = folder / "request.json"
            request_path.write_text(json.dumps(request, indent=2)+"\n")
            measured = output / f"depth-{depth}-measured"
            pair = run(request_path, measured, executable, 2)
            require(pair["measurement_context_accepted"], "output control native context rejected")
            verification = verify(measured, request_path)
            observations = [json.loads((measured / v / "observed.json").read_text()) for v in ("flat", "abstract")]
            tables = [{tuple(r["key"]): r for r in o["observations"]} for o in observations]
            q_results = [{"edge": edge, "analysis": analysis, "flat_slack_ns": tables[0][("output", "q", edge, analysis)]["slack_ns"],
                          "abstract_slack_ns": tables[1][("output", "q", edge, analysis)]["slack_ns"]}
                         for edge in ("rise", "fall") for analysis in ("max", "min")]
            summary["cases"].append({"depth": depth, "context_accepted": pair["measurement_context_accepted"], "output_slacks": q_results,
                                     "binding": verification, "measurement_receipt_sha256": file_sha(measured / "receipt.json")})
        summary["passed"] = True
        return summary
    finally:
        (output / "output-path-control.json").write_text(json.dumps(summary, indent=2)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True)
    parser.add_argument("--library", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--min-executable")
    parser.add_argument("--min-probe-receipt")
    parser.add_argument("--driver", choices=['BUF_X1','BUF_X2'],default='BUF_X2')
    parser.add_argument("--output-load-ff",type=float,default=2)
    args = parser.parse_args()
    print(json.dumps(execute(args.executable, args.library, args.output, args.min_executable, args.min_probe_receipt,args.driver,args.output_load_ff), indent=2))
