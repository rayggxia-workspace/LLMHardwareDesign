`timescale 1ns/1ps
// Refs #250. Candidate PR249 LUT257 S32/Q16 activation and gated Mid32.
// Two lanes, four elastic register stages. One logical 257x32 constant table;
// four combinational point lookups are real synthesis resources, not free ports.
// A fault is atomic across the packet: out_error forbids every lane's S write.
module g_s32 (
    input  wire        clk,
    input  wire        reset,
    input  wire        in_valid,
    output wire        in_ready,
    input  wire [63:0] in_gate,
    input  wire [63:0] in_up,
    input  wire        in_gated,
    input  wire [1:0]  in_mask,
    output wire        out_valid,
    input  wire        out_ready,
    output wire [63:0] out_data,
    output wire [1:0]  out_mask,
    output wire        out_error
);
    function automatic signed [31:0] lut(input logic [8:0] index);
        case (index)
            // LUT257_GENERATED_BEGIN
            9'd0: lut = 32'sd0;
            9'd1: lut = 32'sd0;
            9'd2: lut = 32'sd0;
            9'd3: lut = 32'sd0;
            9'd4: lut = 32'sd0;
            9'd5: lut = 32'sd0;
            9'd6: lut = 32'sd0;
            9'd7: lut = 32'sd0;
            9'd8: lut = 32'sd0;
            9'd9: lut = 32'sd0;
            9'd10: lut = 32'sd0;
            9'd11: lut = 32'sd0;
            9'd12: lut = 32'sd0;
            9'd13: lut = -32'sd1;
            9'd14: lut = -32'sd1;
            9'd15: lut = -32'sd1;
            9'd16: lut = -32'sd1;
            9'd17: lut = -32'sd1;
            9'd18: lut = -32'sd1;
            9'd19: lut = -32'sd1;
            9'd20: lut = -32'sd1;
            9'd21: lut = -32'sd1;
            9'd22: lut = -32'sd2;
            9'd23: lut = -32'sd2;
            9'd24: lut = -32'sd2;
            9'd25: lut = -32'sd2;
            9'd26: lut = -32'sd2;
            9'd27: lut = -32'sd3;
            9'd28: lut = -32'sd3;
            9'd29: lut = -32'sd3;
            9'd30: lut = -32'sd4;
            9'd31: lut = -32'sd4;
            9'd32: lut = -32'sd5;
            9'd33: lut = -32'sd5;
            9'd34: lut = -32'sd6;
            9'd35: lut = -32'sd7;
            9'd36: lut = -32'sd8;
            9'd37: lut = -32'sd9;
            9'd38: lut = -32'sd10;
            9'd39: lut = -32'sd11;
            9'd40: lut = -32'sd12;
            9'd41: lut = -32'sd13;
            9'd42: lut = -32'sd15;
            9'd43: lut = -32'sd17;
            9'd44: lut = -32'sd19;
            9'd45: lut = -32'sd21;
            9'd46: lut = -32'sd24;
            9'd47: lut = -32'sd27;
            9'd48: lut = -32'sd30;
            9'd49: lut = -32'sd33;
            9'd50: lut = -32'sd37;
            9'd51: lut = -32'sd42;
            9'd52: lut = -32'sd47;
            9'd53: lut = -32'sd52;
            9'd54: lut = -32'sd58;
            9'd55: lut = -32'sd65;
            9'd56: lut = -32'sd73;
            9'd57: lut = -32'sd81;
            9'd58: lut = -32'sd91;
            9'd59: lut = -32'sd101;
            9'd60: lut = -32'sd113;
            9'd61: lut = -32'sd127;
            9'd62: lut = -32'sd141;
            9'd63: lut = -32'sd158;
            9'd64: lut = -32'sd176;
            9'd65: lut = -32'sd196;
            9'd66: lut = -32'sd219;
            9'd67: lut = -32'sd244;
            9'd68: lut = -32'sd272;
            9'd69: lut = -32'sd303;
            9'd70: lut = -32'sd337;
            9'd71: lut = -32'sd375;
            9'd72: lut = -32'sd418;
            9'd73: lut = -32'sd465;
            9'd74: lut = -32'sd517;
            9'd75: lut = -32'sd575;
            9'd76: lut = -32'sd639;
            9'd77: lut = -32'sd711;
            9'd78: lut = -32'sd789;
            9'd79: lut = -32'sd876;
            9'd80: lut = -32'sd972;
            9'd81: lut = -32'sd1078;
            9'd82: lut = -32'sd1196;
            9'd83: lut = -32'sd1325;
            9'd84: lut = -32'sd1467;
            9'd85: lut = -32'sd1624;
            9'd86: lut = -32'sd1796;
            9'd87: lut = -32'sd1985;
            9'd88: lut = -32'sd2193;
            9'd89: lut = -32'sd2421;
            9'd90: lut = -32'sd2670;
            9'd91: lut = -32'sd2943;
            9'd92: lut = -32'sd3240;
            9'd93: lut = -32'sd3564;
            9'd94: lut = -32'sd3917;
            9'd95: lut = -32'sd4300;
            9'd96: lut = -32'sd4715;
            9'd97: lut = -32'sd5163;
            9'd98: lut = -32'sd5647;
            9'd99: lut = -32'sd6167;
            9'd100: lut = -32'sd6724;
            9'd101: lut = -32'sd7318;
            9'd102: lut = -32'sd7950;
            9'd103: lut = -32'sd8620;
            9'd104: lut = -32'sd9324;
            9'd105: lut = -32'sd10062;
            9'd106: lut = -32'sd10829;
            9'd107: lut = -32'sd11620;
            9'd108: lut = -32'sd12429;
            9'd109: lut = -32'sd13245;
            9'd110: lut = -32'sd14060;
            9'd111: lut = -32'sd14858;
            9'd112: lut = -32'sd15624;
            9'd113: lut = -32'sd16339;
            9'd114: lut = -32'sd16979;
            9'd115: lut = -32'sd17520;
            9'd116: lut = -32'sd17933;
            9'd117: lut = -32'sd18186;
            9'd118: lut = -32'sd18244;
            9'd119: lut = -32'sd18070;
            9'd120: lut = -32'sd17625;
            9'd121: lut = -32'sd16871;
            9'd122: lut = -32'sd15769;
            9'd123: lut = -32'sd14281;
            9'd124: lut = -32'sd12371;
            9'd125: lut = -32'sd10011;
            9'd126: lut = -32'sd7173;
            9'd127: lut = -32'sd3840;
            9'd128: lut = 32'sd0;
            9'd129: lut = 32'sd4352;
            9'd130: lut = 32'sd9211;
            9'd131: lut = 32'sd14565;
            9'd132: lut = 32'sd20397;
            9'd133: lut = 32'sd26679;
            9'd134: lut = 32'sd33383;
            9'd135: lut = 32'sd40473;
            9'd136: lut = 32'sd47911;
            9'd137: lut = 32'sd55658;
            9'd138: lut = 32'sd63676;
            9'd139: lut = 32'sd71926;
            9'd140: lut = 32'sd80371;
            9'd141: lut = 32'sd88976;
            9'd142: lut = 32'sd97709;
            9'd143: lut = 32'sd106541;
            9'd144: lut = 32'sd115448;
            9'd145: lut = 32'sd124406;
            9'd146: lut = 32'sd133396;
            9'd147: lut = 32'sd142403;
            9'd148: lut = 32'sd151411;
            9'd149: lut = 32'sd160412;
            9'd150: lut = 32'sd169395;
            9'd151: lut = 32'sd178354;
            9'd152: lut = 32'sd187284;
            9'd153: lut = 32'sd196180;
            9'd154: lut = 32'sd205042;
            9'd155: lut = 32'sd213866;
            9'd156: lut = 32'sd222652;
            9'd157: lut = 32'sd231401;
            9'd158: lut = 32'sd240113;
            9'd159: lut = 32'sd248789;
            9'd160: lut = 32'sd257429;
            9'd161: lut = 32'sd266036;
            9'd162: lut = 32'sd274611;
            9'd163: lut = 32'sd283156;
            9'd164: lut = 32'sd291672;
            9'd165: lut = 32'sd300161;
            9'd166: lut = 32'sd308626;
            9'd167: lut = 32'sd317067;
            9'd168: lut = 32'sd325487;
            9'd169: lut = 32'sd333887;
            9'd170: lut = 32'sd342268;
            9'd171: lut = 32'sd350632;
            9'd172: lut = 32'sd358981;
            9'd173: lut = 32'sd367315;
            9'd174: lut = 32'sd375636;
            9'd175: lut = 32'sd383946;
            9'd176: lut = 32'sd392244;
            9'd177: lut = 32'sd400532;
            9'd178: lut = 32'sd408811;
            9'd179: lut = 32'sd417081;
            9'd180: lut = 32'sd425345;
            9'd181: lut = 32'sd433601;
            9'd182: lut = 32'sd441851;
            9'd183: lut = 32'sd450095;
            9'd184: lut = 32'sd458334;
            9'd185: lut = 32'sd466569;
            9'd186: lut = 32'sd474799;
            9'd187: lut = 32'sd483025;
            9'd188: lut = 32'sd491248;
            9'd189: lut = 32'sd499468;
            9'd190: lut = 32'sd507685;
            9'd191: lut = 32'sd515900;
            9'd192: lut = 32'sd524112;
            9'd193: lut = 32'sd532322;
            9'd194: lut = 32'sd540531;
            9'd195: lut = 32'sd548737;
            9'd196: lut = 32'sd556943;
            9'd197: lut = 32'sd565147;
            9'd198: lut = 32'sd573349;
            9'd199: lut = 32'sd581551;
            9'd200: lut = 32'sd589751;
            9'd201: lut = 32'sd597951;
            9'd202: lut = 32'sd606150;
            9'd203: lut = 32'sd614348;
            9'd204: lut = 32'sd622545;
            9'd205: lut = 32'sd630742;
            9'd206: lut = 32'sd638939;
            9'd207: lut = 32'sd647135;
            9'd208: lut = 32'sd655330;
            9'd209: lut = 32'sd663525;
            9'd210: lut = 32'sd671720;
            9'd211: lut = 32'sd679915;
            9'd212: lut = 32'sd688109;
            9'd213: lut = 32'sd696303;
            9'd214: lut = 32'sd704497;
            9'd215: lut = 32'sd712691;
            9'd216: lut = 32'sd720884;
            9'd217: lut = 32'sd729077;
            9'd218: lut = 32'sd737270;
            9'd219: lut = 32'sd745463;
            9'd220: lut = 32'sd753656;
            9'd221: lut = 32'sd761849;
            9'd222: lut = 32'sd770042;
            9'd223: lut = 32'sd778235;
            9'd224: lut = 32'sd786427;
            9'd225: lut = 32'sd794620;
            9'd226: lut = 32'sd802812;
            9'd227: lut = 32'sd811005;
            9'd228: lut = 32'sd819197;
            9'd229: lut = 32'sd827389;
            9'd230: lut = 32'sd835582;
            9'd231: lut = 32'sd843774;
            9'd232: lut = 32'sd851966;
            9'd233: lut = 32'sd860158;
            9'd234: lut = 32'sd868350;
            9'd235: lut = 32'sd876543;
            9'd236: lut = 32'sd884735;
            9'd237: lut = 32'sd892927;
            9'd238: lut = 32'sd901119;
            9'd239: lut = 32'sd909311;
            9'd240: lut = 32'sd917503;
            9'd241: lut = 32'sd925695;
            9'd242: lut = 32'sd933887;
            9'd243: lut = 32'sd942079;
            9'd244: lut = 32'sd950272;
            9'd245: lut = 32'sd958464;
            9'd246: lut = 32'sd966656;
            9'd247: lut = 32'sd974848;
            9'd248: lut = 32'sd983040;
            9'd249: lut = 32'sd991232;
            9'd250: lut = 32'sd999424;
            9'd251: lut = 32'sd1007616;
            9'd252: lut = 32'sd1015808;
            9'd253: lut = 32'sd1024000;
            9'd254: lut = 32'sd1032192;
            9'd255: lut = 32'sd1040384;
            9'd256: lut = 32'sd1048576;
            // LUT257_GENERATED_END
            default: lut = 32'sd0;
        endcase
    endfunction

    function automatic signed [63:0] rne13(input logic signed [63:0] value);
        reg signed [63:0] quotient;
        reg [63:0] remainder;
        begin
            quotient = value >>> 13;
            remainder = $unsigned(value - (quotient <<< 13));
            rne13 = quotient + ((remainder > 64'd4096 ||
                               (remainder == 64'd4096 && quotient[0])) ? 64'sd1 : 64'sd0);
        end
    endfunction

    function automatic signed [63:0] rne16(input logic signed [63:0] value);
        reg signed [63:0] quotient;
        reg [63:0] remainder;
        begin
            quotient = value >>> 16;
            remainder = $unsigned(value - (quotient <<< 16));
            rne16 = quotient + ((remainder > 64'd32768 ||
                               (remainder == 64'd32768 && quotient[0])) ? 64'sd1 : 64'sd0);
        end
    endfunction

    function automatic signed [31:0] interpolate(
        input logic signed [31:0] low_point,
        input logic signed [31:0] high_point,
        input logic [12:0] fraction
    );
        reg signed [63:0] delta, product;
        begin
            delta = {{32{high_point[31]}}, high_point} - {{32{low_point[31]}}, low_point};
            product = delta * $signed({1'b0, fraction});
            // RNE interpolation stays between the two S32 table endpoints.
            interpolate = low_point + 32'(rne13(product));
        end
    endfunction

    reg v0, v1, v2, v3;
    wire r3 = !v3 || out_ready;
    wire r2 = !v2 || r3;
    wire r1 = !v1 || r2;
    wire r0 = !v0 || r1;
    assign in_ready = !reset && r0;
    assign out_valid = !reset && v3;

    reg gated0, gated1;
    reg [1:0] mask0, mask1, mask2, mask3;
    reg signed [31:0] gate0 [0:1], up0 [0:1], low0 [0:1], high0 [0:1];
    reg [12:0] frac0 [0:1];
    reg [1:0] mode0 [0:1];
    reg signed [31:0] act1 [0:1], up1 [0:1];
    reg signed [63:0] product2 [0:1];
    reg [63:0] data3;
    reg error3;
    assign out_data = data3;
    assign out_mask = mask3;
    assign out_error = error3;

    wire signed [31:0] gate_in [0:1];
    wire [20:0] offset_in [0:1];
    wire [8:0] index_in [0:1];
    genvar lane;
    generate for (lane = 0; lane < 2; lane = lane + 1) begin: input_decode
        assign gate_in[lane] = $signed(in_gate[32*lane +: 32]);
        // Only the interior interval uses these low 21 bits.
        assign offset_in[lane] = in_gate[32*lane +: 21] + 21'd1048576;
        assign index_in[lane] = {1'b0, offset_in[lane][20:13]};
    end endgenerate

    reg [63:0] rounded_data;
    reg rounded_error;
    reg signed [63:0] rounded [0:1];
    integer j;
    always @* begin
        rounded_data = 64'b0;
        rounded_error = (mask2 == 2'b00);
        for (integer i = 0; i < 2; i = i + 1) begin
            rounded[i] = rne16(product2[i]);
            if (mask2[i]) begin
                if (rounded[i] < -64'sd2147483648 || rounded[i] > 64'sd2147483647)
                    rounded_error = 1'b1;
                rounded_data[32*i +: 32] = rounded[i][31:0];
            end
        end
        if (rounded_error) rounded_data = 64'b0;
    end

    always @(posedge clk) begin
        if (reset) begin
            v0 <= 1'b0;
            v1 <= 1'b0;
            v2 <= 1'b0;
            v3 <= 1'b0;
        end else begin
            if (r0) begin
                v0 <= in_valid;
                if (in_valid) begin
                    gated0 <= in_gated;
                    mask0 <= in_mask;
                    for (j = 0; j < 2; j = j + 1) begin
                        gate0[j] <= gate_in[j];
                        up0[j] <= $signed(in_up[32*j +: 32]);
                        frac0[j] <= offset_in[j][12:0];
                        low0[j] <= lut(index_in[j]);
                        high0[j] <= lut(index_in[j] + 9'd1);
                        mode0[j] <= gate_in[j] <= -32'sd1048576 ? 2'd0 :
                                    gate_in[j] >= 32'sd1048576 ? 2'd2 : 2'd1;
                    end
                end
            end
            if (r1) begin
                v1 <= v0;
                if (v0) begin
                    gated1 <= gated0;
                    mask1 <= mask0;
                    for (j = 0; j < 2; j = j + 1) begin
                        up1[j] <= up0[j];
                        if (!mask0[j] || mode0[j] == 2'd0) act1[j] <= 32'sd0;
                        else if (mode0[j] == 2'd2) act1[j] <= gate0[j];
                        else act1[j] <= interpolate(low0[j], high0[j], frac0[j]);
                    end
                end
            end
            if (r2) begin
                v2 <= v1;
                if (v1) begin
                    mask2 <= mask1;
                    for (j = 0; j < 2; j = j + 1) begin
                        if (gated1) product2[j] <= $signed(act1[j]) * $signed(up1[j]);
                        else product2[j] <= $signed({{32{act1[j][31]}}, act1[j]}) <<< 16;
                    end
                end
            end
            if (r3) begin
                v3 <= v2;
                if (v2) begin
                    mask3 <= mask2;
                    data3 <= rounded_data;
                    error3 <= rounded_error;
                end
            end
        end
    end
endmodule
