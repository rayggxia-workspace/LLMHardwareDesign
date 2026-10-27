"""Actual DFF/Liberty/SPEF/export/STA controls; no routed macro qualification."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from audit import file_sha, require
from native_pair import run, tcl_list, verify, native_log_diagnostics


def probe_spef(resistance):
    header = '''*SPEF "IEEE 1481-1998"
*DESIGN "qa_probe"
*DATE "fixed control"
*VENDOR "LLMHardwareDesign"
*PROGRAM "QA127 control"
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
    for name, pin, direction, value in (("clk", "CK", "I", 1), ("d", "D", "I", resistance), ("q", "Q", "O", 1)):
        header += f'''*D_NET {name} 2
*CONN
*P {name} {direction}
*I ff:{pin} {direction}
*CAP
1 {name} 1
2 ff:{pin} 1
*RES
1 {name} ff:{pin} {value}
*END
'''
    return header


def sdc(driver):
    return f'''set_cmd_units -time ns -capacitance fF -resistance kOhm -distance um
create_clock -name core -period 10 [get_ports clk]
set_clock_uncertainty .1 [get_clocks core]
set_clock_transition .05 [get_clocks core]
set_input_delay -clock core -max 2 [get_ports d]
set_input_delay -clock core -min .2 [get_ports d]
set_output_delay -clock core -max 2 [get_ports q]
set_output_delay -clock core -min .2 [get_ports q]
set_driving_cell -lib_cell {driver} -pin Z [get_ports d]
set_load 2 [get_ports q]
'''


def control(executable, library, output, parallel=1, export_drive="original-sdc"):
    executable, library, output = Path(executable).resolve(), Path(library).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    summary = {"schema": "block-v1-native-boundary-control/1", "passed": False,
               "executable_sha256": file_sha(executable), "base_lib_sha256": file_sha(library),
               "control_script_sha256": file_sha(Path(__file__)),
               "qualified_hard_macro": False, "flat_abstract_boundary_qualified": False,
               "cases": [], "export_drive": export_drive,
               "scope": "Actual native small DFF controls; not placed/routed C8/T6K or full macro qualification"}
    try:
        (output / "native_control.py").write_bytes(Path(__file__).read_bytes())
        for name, resistance in (("low-r", 1), ("high-r", 20000)):
            folder = output / name
            folder.mkdir()
            (folder / "flat.v").write_text("module qa_probe(input clk,d,output q); DFF_X1 ff(.CK(clk),.D(d),.Q(q)); endmodule\n")
            (folder / "wrapper.v").write_text("module qa_wrapper(input clk,d,output q); QA127_MACRO macro0(.clk(clk),.d(d),.q(q)); endmodule\n")
            (folder / "source.spef").write_text(probe_spef(resistance))
            (folder / "BUF_X2.sdc").write_text(sdc("BUF_X2"))
            (folder / "BUF_X1.sdc").write_text(sdc("BUF_X1"))
            (folder / "transition-export.sdc").write_text("\n".join(
                line for line in sdc("BUF_X2").splitlines() if not line.startswith("set_driving_cell "))+"\n")
            require(export_drive in ("original-sdc", "matched-transition"), "control export drive mode")
            capture_record = None
            if export_drive == "matched-transition":
                capture = "\n".join([
                    "read_liberty " + tcl_list([library]), "read_verilog flat.v", "link_design qa_probe",
                    "read_sdc BUF_X2.sdc", "read_spef source.spef", "set_propagated_clock [all_clocks]",
                    '''sta::find_timing
set data_port [lindex [get_ports d] 0]
set stream [open transition-export.sdc a]
foreach mm {max min} {
  foreach edge {rise fall} {
    set slew [get_property $data_port slew_${mm}_${edge}]
    puts $stream "set_input_transition -$mm -$edge $slew \\[get_ports d\\]"
  }
}
close $stream
'''])
                (folder / "capture-transition.tcl").write_text("if {[catch {\n" + capture + "} problem options]} {puts stderr $problem; puts stderr [dict get $options -errorinfo]; exit 1}\nexit 0\n")
                with (folder / "capture-transition.log").open("w") as log:
                    code = subprocess.run([str(executable), "-no_init", "-exit", "capture-transition.tcl"], cwd=folder,
                                          env=dict(os.environ, OMP_NUM_THREADS="1"), stdout=log, stderr=subprocess.STDOUT).returncode
                require(code == 0, "native transition capture failed")
                capture_record = {"returncode": code,
                                  "inputs": {name: file_sha(folder / name) for name in ("capture-transition.tcl", "BUF_X2.sdc", "source.spef", "flat.v")},
                                  "outputs": {name: file_sha(folder / name) for name in ("transition-export.sdc", "capture-transition.log")}}
                require(native_log_diagnostics(folder / "capture-transition.log")["native_error_count"] == 0, "native transition capture printed errors")
            export_sdc = "transition-export.sdc" if export_drive == "matched-transition" else "BUF_X2.sdc"
            script = "\n".join([
                "read_liberty " + tcl_list([library]), "read_verilog {flat.v}", "link_design qa_probe",
                "read_sdc {"+export_sdc+"}", "read_spef {source.spef}", "set_propagated_clock [all_clocks]",
                f"write_timing_model -library_name QA127_{name.replace('-', '_')} -cell_name QA127_MACRO model.lib", "exit 0", ""])
            # Tcl failures must return a failing process, including missing API.
            (folder / "export.tcl").write_text("if {[catch {\n" + script.replace("exit 0\n", "") + "} problem options]} {puts stderr $problem; puts stderr [dict get $options -errorinfo]; exit 1}\nexit 0\n")
            argv = [str(executable), "-no_init", "-exit", "export.tcl"]
            env = dict(os.environ, OMP_NUM_THREADS="1")
            with (folder / "export.log").open("w") as stream:
                code = subprocess.run(argv, cwd=folder, env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
            require(code == 0 and (folder / "model.lib").is_file(), "native model export failed; inspect preserved export.log")
            require(native_log_diagnostics(folder / "export.log")["native_error_count"] == 0, "native model export printed errors")
            export_record = {"argv": argv, "returncode": code,
                             "executable_sha256": file_sha(executable),
                             "inputs": {str(p): file_sha(p) for p in (library, folder / "flat.v", folder / "source.spef", folder / export_sdc, folder / "export.tcl")},
                             "outputs": {n: file_sha(folder / n) for n in ("model.lib", "export.log")}}
            export_record["transition_capture"] = capture_record
            (folder / "export-receipt.json").write_text(json.dumps(export_record, indent=2)+"\n")
            for driver in ("BUF_X2", "BUF_X1"):
                files = {"base_lib_0": library, "flat_verilog": folder / "flat.v", "flat_spef": folder / "source.spef",
                         "abstract_verilog": folder / "wrapper.v", "macro_lib": folder / "model.lib", "sdc": folder / f"{driver}.sdc"}
                request = {"schema": "block-v1-native-boundary-request/1", "evidence_kind": "native-control",
                           "abstract_parent_interconnect": "ideal", "flat_top": "qa_probe", "abstract_top": "qa_wrapper",
                           "expected_ports": {"clk": "input", "d": "input", "q": "output"},
                           "time_tolerance_ns": .001, "slew_tolerance_ns": .001,
                           "files": {role: {"path": str(p), "sha256": file_sha(p)} for role, p in files.items()}}
                request_path = folder / f"{driver}-request.json"
                request_path.write_text(json.dumps(request, indent=2)+"\n")
                result = run(request_path, output / f"{name}-{driver}", executable, parallel)
                verified = verify(output / f"{name}-{driver}", request_path)
                summary["cases"].append({"resistance_ohm": resistance, "driver": driver,
                                          "result": result, "independent_receive": verified})
            # Exact native reread is a positive control, separately labeled;
            # it cannot be reported as successful abstract-model equivalence.
            request["abstract_top"] = "qa_probe"
            request["abstract_parent_interconnect"] = "explicit-spef"
            request["files"]["abstract_verilog"] = request["files"]["flat_verilog"]
            request["files"]["abstract_spef"] = request["files"]["flat_spef"]
            request_path = folder / "exact-reread-request.json"
            request_path.write_text(json.dumps(request, indent=2)+"\n")
            repeated = run(request_path, output / f"{name}-exact-reread", executable, parallel)
            require(repeated["passed"], "exact same flat native reread differs")
            verify(output / f"{name}-exact-reread", request_path)
        # The control succeeds by running honest measurements plus a stable
        # reread. Actual model mismatches remain visible and are not relaxed.
        require(file_sha(executable) == summary["executable_sha256"]
                and file_sha(library) == summary["base_lib_sha256"]
                and file_sha(Path(__file__)) == summary["control_script_sha256"], "control tool/library/code changed")
        summary["passed"] = True
        return summary
    finally:
        (output / "native-control-report.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--export-drive", choices=("original-sdc", "matched-transition"), default="original-sdc")
    args = parser.parse_args()
    result = control(args.executable, args.library, args.output, args.parallel, args.export_drive)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
