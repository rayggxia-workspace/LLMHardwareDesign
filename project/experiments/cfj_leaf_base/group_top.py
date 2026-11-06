"""Build synthesizable C/F/J groups using the verified native local controller."""
import hashlib
import re
import tarfile

BUNDLE_SHA = "3387aa6f05f5fdd658e0ce326fce70fd694200c1882a4a5941c4fa6ddafea281"
CTRL = "staged/project/control_rtl_min_v0_1/"
SVC = re.compile(r"^(?:svc|close)_")
RETURN_REGS = ("token", "sequence", "job", "epoch", "task_sequence")


def ports(text):
    result = {}
    for item in text.strip().split(","):
        match = re.fullmatch(
            r"\s*(input|output)\s+(?:wire|reg)\s*(\[[^\]]+\])?\s+(\w+)\s*", item)
        if match is None:
            raise ValueError(f"unrecognized LC port declaration {item}")
        direction, width, name = match.groups()
        result[name] = (direction, width or "")
    return result


def instance(module, name, connections, parameters=""):
    overrides = f" #({parameters})" if parameters else ""
    pins = ",\n".join(f"        .{pin}({value})" for pin, value in connections.items())
    return f"    {module}{overrides} {name}(\n{pins}\n    );\n"


def stage(root, out, kind, service, service_files):
    archive = root / "issue-193-local-control/acceptance-02/bundle.tar.gz"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != BUNDLE_SHA:
        raise ValueError("qualified local controller bundle digest differs")
    with tarfile.open(archive) as tar:
        def member(name):
            with tar.extractfile(name) as file:
                return file.read().decode("utf-8")
        lc = member(CTRL + "lc_min_controller.sv")
        declaration = ports(member(CTRL + "ports.svh"))
        lc = re.sub(r'`include "([^"]+)"', lambda match: member(CTRL + match[1]), lc)
        (out / "lc_min_controller.sv").write_text(lc)
        filenames = ["lc_min_controller.sv"]
        for file in (("pj_native_service.sv",) if kind == "j" else
                     ("ucf_native_service.sv", "stored_link.sv")):
            body = member("design/" + file)
            (out / file).write_text(body)
            filenames.append(file)
    return group(out, kind, service, service_files, declaration), [out / p for p in filenames]


def group(out, kind, service, service_files, declaration, verify_read=False):
    block_kind = {"c": 2, "f": 1, "j": 4}[kind]
    group_name = f"cfj_group_{kind}"
    src = next(f for f in service_files if f.stem == service).read_text()
    interface = re.split(r"\)\s*\(\s*\n", src, maxsplit=1)[1].split("\n);", 1)[0]
    native_ports = {}
    direction = width = None
    for raw in interface.strip().split(","):
        item = raw.strip()
        match = re.fullmatch(r"(input|output)\s+(?:wire|reg)\s*(\[[^\]]+\])?\s+(\w+)", item)
        if match:
            direction, width, name = match.groups()
        else:
            name = item
        if not re.fullmatch(r"\w+", name):
            raise ValueError(f"unrecognized native port {item}")
        native_ports[name] = (direction, width or "")
    if kind == "j":
        internal = {"start", "start_ready", "join_tag", "join_three", "result_addr", "words",
                    "done_valid", "done_take", "done_error", "release_valid", "release_ready"}
    else:
        internal = {name for name in native_ports if name.startswith(("cmd_", "done_", "tx_"))}
    external = {name: spec for name, spec in native_ports.items()
                if name not in internal | {"clk", "reset"}}
    if kind != "j":
        external.update({
            "peer_reserved": ("input", ""), "peer_addr": ("input", "[9:0]"),
            "outgoing_valid": ("output", ""), "outgoing_ready": ("input", ""),
            "outgoing_addr": ("output", "[9:0]"), "outgoing_data": ("output", "[127:0]"),
            "outgoing_ack": ("input", ""), "outgoing_ack_ready": ("output", ""),
            "rx_reserved": ("output", ""), "rx_reserved_addr": ("output", "[9:0]"),
        })
    if verify_read and kind != "j":
        external.update(verify_read=("input", ""), verify_addr=("input", "[9:0]"),
                        verify_take=("input", ""), verify_valid=("output", ""),
                        verify_data=("output", "[127:0]"))
    exported = {name: spec for name, spec in declaration.items() if not SVC.match(name)}
    if set(exported).intersection(external):
        raise ValueError("control and data port name collision")
    exported.update(external)
    header = ",\n".join(f"    {d} wire {w} {n}" for n,(d,w) in exported.items())
    body = [f"module {group_name} #(parameter [7:0] BLOCK_ID=0,\n"
            f"    parameter [31:0] TOPOLOGY_ID=32'h01930010)(\n{header}\n);\n"]
    body.append(f"    localparam integer CLIENTS={5 if kind == 'c' else 4};\n"
                """    wire clk=clk_i;
    // Asynchronous assertion and two-cycle synchronous release.
    (* async_reg = "true" *) reg [1:0] reset_release;
    always @(posedge clk_i or negedge rst_ni) begin
        if (!rst_ni) reset_release <= 2'b00;
        else reset_release <= {reset_release[0], 1'b1};
    end
    wire reset=!reset_release[1];
""")
    core = {name: name for name in declaration}
    core["rst_ni"] = "reset_release[1]"
    for name,(direction,width) in declaration.items():
        if name.startswith("close_") or name == "svc_rsp_kind_i":
            # Only native EXEC is enabled by this profile. Unsupported
            # release/object-close opcodes keep the native controller's fault path.
            core[name] = "'0" if direction == "input" else ""
        elif name.startswith("svc_rsp_") and name[8:-2] in RETURN_REGS:
            body.append(f"    reg {width} {name};\n")
        elif name.startswith("svc_"):
            body.append(f"    wire {width} {name};\n")
    for name in sorted(internal):
        if name == "done_data":
            continue
        body.append(f"    wire {native_ports[name][1]} {name};\n")
    body.append("    always @(posedge clk) begin\n        if (reset) begin\n")
    for field in RETURN_REGS:
        body.append(f"            svc_rsp_{field}_i <= '0;\n")
    body.append("        end else if (svc_req_valid_o && svc_req_ready_i) begin\n")
    for field in RETURN_REGS:
        body.append(f"            svc_rsp_{field}_i <= svc_req_{field}_o;\n")
    body.append("        end\n    end\n")
    body.append(instance("lc_min_controller", "control", core,
        f".BLOCK_ID(BLOCK_ID), .ENABLE_NATIVE(1'b1), .NATIVE_BLOCK_TYPE(8'd{block_kind}), "
        ".NATIVE_TOPOLOGY(TOPOLOGY_ID), .STALL_LIMIT(4096)"))
    adapter = dict(clk="clk", reset="reset", svc_valid="svc_req_valid_o",
                   svc_ready="svc_req_ready_i", descriptor="svc_req_descriptor_o",
                   rsp_valid="svc_rsp_valid_i", rsp_ready="svc_rsp_ready_o",
                   status="svc_rsp_status_i", saturated="svc_rsp_saturated_i",
                   read_bytes="svc_rsp_read_bytes_i", write_bytes="svc_rsp_write_bytes_i")
    service_pins = {name: name for name in native_ports}
    if "done_data" in service_pins:
        service_pins["done_data"] = ""
    if kind == "j":
        for key in ("load_ready", "load_done", "load_error", "cmd_ready", "cmd_done",
                    "cmd_error", "cmd_saturated", "gate_ready", "gate_done", "gate_error",
                    "gate_saturated"):
            adapter[key] = "1'b0"
        adapter.update({n: n for n in ("start", "start_ready", "done_take", "done_valid",
                                        "done_error", "join_tag", "release_valid", "release_ready")})
        adapter["join_fields"] = "{join_three, words, result_addr}"
        body.append(instance("pj_native_service", "dispatch", adapter, ".JOIN_BLOCK(1'b1)"))
    else:
        body.append("    wire send_start, send_ready, send_done, native_rx_ready;\n"
                    "    wire [9:0] source_addr, destination_addr;\n"
                    "    wire rx_admitted=!deploy_valid_i || "
                    "(rx_reserved && rx_addr==rx_reserved_addr);\n"
                    "    assign rx_ready=native_rx_ready && rx_admitted;\n")
        service_pins["rx_valid"] = "rx_valid && rx_admitted"
        service_pins["rx_ready"] = "native_rx_ready"
        if verify_read:
            service_pins.update(tx_req="tx_req || verify_read",
                                tx_addr="verify_read ? verify_addr : tx_addr",
                                tx_take="tx_take || verify_take")
            body.append("    assign verify_valid=tx_valid;\n    assign verify_data=tx_data;\n")
        adapter.update({n: n for n in internal if n.startswith(("cmd_", "done_")) and n != "done_data"})
        adapter.update({n: n for n in ("send_start", "send_ready", "send_done",
                                        "source_addr", "destination_addr")})
        adapter.update(receive_commit="rx_stored && rx_stored_ready",
                       receive_reserved="rx_reserved", receive_address="rx_reserved_addr")
        body.append(instance("ucf_native_service", "dispatch", adapter, ".LANES(CLIENTS-2)"))
        transport = {n: n for n in ("clk", "reset", "source_addr", "destination_addr",
                                    "tx_req", "tx_ready", "tx_addr", "tx_valid", "tx_take", "tx_data")}
        transport.update(start="send_start", ready="send_ready", done="send_done",
                         rx_valid="outgoing_valid", rx_ready="outgoing_ready",
                         rx_addr="outgoing_addr", rx_data="outgoing_data", rx_stored="outgoing_ack",
                         rx_stored_ready="outgoing_ack_ready",
                         sink_reserved="peer_reserved && peer_addr==outgoing_addr")
        body.append(instance("stored_link", "transport", transport))
    if kind == "j":
        overrides = ".LATE_E_WRITEBACK(1'b1)"
    else:
        overrides = f".KIND({block_kind}), .LATE_G_E(1'b1)"
    body.append(instance(service, "services", service_pins, overrides))
    body.append("endmodule\n")
    (out / f"{group_name}.sv").write_text("".join(body))
    return group_name
