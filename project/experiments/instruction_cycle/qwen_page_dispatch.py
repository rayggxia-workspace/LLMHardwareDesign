"""Predict the control path from MC PM installation to an LC descriptor offer.

This model uses the successful, serial generation-1 path of the frozen 105530
fixture. All cycle indices are the DDR bridge's pre-edge core count.
"""

from qwen_native_control import BURST_BYTES, DESCRIPTOR_BYTES, require


PM_WORD_BYTES = 16
MC_PM_REQUEST_TO_RESPONSE = 4
MC_CONFIG_PM_ACK = MC_PM_REQUEST_TO_RESPONSE + 2
MC_INSTRUCTION_CYCLES = MC_PM_REQUEST_TO_RESPONSE + 2
PACKET_FLITS = 4
LC_PM_REQUEST_TO_RESPONSE = 1
LC_META_WORDS = 20
CRC_BYTES = DESCRIPTOR_BYTES - 4


def _descriptor_edges(call, decode):
    # mc_native_controller queues CALL after decode; mc_packet128_bridge
    # accepts it only on the fourth flit. The LC validates the buffered frame
    # the following edge, then reads and decodes EXEC followed by 20 PM words.
    mc_call_accept = decode + PACKET_FLITS
    lc_call_accept = mc_call_accept + 1
    lc_exec_decode = lc_call_accept + LC_PM_REQUEST_TO_RESPONSE + 2
    meta_stride = LC_PM_REQUEST_TO_RESPONSE + 1
    lc_fetch_start = lc_exec_decode + LC_META_WORDS * meta_stride + 1
    address = call["descriptor_address"]
    return {"mc_call_decode": decode, "first_call_accept": mc_call_accept, "lc_call_accept": lc_call_accept,
            "lc_exec_decode": lc_exec_decode, "lc_fetch_start": lc_fetch_start,
            "descriptor_admissions": [{"cycle": lc_fetch_start + 1 + index,
                                       "target": call["target"], "tag": call["ticket"] * 2 + index,
                                       "address": address + index * BURST_BYTES}
                                      for index in range(DESCRIPTOR_BYTES // BURST_BYTES)]}


def _wait_release(service_retire):
    # The service router reports a completion one edge after provider retire.
    # WAIT consumes it, then LC END reads/decodes and releases descriptor
    # ownership. Its four-flit terminal reaches the MC's buffered return.
    lc_completion = service_retire + 1
    lc_end_decode = lc_completion + LC_PM_REQUEST_TO_RESPONSE + 2
    lc_scope_release = lc_end_decode + 1
    mc_return = lc_scope_release + PACKET_FLITS + 1
    # The WAIT already decoded before the provider retires. Its token frees
    # one edge after MC records the terminal.
    return {"lc_completion": lc_completion, "lc_scope_release": lc_scope_release,
            "mc_return": mc_return, "mc_wait_release": mc_return + 1}


def dispatch(page, mc_last_write_ack, mode):
    """Predict generation 1 startup and its first two descriptor admissions."""
    require(type(mc_last_write_ack) is int and mc_last_write_ack >= 0 and mode in (0, 1),
            "invalid MC installation ACK or testbench mode")
    require(page["generation"] == 1 and page["target_mask"] == 1 and page["bytes"] == 240,
            "unsupported page for serial dispatch")
    call = page["calls"][0]
    require((call["target"], call["ticket"], call["wave"], call["mc_pc"]) == (0, 1, 0, 8),
            "unexpected generation 1 CALL entry")

    # native_mc_image_install consumes STREAM REPORT, issues one READ config
    # per word, and folds one byte per edge after the readback response.
    readback_first = mc_last_write_ack + 2
    readback_stride = MC_CONFIG_PM_ACK + PM_WORD_BYTES + 1
    readback_words = [readback_first + index * readback_stride
                      for index in range(page["bytes"] // PM_WORD_BYTES)]
    prove = readback_words[-1] + readback_stride
    prepare = prove + 2  # PROVE request, its registered ACK, then PREPARE
    installed = prepare + 2  # PREPARE ACK, then install REPORT to cohort
    started = installed + 2  # deploy/READY edge, then START handshake
    first_fetch = started + 1
    decode = first_fetch + call["mc_pc"] * MC_INSTRUCTION_CYCLES + MC_PM_REQUEST_TO_RESPONSE + 1
    return {"mc_last_write_ack": mc_last_write_ack, "mc_readback_requests": readback_words,
            "mc_prove": prove, "mc_prepare": prepare, "mc_install_retire": installed, "mc_start": started,
            **_descriptor_edges(call, decode)}


def service_accept(last_lc_descriptor_response):
    """Predict an immediately ready native provider after the LC checks CRC32."""
    require(type(last_lc_descriptor_response) is int and last_lc_descriptor_response >= 0,
            "invalid descriptor response cycle")
    # On the final response edge lc_scope_fetch128 enters CRC. It visits
    # bytes 0 through 123, then FETCH_WAIT consumes DONE. The route's offer
    # is combinational when the service router is free.
    return last_lc_descriptor_response + CRC_BYTES + 2


def next_call(page, completed_index, service_retire):
    """Predict the next serial generation-1 CALL from a provider retirement."""
    require(type(completed_index) is int and 0 <= completed_index < len(page["calls"]) - 1
            and type(service_retire) is int and service_retire >= 0,
            "invalid generation 1 provider retirement")
    require(page["generation"] == 1 and page["target_mask"] == 1,
            "unsupported page for serial dispatch")
    previous, upcoming = page["calls"][completed_index:completed_index + 2]
    require(previous["target"] == upcoming["target"] == 0
            and upcoming["ticket"] == previous["ticket"] + 1
            and upcoming["wave"] == previous["wave"] + 1
            and page["waves"][previous["wave"]]["wait_pc"] == previous["mc_pc"] + 2
            and upcoming["mc_pc"] == previous["mc_pc"], "unsupported serial WAIT/LOOP path")
    release = _wait_release(service_retire)
    mc_loop_decode = release["mc_wait_release"] + MC_INSTRUCTION_CYCLES
    return {**release, "mc_loop_decode": mc_loop_decode,
            **_descriptor_edges(upcoming, mc_loop_decode + MC_INSTRUCTION_CYCLES)}


def page_commit(page, last_service_retire):
    """Predict generation 1's commit given its final provider retirement."""
    require(page["generation"] == 1 and page["target_mask"] == 1 and page["calls"][-1]["ticket"] == 124
            and type(last_service_retire) is int and last_service_retire >= 0,
            "invalid generation 1 final provider retirement")
    # After the final WAIT, LOOP falls through to END. The cohort takes the
    # resulting terminal then offers the page commit on the following edge.
    wait = _wait_release(last_service_retire)["mc_wait_release"]
    return wait + 2 * MC_INSTRUCTION_CYCLES + 2
