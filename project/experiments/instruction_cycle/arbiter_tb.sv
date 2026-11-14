`timescale 1ns/1ps

module arbiter_tb;
    localparam integer CLIENTS = 3;
    localparam integer REQUESTS_PER_CLIENT = 3;
    localparam integer RESPONSE_DELAY = 2;

    reg clk = 0;
    reg reset = 1;
    reg [CLIENTS-1:0] req_valid = 0, req_write = 0, rsp_ready = 0;
    reg [CLIENTS*10-1:0] req_addr = 0;
    reg [CLIENTS*128-1:0] req_data = 0;
    wire [CLIENTS-1:0] req_ready, rsp_valid;
    wire [CLIENTS*128-1:0] rsp_data;
    wire mem_req, mem_write, mem_take, busy;
    wire [9:0] mem_addr;
    wire [127:0] mem_data;
    reg mem_ready = 0, mem_valid = 0;
    reg [127:0] mem_result = 0;
    reg waiting_to_send = 0;

    integer case_id, cycle;
    integer issued [0:CLIENTS-1];
    integer grant_owner, grant_sequence;
    integer pending_owner, pending_sequence, response_cycle;
    integer grants, sends, responses;

    block_local_s_arbiter #(.CLIENTS(CLIENTS)) dut (
        .clk, .reset, .req_valid, .req_write, .req_addr, .req_data,
        .req_ready, .rsp_valid, .rsp_ready, .rsp_data, .mem_req,
        .mem_write, .mem_addr, .mem_data, .mem_ready, .mem_valid,
        .mem_result, .mem_take, .busy
    );

    function automatic integer arrival(input integer client, sequence_id);
        if (case_id == 0) begin
            case (client)
                0: return sequence_id == 2 ? 8 : 0;
                1: return sequence_id == 2 ? 4 : 0;
                2: return sequence_id == 2 ? 5 : 0;
                default: return -1;
            endcase
        end
        case (client)
            0: return sequence_id == 2 ? 14 : 2;
            1: return 0;
            2: case (sequence_id)
                   0: return 0;
                   1: return 1;
                   2: return 13;
                   default: return -1;
               endcase
            default: return -1;
        endcase
    endfunction

    function automatic bit memory_open(input integer at);
        if (case_id == 0)
            return !((at >= 1 && at <= 3) || (at >= 16 && at <= 18));
        return !((at >= 1 && at <= 2) || (at >= 19 && at <= 22));
    endfunction

    function automatic bit receiver_open(input integer client, at);
        if (case_id == 0)
            return !((client == 0 && at >= 6 && at <= 8) ||
                     (client == 1 && at >= 12 && at <= 14));
        return !((client == 1 && at >= 5 && at <= 7) ||
                 (client == 2 && at >= 12 && at <= 14));
    endfunction

    function automatic [9:0] address(input integer client, sequence_id);
        return sequence_id % 2 == 0 ? 10'd4 : 10'(12 + client);
    endfunction

    function automatic bit is_write(input integer client, sequence_id);
        return (client + sequence_id) % 2 != 0;
    endfunction

    function automatic [127:0] payload(input integer client, sequence_id);
        return {32'hc1c1e265, 32'(client), 32'(sequence_id), 32'hdada0265};
    endfunction

    task automatic emit(input string event_name, input integer client, sequence_id);
        $display("{\"event\":\"%s\",\"cycle\":%0d,\"client\":%0d,\"sequence\":%0d,\"address\":%0d,\"write\":%0d}",
                 event_name, cycle, client, sequence_id, address(client, sequence_id),
                 is_write(client, sequence_id));
    endtask

    initial begin
        if (!$value$plusargs("CASE=%d", case_id)) case_id = 0;
        if (case_id != 0 && case_id != 1) $fatal(1, "CASE must be 0 or 1");
        for (integer client = 0; client < CLIENTS; client++) issued[client] = 0;
        grant_owner = -1;
        pending_owner = -1;
        grant_sequence = -1;
        pending_sequence = -1;
        response_cycle = -1;
        grants = 0;
        sends = 0;
        responses = 0;

        #5 clk = 1;
        #5 clk = 0;
        reset = 0;

        // Drive during the low half cycle and observe each handshake immediately
        // before the rising edge that accepts it. Cycle 0 is the first such edge.
        for (cycle = 0; cycle < 160; cycle++) begin
            for (integer client = 0; client < CLIENTS; client++) begin
                req_valid[client] = issued[client] < REQUESTS_PER_CLIENT && cycle >= arrival(client, issued[client]);
                req_write[client] = is_write(client, issued[client]);
                req_addr[client*10 +: 10] = address(client, issued[client]);
                req_data[client*128 +: 128] = payload(client, issued[client]);
                rsp_ready[client] = receiver_open(client, cycle);
            end
            mem_ready = pending_owner < 0 && memory_open(cycle);
            mem_valid = pending_owner >= 0 && cycle >= response_cycle;
            mem_result = mem_valid ? payload(pending_owner, pending_sequence) : 128'b0;
            #4;

            if (busy !== (grant_owner >= 0)) $fatal(1, "unexpected owner state at cycle %0d", cycle);
            for (integer client = 0; client < CLIENTS; client++) begin
                if (req_valid[client] && req_ready[client]) begin
                    if (grant_owner >= 0) $fatal(1, "multiple live grants at cycle %0d", cycle);
                    grant_owner = client;
                    grant_sequence = issued[client];
                    issued[client]++;
                    grants++;
                    emit("grant", client, grant_sequence);
                end
            end
            if (waiting_to_send && !mem_req)
                $fatal(1, "memory request dropped under backpressure at cycle %0d", cycle);
            if (mem_req) begin
                if (grant_owner < 0 || pending_owner >= 0 ||
                    mem_addr !== address(grant_owner, grant_sequence) ||
                    mem_write !== is_write(grant_owner, grant_sequence) ||
                    mem_data !== payload(grant_owner, grant_sequence))
                    $fatal(1, "invalid memory command at cycle %0d", cycle);
                if (mem_ready) begin
                    pending_owner = grant_owner;
                    pending_sequence = grant_sequence;
                    response_cycle = cycle + RESPONSE_DELAY;
                    sends++;
                    emit("send", pending_owner, pending_sequence);
                end
            end
            waiting_to_send = mem_req && !mem_ready;
            if (mem_valid && !rsp_valid[pending_owner])
                $fatal(1, "memory response dropped at cycle %0d", cycle);
            for (integer client = 0; client < CLIENTS; client++) begin
                if (rsp_valid[client]) begin
                    if (!mem_valid || client != pending_owner || client != grant_owner ||
                        rsp_data[client*128 +: 128] !== payload(pending_owner, pending_sequence))
                        $fatal(1, "misrouted memory response at cycle %0d", cycle);
                    if (rsp_ready[client]) begin
                        if (!mem_take) $fatal(1, "missing memory take at cycle %0d", cycle);
                        emit("response", pending_owner, pending_sequence);
                        pending_owner = -1;
                        grant_owner = -1;
                        responses++;
                    end
                end
            end

            #1 clk = 1;
            #5 clk = 0;
            if (responses == CLIENTS * REQUESTS_PER_CLIENT) begin
                if (grants != responses || sends != responses || busy)
                    $fatal(1, "terminal counters or state disagree");
                $display("{\"event\":\"summary\",\"case\":%0d,\"cycle\":%0d,\"grants\":%0d,\"sends\":%0d,\"responses\":%0d}",
                         case_id, cycle, grants, sends, responses);
                $finish;
                break;
            end
        end
        if (responses != CLIENTS * REQUESTS_PER_CLIENT)
            $fatal(1, "timeout waiting for arbiter to drain");
    end
endmodule
