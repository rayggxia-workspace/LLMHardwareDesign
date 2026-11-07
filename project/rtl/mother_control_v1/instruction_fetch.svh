// Included in each controller's program fetch path.
wire [15:0] instruction_version = header[64+:16];
wire compact_image = instruction_version==16'd2;
wire instruction_version_ok = compact_image || instruction_version==16'd1;
wire [8:0] instruction_beats = compact_image ? {1'b0,inst_count[8:1]}+{8'b0,inst_count[0]} :
                                             inst_count[8:0];
wire [31:0] fetch_word = compact_image ? {1'b0,pc[31:1]} : pc;
wire [63:0] fetch_address = {32'b0,inst_offset}+{28'b0,fetch_word,4'b0};
wire [63:0] instruction_end = {32'b0,inst_offset}+{51'b0,instruction_beats,4'b0};
wire [63:0] short_instruction = pc[0] ? pm_rsp_data_i[127:64] : pm_rsp_data_i[63:0];
wire short_branch = short_instruction[63:56]==8'h15 || short_instruction[63:56]==8'h4b;
wire short_branch_reserved = |{short_instruction[52:48],short_instruction[15:0]};
// Expand only into the existing decode register, never into program memory.
wire [127:0] fetch_instruction = !compact_image ? pm_rsp_data_i : short_branch ?
      {short_instruction[63:56],7'b0,short_branch_reserved,5'b0,short_instruction[55:53],
       40'b0,16'b0,short_instruction[47:32],16'b0,short_instruction[31:16]} :
      {short_instruction[63:56],8'b0,short_instruction[55:32],24'b0,short_instruction[31:0],32'b0};
wire bad_instruction_padding = compact_image && inst_count[0] &&
       {50'b0,cfg_address}+64'd16==instruction_end && |pm_rsp_data_i[127:64];

wire [31:0] branch_true_pc = ireg[63:32];
wire [31:0] branch_false_pc = ireg[31:0];
wire branch_fields_ok = ireg[119:112]==0;
wire branch_targets_ok = branch_true_pc>pc && branch_true_pc<inst_count &&
                         branch_false_pc>pc && branch_false_pc<inst_count;
wire [31:0] branch_next_pc = (|registers[ireg[106:104]]) ? branch_true_pc : branch_false_pc;
