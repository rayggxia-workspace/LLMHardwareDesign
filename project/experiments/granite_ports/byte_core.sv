module byte_core #(
    parameter integer ROM_DEPTH = 32768
)(
    input logic clk, input logic reset,
    input logic [7:0] request,
    input logic [3:0] opcode [8],
    input logic [7:0] a [8], b [8], cin [8],
    output logic [7:0] response,
    output logic [7:0] lo [8], hi [8],
    input logic rom_request,
    input logic [14:0] rom_address,
    output logic rom_response,
    output logic [31:0] rom_data
);
    logic [7:0] nextlo [8], nexthi [8];
    logic [8:0] addtemp [8], subtemp [8];
    logic signed [15:0] product [8];
    logic [31:0] rom [0:ROM_DEPTH-1];
    logic [31:0] rom_stage0, rom_stage1;
    logic valid0, valid1;
    string rom_file;
    initial begin
        if ($value$plusargs("rom=%s", rom_file)) $readmemh(rom_file, rom);
    end
    always_comb begin
        for (integer i = 0; i < 8; i = i+1) begin
            nextlo[i] = 0; nexthi[i] = 0;
            addtemp[i] = {1'b0,a[i]} + {1'b0,b[i]} + {8'b0,cin[i][0]};
            subtemp[i] = {1'b0,a[i]} - {1'b0,b[i]} - {8'b0,cin[i][0]};
            // The only multiplication in this core has two signed eight-bit inputs.
            product[i] = $signed(a[i]) * $signed(b[i]);
            case (opcode[i])
                0,11: nextlo[i] = a[i];
                1: begin nextlo[i] = addtemp[i][7:0]; nexthi[i] = {7'b0,addtemp[i][8]}; end
                2: begin
                    nextlo[i] = subtemp[i][7:0];
                    nexthi[i] = {7'b0,({1'b0,a[i]} < ({1'b0,b[i]}+{8'b0,cin[i][0]}))};
                end
                3: begin nextlo[i] = product[i][7:0]; nexthi[i] = product[i][15:8]; end
                4: nextlo[i] = b[i] < 8 ? a[i] << b[i][2:0] : 8'b0;
                5: nextlo[i] = b[i] < 8 ? a[i] >> b[i][2:0] : 8'b0;
                6: nextlo[i] = a[i] | b[i];
                7: nextlo[i] = a[i] & b[i];
                8: nextlo[i] = a[i] ^ b[i];
                9: begin nextlo[i] = {7'b0,a[i]<b[i]}; nexthi[i] = {7'b0,a[i]==b[i]}; end
                10: nextlo[i] = cin[i][0] ? a[i] : b[i];
                default: begin nextlo[i] = 0; nexthi[i] = 0; end
            endcase
        end
    end
    always_ff @(posedge clk) begin
        if (reset) begin
            response <= 0; rom_response <= 0; valid0 <= 0; valid1 <= 0;
            rom_stage0 <= 0; rom_stage1 <= 0; rom_data <= 0;
            for (integer i = 0; i < 8; i = i+1) begin lo[i] <= 0; hi[i] <= 0; end
        end else begin
            response <= request;
            for (integer i = 0; i < 8; i = i+1) begin
                if (request[i]) begin lo[i] <= nextlo[i]; hi[i] <= nexthi[i]; end
            end
            // Single read request per edge. Accepted-edge to response-edge delta = 2.
            valid0 <= rom_request; valid1 <= valid0; rom_response <= valid1;
            if (rom_request) rom_stage0 <= rom[rom_address];
            rom_stage1 <= rom_stage0; rom_data <= rom_stage1;
        end
    end
endmodule
