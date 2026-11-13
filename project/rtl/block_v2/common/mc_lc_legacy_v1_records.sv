`timescale 1ns/1ps
// Record conversion for a single V1 local controller with one active call.
// Place next to the LC and connect the V2 side to the framed transport.
// The deployment manager supplies the binding after checking both images.
module mc_lc_legacy_v1_records #(
    parameter logic [7:0] GLOBAL_TARGET = 0,
    parameter logic [7:0] LEGACY_BLOCK_ID = 0
) (
    input  logic clk, reset,
    input  logic binding_valid,
    input  logic [31:0] native_image, native_topology, native_generation,
    input  logic [31:0] legacy_image, legacy_topology,
    input  logic native_task_valid, native_task_credit,
    input  logic [511:0] native_task,
    output logic native_task_ready,
    output logic native_event_valid,
    output logic [511:0] native_event,
    input  logic native_event_ready,
    output logic legacy_task_valid, legacy_task_credit,
    output logic [511:0] legacy_task,
    input  logic legacy_task_ready,
    input  logic legacy_event_valid,
    input  logic [511:0] legacy_event,
    output logic legacy_event_ready,
    output logic drained,
    output logic protocol_fault
);
    logic active, have_context;
    logic [95:0] owner;
    logic [7:0] token;
    logic [31:0] generation, topology, image, local_image, local_topology;

    wire [7:0] task_kind = native_task[16+:8];
    wire task_header_ok = native_task[0+:16] == 2 &&
                          native_task[24+:8] == GLOBAL_TARGET &&
                          native_task[128+:8] == 0 &&
                          native_task[136+:8] < 16 &&
                          native_task[144+:16] == 0;
    wire call_ok = task_header_ok && task_kind == 0 && native_task_credit &&
                   native_task[160+:32] == native_image &&
                   native_task[192+:32] == native_topology &&
                   native_task[224+:32] == native_generation;
    wire cancel_ok = task_header_ok && task_kind == 1 && !native_task_credit &&
                     have_context && native_task[32+:96] == owner &&
                     native_task[136+:8] == token && native_task[160+:32] == image &&
                     native_task[192+:32] == topology &&
                     native_task[224+:32] == generation && native_task[256+:256] == 0;

    wire [7:0] event_kind = legacy_event[16+:8];
    wire event_header_ok = active && legacy_event[0+:16] == 1 &&
                           legacy_event[24+:8] == LEGACY_BLOCK_ID &&
                           legacy_event[32+:96] == owner && legacy_event[352+:160] == 0;
    wire ready_ok = event_kind == 0 && legacy_event[128+:8] == 255 &&
                    legacy_event[144+:16] == 0 && legacy_event[192+:96] == 0 &&
                    legacy_event[288+:32] == 1 && legacy_event[320+:32] == '1;
    // The legacy terminal uses token zero because the LC owns only one call.
    wire terminal_ok = (event_kind == 2 || event_kind == 3) &&
                       legacy_event[128+:8] == 0 && legacy_event[136+:8] == 255 &&
                       legacy_event[160+:32] == 0 && legacy_event[256+:32] <= 1 &&
                       legacy_event[288+:32] == 0 &&
                       (event_kind == 2 ?
                        legacy_event[144+:16] == 0 && legacy_event[320+:32] == '1 :
                        legacy_event[144+:16] != 0);
    wire terminal_pending = legacy_event_valid && event_header_ok && terminal_ok;
    wire forward_call = !reset && !active && binding_valid && call_ok;
    wire forward_cancel = !reset && active && cancel_ok && !terminal_pending;
    wire task_fire = native_task_valid && native_task_ready;
    wire event_fire = legacy_event_valid && legacy_event_ready;

    assign drained = !reset && !active && !native_task_valid && !legacy_event_valid;
    assign legacy_task_valid = native_task_valid && (forward_call || forward_cancel);
    assign legacy_task_credit = forward_call;
    assign native_task_ready = !reset &&
        ((task_kind == 0 && !active && binding_valid && (!call_ok || legacy_task_ready)) ||
         (task_kind != 0 && (!cancel_ok || !active || terminal_pending || legacy_task_ready)));
    assign native_event_valid = !reset && legacy_event_valid;
    assign legacy_event_ready = !reset && native_event_ready;

    always_comb begin
        legacy_task = native_task;
        legacy_task[0+:16] = 1;
        legacy_task[24+:8] = LEGACY_BLOCK_ID;
        legacy_task[136+:8] = 0;
        legacy_task[160+:32] = task_kind == 0 ? legacy_image : local_image;
        legacy_task[192+:32] = task_kind == 0 ? legacy_topology : local_topology;
        legacy_task[224+:32] = 0;

        // Version zero is rejected by MC and cannot retire an owner.
        native_event = 0;
        if (event_header_ok && (ready_ok || terminal_ok)) begin
            native_event = legacy_event;
            native_event[0+:16] = 2;
            native_event[24+:8] = GLOBAL_TARGET;
            if (terminal_ok) native_event[128+:8] = token;
            native_event[352+:32] = generation;
            native_event[384+:32] = topology;
        end
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            active <= 0;
            have_context <= 0;
            owner <= 0;
            token <= 0;
            generation <= 0;
            topology <= 0;
            image <= 0;
            local_image <= 0;
            local_topology <= 0;
            protocol_fault <= 0;
        end else begin
            if (task_fire && forward_call) begin
                active <= 1;
                have_context <= 1;
                owner <= native_task[32+:96];
                token <= native_task[136+:8];
                generation <= native_generation;
                topology <= native_topology;
                image <= native_image;
                local_image <= legacy_image;
                local_topology <= legacy_topology;
            end
            if (event_fire && terminal_pending) active <= 0;
            if ((task_fire && !call_ok && !cancel_ok) ||
                (event_fire && !(event_header_ok && (ready_ok || terminal_ok))))
                protocol_fault <= 1;
        end
    end
endmodule
