// Issue29: finite-credit, beat-level two-bank memory-port reference RTL.
// All endpoint fields are packed with endpoint 0 in the least-significant bits.
module bank_port_fabric #(
    parameter integer PORT_MODE = 0,  // 0: 1RW, 1: 1R1W, 2: 2RW per bank
    parameter integer RESP_DEPTH = 2, // supported depths: 1, 2, 4
    parameter logic [5:0] LINK_MASK = 6'b111111
) (
    input  logic          clk,
    input  logic          rst,       // synchronous active high; no SRAM clearing
    input  logic [2:0]    req_valid,
    output logic [2:0]    req_ready,
    input  logic [2:0]    req_bank,
    input  logic [2:0]    req_write,
    input  logic [29:0]   req_addr,
    input  logic [1535:0] req_wdata,
    input  logic [191:0]  req_wstrb,
    input  logic [95:0]   req_tag,
    output logic [2:0]    rsp_valid,
    input  logic [2:0]    rsp_ready,
    output logic [2:0]    rsp_write,
    output logic [1535:0] rsp_data,
    output logic [95:0]   rsp_tag
);
    localparam integer PTR_W = (RESP_DEPTH <= 1) ? 1 : $clog2(RESP_DEPTH);
    localparam integer COUNT_W = $clog2(RESP_DEPTH + 1);

    // Two separate 64KiB arrays. This is behavioral memory, not a technology
    // SRAM macro or a claim that a synthesizer maps it into a given macro.
    logic [511:0] bank_mem [0:1][0:1023];

    // Registered read result and write acknowledgement share this FIFO.
    // There is no extra uncredited read pipeline or combinational bypass.
    logic [511:0] response_data [0:2][0:RESP_DEPTH-1];
    logic [31:0]  response_tag [0:2][0:RESP_DEPTH-1];
    logic         response_write [0:2][0:RESP_DEPTH-1];
    logic [PTR_W-1:0] rd_ptr [0:2];
    logic [PTR_W-1:0] wr_ptr [0:2];
    logic [COUNT_W-1:0] response_count [0:2];
    logic [1:0] rr [0:1];
    logic [1:0] rr_next [0:1];
    logic credit [0:2];
    logic slot_valid [0:1][0:1];
    logic [1:0] slot_ep [0:1][0:1];
    logic [2:0] selected_ep;

    // Versioned prototype: factor endpoint selection once per bank/slot.
    // These are combinational wires, with no new storage or port capacity.
    logic [9:0] selected_addr [0:1][0:1];
    logic [511:0] selected_data [0:1][0:1];
    logic [63:0] selected_strb [0:1][0:1];
    always_comb begin
        for (int bank = 0; bank < 2; bank = bank + 1) begin
            for (int slot = 0; slot < 2; slot = slot + 1) begin
                selected_addr[bank][slot] = req_addr[int'(slot_ep[bank][slot])*10 +: 10];
                selected_data[bank][slot] = req_wdata[int'(slot_ep[bank][slot])*512 +: 512];
                selected_strb[bank][slot] = req_wstrb[int'(slot_ep[bank][slot])*64 +: 64];
            end
        end
    end

    function automatic logic [PTR_W-1:0] advance_ptr(input logic [PTR_W-1:0] value);
        if (int'(value) == RESP_DEPTH - 1)
            advance_ptr = '0;
        else
            advance_ptr = value + 1'b1;
    endfunction

    always_comb begin
        req_ready = '0;
        rsp_valid = '0;
        rsp_write = '0;
        rsp_data = '0;
        rsp_tag = '0;
        selected_ep = '0;
        for (int ep = 0; ep < 3; ep = ep + 1) begin
            if (!rst && response_count[ep] != 0) begin
                rsp_valid[ep] = 1'b1;
                rsp_write[ep] = response_write[ep][rd_ptr[ep]];
                rsp_data[ep*512 +: 512] = response_data[ep][rd_ptr[ep]];
                rsp_tag[ep*32 +: 32] = response_tag[ep][rd_ptr[ep]];
            end
            // A head consumed at this edge frees a slot for this edge's grant.
            credit[ep] = (int'(response_count[ep]) < RESP_DEPTH) ||
                         (rsp_valid[ep] && rsp_ready[ep]);
        end
        for (int bank = 0; bank < 2; bank = bank + 1) begin
            int selected_count;
            logic served_read;
            logic served_write;
            logic [9:0] first_address;
            selected_count = 0;
            served_read = 1'b0;
            served_write = 1'b0;
            first_address = '0;
            rr_next[bank] = rr[bank];
            for (int slot = 0; slot < 2; slot = slot + 1) begin
                slot_valid[bank][slot] = 1'b0;
                slot_ep[bank][slot] = '0;
            end
            for (int offset = 0; offset < 3; offset = offset + 1) begin
                int ep;
                logic mode_ok;
                logic eligible;
                ep = int'(rr[bank]) + offset;
                if (ep >= 3)
                    ep = ep - 3;
                mode_ok = 1'b0;
                case (PORT_MODE)
                    0: mode_ok = (selected_count == 0);
                    1: mode_ok = (selected_count < 2) &&
                                 (req_write[ep] ? !served_write : !served_read);
                    2: mode_ok = (selected_count < 2);
                    default: mode_ok = 1'b0;
                endcase
                eligible = !rst && req_valid[ep] && !selected_ep[ep] &&
                           (int'(req_bank[ep]) == bank) && LINK_MASK[ep*2+bank] && credit[ep] &&
                           // Read response owns the endpoint's 512-bit data
                           // channel even when it will pop, or is stalled.
                           !(req_write[ep] && rsp_valid[ep] && !rsp_write[ep]);
                if (eligible && mode_ok &&
                    ((selected_count == 0) || req_addr[ep*10 +: 10] != first_address)) begin
                    slot_valid[bank][selected_count] = 1'b1;
                    slot_ep[bank][selected_count] = ep[1:0];
                    req_ready[ep] = 1'b1;
                    selected_ep[ep] = 1'b1;
                    if (selected_count == 0) begin
                        first_address = req_addr[ep*10 +: 10];
                        // Advance after the FIRST winner. Advancing after the
                        // last winner can starve R1 under persistent R0/R1/W2.
                        rr_next[bank] = (ep == 2) ? 2'd0 : ep[1:0] + 2'd1;
                    end
                    selected_count = selected_count + 1;
                    if (req_write[ep])
                        served_write = 1'b1;
                    else
                        served_read = 1'b1;
                end
            end
        end
    end

    always_ff @(posedge clk) begin
        if (rst) begin
            for (int ep = 0; ep < 3; ep = ep + 1) begin
                rd_ptr[ep] <= '0;
                wr_ptr[ep] <= '0;
                response_count[ep] <= '0;
            end
            for (int bank = 0; bank < 2; bank = bank + 1)
                rr[bank] <= '0;
        end else begin
            for (int bank = 0; bank < 2; bank = bank + 1)
                rr[bank] <= rr_next[bank];
            for (int ep = 0; ep < 3; ep = ep + 1) begin
                case ({(req_valid[ep] && req_ready[ep]), (rsp_valid[ep] && rsp_ready[ep])})
                    2'b10: response_count[ep] <= response_count[ep] + 1'b1;
                    2'b01: response_count[ep] <= response_count[ep] - 1'b1;
                    default: response_count[ep] <= response_count[ep];
                endcase
                if (rsp_valid[ep] && rsp_ready[ep])
                    rd_ptr[ep] <= advance_ptr(rd_ptr[ep]);
                if (req_valid[ep] && req_ready[ep]) begin
                    wr_ptr[ep] <= advance_ptr(wr_ptr[ep]);
                    response_write[ep][wr_ptr[ep]] <= req_write[ep];
                    response_tag[ep][wr_ptr[ep]] <= req_tag[ep*32 +: 32];
                end
            end
            // At most two explicit access slots per bank. Nonblocking SRAM
            // writes mean a registered read observes pre-edge contents.
            // Same-row dual grants of ANY kind have already been excluded.
            for (int bank = 0; bank < 2; bank = bank + 1) begin
                for (int slot = 0; slot < 2; slot = slot + 1) begin
                    if (slot_valid[bank][slot]) begin
                        int ep;
                        ep = int'(slot_ep[bank][slot]);
                        if (req_write[ep]) begin
                            response_data[ep][wr_ptr[ep]] <= '0;
                            for (int lane = 0; lane < 64; lane = lane + 1) begin
                                if (selected_strb[bank][slot][lane])
                                    bank_mem[bank][selected_addr[bank][slot]][lane*8 +: 8]
                                        <= selected_data[bank][slot][lane*8 +: 8];
                            end
                        end else begin
                            response_data[ep][wr_ptr[ep]] <= bank_mem[bank][selected_addr[bank][slot]];
                        end
                    end
                end
            end
        end
    end

`ifndef SYNTHESIS
    initial begin
        assert (PORT_MODE >= 0 && PORT_MODE <= 2)
            else $fatal(1, "PORT_MODE must be 0, 1 or 2");
        assert (RESP_DEPTH == 1 || RESP_DEPTH == 2 || RESP_DEPTH == 4)
            else $fatal(1, "RESP_DEPTH must be 1, 2 or 4");
    end

    // These history registers only monitor the interface; they are excluded
    // from the synthesis inventory by the SYNTHESIS guard.
    logic [2:0] prev_rsp_stall;
    logic [2:0] prev_req_stall;
    logic [2:0] held_rsp_write;
    logic [1535:0] held_rsp_data;
    logic [95:0] held_rsp_tag;
    logic [2:0] held_req_bank;
    logic [2:0] held_req_write;
    logic [29:0] held_req_addr;
    logic [1535:0] held_req_data;
    logic [191:0] held_req_strb;
    logic [95:0] held_req_tag;

    always_ff @(posedge clk) begin
        if (rst) begin
            prev_rsp_stall <= '0;
            prev_req_stall <= '0;
        end else begin
            for (int ep = 0; ep < 3; ep = ep + 1) begin
                assert (int'(response_count[ep]) <= RESP_DEPTH)
                    else $fatal(1, "response count overflow ep=%0d", ep);
                assert (int'(rd_ptr[ep]) < RESP_DEPTH && int'(wr_ptr[ep]) < RESP_DEPTH)
                    else $fatal(1, "response pointer out of range ep=%0d", ep);
                if (req_ready[ep]) begin
                    assert (req_valid[ep] && credit[ep] && LINK_MASK[ep*2+int'(req_bank[ep])])
                        else $fatal(1, "grant without request/credit/link ep=%0d", ep);
                    assert (!(req_write[ep] && rsp_valid[ep] && !rsp_write[ep]))
                        else $fatal(1, "endpoint read-response/write-request conflict ep=%0d", ep);
                end
                if (prev_rsp_stall[ep]) begin
                    assert (rsp_valid[ep] && (rsp_write[ep] === held_rsp_write[ep]) &&
                            (rsp_data[ep*512 +: 512] === held_rsp_data[ep*512 +: 512]) &&
                            (rsp_tag[ep*32 +: 32] === held_rsp_tag[ep*32 +: 32]))
                        else $fatal(1, "response changed while stalled ep=%0d", ep);
                end
                if (prev_req_stall[ep]) begin
                    assert (req_valid[ep] && (req_bank[ep] === held_req_bank[ep]) &&
                            (req_write[ep] === held_req_write[ep]) &&
                            (req_addr[ep*10 +: 10] === held_req_addr[ep*10 +: 10]) &&
                            (req_wdata[ep*512 +: 512] === held_req_data[ep*512 +: 512]) &&
                            (req_wstrb[ep*64 +: 64] === held_req_strb[ep*64 +: 64]) &&
                            (req_tag[ep*32 +: 32] === held_req_tag[ep*32 +: 32]))
                        else $fatal(1, "source changed request while stalled ep=%0d", ep);
                end
            end
            for (int bank = 0; bank < 2; bank = bank + 1) begin
                assert (!slot_valid[bank][1] || slot_valid[bank][0])
                    else $fatal(1, "noncontiguous grant slots");
                if (PORT_MODE == 0)
                    assert (!slot_valid[bank][1]) else $fatal(1, "1RW double grant");
                if (slot_valid[bank][0] && slot_valid[bank][1]) begin
                    assert (slot_ep[bank][0] != slot_ep[bank][1])
                        else $fatal(1, "same endpoint granted twice");
                    assert (req_addr[int'(slot_ep[bank][0])*10 +: 10] !=
                            req_addr[int'(slot_ep[bank][1])*10 +: 10])
                        else $fatal(1, "same-row dual grant");
                    if (PORT_MODE == 1)
                        assert (req_write[slot_ep[bank][0]] != req_write[slot_ep[bank][1]])
                            else $fatal(1, "1R1W same-kind double grant");
                end
            end
            prev_rsp_stall <= rsp_valid & ~rsp_ready;
            prev_req_stall <= req_valid & ~req_ready;
            held_rsp_write <= rsp_write;
            held_rsp_data <= rsp_data;
            held_rsp_tag <= rsp_tag;
            held_req_bank <= req_bank;
            held_req_write <= req_write;
            held_req_addr <= req_addr;
            held_req_data <= req_wdata;
            held_req_strb <= req_wstrb;
            held_req_tag <= req_tag;
        end
    end
`endif
endmodule
