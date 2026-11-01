`timescale 1ns/1ps
// Frozen expectations use independent math oracle. No DUT output forms an expected value.
module block_w3_adapters_tb;
  localparam NE=22,NG=14;
  function automatic integer e_op;input integer index;begin case(index)
    0:e_op=0;
    1:e_op=1;
    2:e_op=2;
    3:e_op=3;
    4:e_op=4;
    5:e_op=5;
    6:e_op=6;
    7:e_op=7;
    8:e_op=8;
    9:e_op=9;
    10:e_op=10;
    11:e_op=11;
    12:e_op=12;
    13:e_op=13;
    14:e_op=13;
    15:e_op=11;
    16:e_op=14;
    17:e_op=15;
    18:e_op=0;
    19:e_op=0;
    20:e_op=13;
    21:e_op=9;
    default:e_op=0;endcase end endfunction
  function automatic integer e_shift;input integer index;begin case(index)
    0:e_shift=0;
    1:e_shift=0;
    2:e_shift=1;
    3:e_shift=1;
    4:e_shift=0;
    5:e_shift=0;
    6:e_shift=0;
    7:e_shift=3;
    8:e_shift=1;
    9:e_shift=10;
    10:e_shift=1;
    11:e_shift=0;
    12:e_shift=31;
    13:e_shift=1;
    14:e_shift=1;
    15:e_shift=0;
    16:e_shift=0;
    17:e_shift=0;
    18:e_shift=0;
    19:e_shift=0;
    20:e_shift=1;
    21:e_shift=10;
    default:e_shift=0;endcase end endfunction
  function automatic integer e_count;input integer index;begin case(index)
    0:e_count=8;
    1:e_count=8;
    2:e_count=8;
    3:e_count=8;
    4:e_count=8;
    5:e_count=8;
    6:e_count=8;
    7:e_count=5;
    8:e_count=4;
    9:e_count=4;
    10:e_count=4;
    11:e_count=3;
    12:e_count=5;
    13:e_count=4;
    14:e_count=3;
    15:e_count=3;
    16:e_count=8;
    17:e_count=8;
    18:e_count=0;
    19:e_count=9;
    20:e_count=5;
    21:e_count=3;
    default:e_count=0;endcase end endfunction
  function automatic [127:0] e_a;input integer index;begin case(index)
    0:e_a=128'h0003000200010000fffc000480087ff8;
    1:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    2:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    3:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    4:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    5:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    6:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    7:e_a=128'h8000800080000ffffffd00031000f000;
    8:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    9:e_a=128'hff85007b80007fff0190fed400c80064;
    10:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    11:e_a=128'h800080008000800080000000ffff8000;
    12:e_a=128'h8000800080000080007f0000ff80ff7f;
    13:e_a=128'hfffeffff00010001fffffffd00000003;
    14:e_a=128'h800000000000fffafffffffd00000003;
    15:e_a=128'h800080008000800080000003fffe0001;
    16:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    17:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    18:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    19:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    20:e_a=128'h800000000000fffafffffffd00000003;
    21:e_a=128'h80007ffffe38007bfffb0005fffd0003;
    default:e_a=0;endcase end endfunction
  function automatic [127:0] e_b;input integer index;begin case(index)
    0:e_b=128'h00030002000100000004fffcffec0014;
    1:e_b=128'h007f007ffffefffe0003000300010001;
    2:e_b=128'h007f007ffffefffe0003000300010001;
    3:e_b=128'h007f007ffffefffe0003000300010001;
    4:e_b=128'h007f007ffffefffe0003000300010001;
    5:e_b=128'h007f007ffffefffe0003000300010001;
    6:e_b=128'h007f007ffffefffe0003000300010001;
    7:e_b=128'h007f007ffffefffe0003000300010001;
    8:e_b=128'h007f007ffffefffe0003000300010001;
    9:e_b=128'hfff4000c80007fff0400000000000400;
    10:e_b=128'h007f007ffffefffe0003000300010001;
    11:e_b=128'h007f007ffffefffe0003000300010001;
    12:e_b=128'h007f007ffffefffe0003000300010001;
    13:e_b=128'h007f007ffffefffe0003000300010001;
    14:e_b=128'h007f007ffffefffe0003000300010001;
    15:e_b=128'h007f007ffffefffe0003000300010001;
    16:e_b=128'h007f007ffffefffe0003000300010001;
    17:e_b=128'h007f007ffffefffe0003000300010001;
    18:e_b=128'h007f007ffffefffe0003000300010001;
    19:e_b=128'h007f007ffffefffe0003000300010001;
    20:e_b=128'h007f007ffffefffe0003000300010001;
    21:e_b=128'h007f007ffffefffe0003000300010001;
    default:e_b=0;endcase end endfunction
  function automatic [127:0] e_c;input integer index;begin case(index)
    0:e_c=128'hffff000100030003ffff000100000000;
    1:e_c=128'hffff000100030003ffff000100000000;
    2:e_c=128'hffff000100030003ffff000100000000;
    3:e_c=128'hffff000100030003ffff000100000000;
    4:e_c=128'hffff000100030003ffff000100000000;
    5:e_c=128'hffff000100030003ffff000100000000;
    6:e_c=128'hffff000100030003ffff000100000000;
    7:e_c=128'hffff000100030003ffff000100000000;
    8:e_c=128'hffff000100030003ffff000100000000;
    9:e_c=128'hffff000100030003ffff000100000000;
    10:e_c=128'hffff000100030003ffff000100000000;
    11:e_c=128'hffff000100030003ffff000100000000;
    12:e_c=128'hffff000100030003ffff000100000000;
    13:e_c=128'hffff000100030003ffff000100000000;
    14:e_c=128'hffff000100030003ffff000100000000;
    15:e_c=128'hffff000100030003ffff000100000000;
    16:e_c=128'hffff000100030003ffff000100000000;
    17:e_c=128'hffff000100030003ffff000100000000;
    18:e_c=128'hffff000100030003ffff000100000000;
    19:e_c=128'hffff000100030003ffff000100000000;
    20:e_c=128'hffff000100030003ffff000100000000;
    21:e_c=128'hffff000100030003ffff000100000000;
    default:e_c=0;endcase end endfunction
  function automatic [127:0] e_mask_a;input integer index;begin case(index)
    0:e_mask_a=128'h0003000200010000fffc000480087ff8;
    1:e_mask_a=128'h80007ffffe38007bfffb0005fffd0003;
    2:e_mask_a=128'h80007ffffe38007bfffb0005fffd0003;
    3:e_mask_a=128'h80007ffffe38007bfffb0005fffd0003;
    4:e_mask_a=128'h80007ffffe38007bfffb0005fffd0003;
    5:e_mask_a=128'h80007ffffe38007bfffb0005fffd0003;
    6:e_mask_a=128'h80007ffffe38007bfffb0005fffd0003;
    7:e_mask_a=128'h0000000000000ffffffd00031000f000;
    8:e_mask_a=128'h0000000000000000fffb0005fffd0003;
    9:e_mask_a=128'h00000000000000000190fed400c80064;
    10:e_mask_a=128'h0000000000000000fffb0005fffd0003;
    11:e_mask_a=128'h000000000000000000000000ffff8000;
    12:e_mask_a=128'h0000000000000080007f0000ff80ff7f;
    13:e_mask_a=128'hfffeffff00010001fffffffd00000003;
    14:e_mask_a=128'h000000000000fffafffffffd00000003;
    15:e_mask_a=128'h000000000000000000000003fffe0001;
    16:e_mask_a=128'h80007ffffe38007bfffb0005fffd0003;
    17:e_mask_a=128'h80007ffffe38007bfffb0005fffd0003;
    18:e_mask_a=128'h00000000000000000000000000000000;
    19:e_mask_a=128'h80007ffffe38007bfffb0005fffd0003;
    20:e_mask_a=128'h800000000000fffafffffffd00000003;
    21:e_mask_a=128'h000000000000000000000005fffd0003;
    default:e_mask_a=0;endcase end endfunction
  function automatic [127:0] e_mask_b;input integer index;begin case(index)
    0:e_mask_b=128'h00030002000100000004fffcffec0014;
    1:e_mask_b=128'h007f007ffffefffe0003000300010001;
    2:e_mask_b=128'h007f007ffffefffe0003000300010001;
    3:e_mask_b=128'h007f007ffffefffe0003000300010001;
    4:e_mask_b=128'h007f007ffffefffe0003000300010001;
    5:e_mask_b=128'h007f007ffffefffe0003000300010001;
    6:e_mask_b=128'h007f007ffffefffe0003000300010001;
    7:e_mask_b=128'h00000000000000000000000000000000;
    8:e_mask_b=128'h00000000000000000000000000000000;
    9:e_mask_b=128'h00000000000000000400000000000400;
    10:e_mask_b=128'h00000000000000000000000000000000;
    11:e_mask_b=128'h00000000000000000000000000000000;
    12:e_mask_b=128'h00000000000000000000000000000000;
    13:e_mask_b=128'h00000000000000000000000000000000;
    14:e_mask_b=128'h00000000000000000000000000000000;
    15:e_mask_b=128'h00000000000000000000000000000000;
    16:e_mask_b=128'h00000000000000000000000000000000;
    17:e_mask_b=128'h00000000000000000000000000000000;
    18:e_mask_b=128'h00000000000000000000000000000000;
    19:e_mask_b=128'h007f007ffffefffe0003000300010001;
    20:e_mask_b=128'h00000000000000000000000000000000;
    21:e_mask_b=128'h00000000000000000000000300010001;
    default:e_mask_b=0;endcase end endfunction
  function automatic [127:0] e_mask_c;input integer index;begin case(index)
    0:e_mask_c=128'h00000000000000000000000000000000;
    1:e_mask_c=128'h00000000000000000000000000000000;
    2:e_mask_c=128'h00000000000000000000000000000000;
    3:e_mask_c=128'hffff000100030003ffff000100000000;
    4:e_mask_c=128'h00000000000000000000000000000000;
    5:e_mask_c=128'h00000000000000000000000000000000;
    6:e_mask_c=128'hffff000100030003ffff000100000000;
    7:e_mask_c=128'h00000000000000000000000000000000;
    8:e_mask_c=128'h00000000000000000000000000000000;
    9:e_mask_c=128'h00000000000000000000000000000000;
    10:e_mask_c=128'h00000000000000000000000000000000;
    11:e_mask_c=128'h00000000000000000000000000000000;
    12:e_mask_c=128'h00000000000000000000000000000000;
    13:e_mask_c=128'h00000000000000000000000000000000;
    14:e_mask_c=128'h00000000000000000000000000000000;
    15:e_mask_c=128'h00000000000000000000000000000000;
    16:e_mask_c=128'h00000000000000000000000000000000;
    17:e_mask_c=128'h00000000000000000000000000000000;
    18:e_mask_c=128'h00000000000000000000000000000000;
    19:e_mask_c=128'h00000000000000000000000000000000;
    20:e_mask_c=128'h00000000000000000000000000000000;
    21:e_mask_c=128'h00000000000000000000000000000000;
    default:e_mask_c=0;endcase end endfunction
  function automatic [127:0] e_expected;input integer index;begin case(index)
    0:e_expected=128'h00060004000200000000000080007fff;
    1:e_expected=128'h80007f80fe3a007dfff80002fffc0002;
    2:e_expected=128'h80007fff01c8ff85fff80008fffe0002;
    3:e_expected=128'h80007fff01caff86fff80008fffe0002;
    4:e_expected=128'h007f7ffffffe007b0003000500010003;
    5:e_expected=128'h8000007ffe38fffefffb0003fffd0001;
    6:e_expected=128'h80007ffffe38007bfffb000500010001;
    7:e_expected=128'h0000000000007ff8ffe800187fff8000;
    8:e_expected=128'h0000000000000000fffd0002fffe0001;
    9:e_expected=128'h0000000000000000fed4fe7000c80064;
    10:e_expected=128'h0000000000000000fffe0002fffe0002;
    11:e_expected=128'h00000000000000000000000000017fff;
    12:e_expected=128'h00000000000000000000007f7f008080;
    13:e_expected=128'h000000000000000080007ffffffe0002;
    14:e_expected=128'h000000000000000000007ffdfffe0002;
    15:e_expected=128'h00000000000000000000000300020001;
    16:e_expected=128'h00000000000000000000000000000000;
    17:e_expected=128'h00000000000000000000000000000000;
    18:e_expected=128'h00000000000000000000000000000000;
    19:e_expected=128'h00000000000000000000000000000000;
    20:e_expected=128'h00000000000000000000000000000000;
    21:e_expected=128'h00000000000000000000000000000000;
    default:e_expected=0;endcase end endfunction
  function automatic integer e_error;input integer index;begin case(index)
    0:e_error=0;
    1:e_error=0;
    2:e_error=0;
    3:e_error=0;
    4:e_error=0;
    5:e_error=0;
    6:e_error=0;
    7:e_error=0;
    8:e_error=0;
    9:e_error=0;
    10:e_error=0;
    11:e_error=0;
    12:e_error=0;
    13:e_error=0;
    14:e_error=0;
    15:e_error=0;
    16:e_error=1;
    17:e_error=1;
    18:e_error=1;
    19:e_error=1;
    20:e_error=1;
    21:e_error=1;
    default:e_error=0;endcase end endfunction
  function automatic integer e_sat;input integer index;begin case(index)
    0:e_sat=1;
    1:e_sat=1;
    2:e_sat=1;
    3:e_sat=1;
    4:e_sat=0;
    5:e_sat=0;
    6:e_sat=0;
    7:e_sat=1;
    8:e_sat=0;
    9:e_sat=0;
    10:e_sat=0;
    11:e_sat=1;
    12:e_sat=1;
    13:e_sat=1;
    14:e_sat=0;
    15:e_sat=0;
    16:e_sat=0;
    17:e_sat=0;
    18:e_sat=0;
    19:e_sat=0;
    20:e_sat=0;
    21:e_sat=0;
    default:e_sat=0;endcase end endfunction
  function automatic integer e_reads;input integer index;begin case(index)
    0:e_reads=2;
    1:e_reads=2;
    2:e_reads=2;
    3:e_reads=3;
    4:e_reads=2;
    5:e_reads=2;
    6:e_reads=3;
    7:e_reads=1;
    8:e_reads=1;
    9:e_reads=2;
    10:e_reads=1;
    11:e_reads=1;
    12:e_reads=1;
    13:e_reads=1;
    14:e_reads=1;
    15:e_reads=1;
    16:e_reads=1;
    17:e_reads=1;
    18:e_reads=0;
    19:e_reads=0;
    20:e_reads=0;
    21:e_reads=0;
    default:e_reads=0;endcase end endfunction
  function automatic integer e_native;input integer index;begin case(index)
    0:e_native=1;
    1:e_native=1;
    2:e_native=1;
    3:e_native=1;
    4:e_native=1;
    5:e_native=1;
    6:e_native=1;
    7:e_native=1;
    8:e_native=1;
    9:e_native=1;
    10:e_native=1;
    11:e_native=1;
    12:e_native=1;
    13:e_native=1;
    14:e_native=1;
    15:e_native=1;
    16:e_native=1;
    17:e_native=1;
    18:e_native=0;
    19:e_native=0;
    20:e_native=0;
    21:e_native=0;
    default:e_native=0;endcase end endfunction
  function automatic [8*100-1:0] e_name;input integer index;begin case(index)
    0:e_name="W3_E_ADD_SAT";
    1:e_name="W3_E_SUB";
    2:e_name="W3_E_MUL_RNE";
    3:e_name="W3_E_FMA_PRODUCT_UNITS";
    4:e_name="W3_E_MAX";
    5:e_name="W3_E_MIN";
    6:e_name="W3_E_SELECT_THIRD_OPERAND";
    7:e_name="W3_E_LEFT_SAT";
    8:e_name="W3_E_ASR_NOT_RNE";
    9:e_name="W3_E_ROPE_PAIRS";
    10:e_name="W3_E_RNE_COPY";
    11:e_name="W3_E_ABS_SAT";
    12:e_name="W3_E_PACK_S8_SHIFT_IGNORED";
    13:e_name="W3_E_CAST_S32_RNE_CLIP";
    14:e_name="W3_E_CAST_S32_TAIL_MASK";
    15:e_name="W3_E_TAIL_MASK_PREVENTS_FALSE_SAT";
    16:e_name="W3_E_NATIVE_INVALID14_NO_WRITE";
    17:e_name="W3_E_NATIVE_INVALID15_NO_WRITE";
    18:e_name="W3_E_INVALID_COUNT0";
    19:e_name="W3_E_INVALID_COUNT9";
    20:e_name="W3_E_INVALID_CAST_COUNT5";
    21:e_name="W3_E_INVALID_ROPE_ODD_COUNT";
    default:e_name="BAD";endcase end endfunction
  function automatic integer g_fn;input integer index;begin case(index)
    0:g_fn=0;
    1:g_fn=0;
    2:g_fn=1;
    3:g_fn=1;
    4:g_fn=2;
    5:g_fn=2;
    6:g_fn=3;
    7:g_fn=3;
    8:g_fn=0;
    9:g_fn=3;
    10:g_fn=4;
    11:g_fn=7;
    12:g_fn=0;
    13:g_fn=0;
    default:g_fn=0;endcase end endfunction
  function automatic integer g_gated;input integer index;begin case(index)
    0:g_gated=0;
    1:g_gated=1;
    2:g_gated=0;
    3:g_gated=1;
    4:g_gated=0;
    5:g_gated=1;
    6:g_gated=0;
    7:g_gated=1;
    8:g_gated=1;
    9:g_gated=0;
    10:g_gated=1;
    11:g_gated=0;
    12:g_gated=1;
    13:g_gated=1;
    default:g_gated=0;endcase end endfunction
  function automatic integer g_count;input integer index;begin case(index)
    0:g_count=8;
    1:g_count=8;
    2:g_count=8;
    3:g_count=8;
    4:g_count=8;
    5:g_count=8;
    6:g_count=8;
    7:g_count=8;
    8:g_count=5;
    9:g_count=1;
    10:g_count=8;
    11:g_count=1;
    12:g_count=0;
    13:g_count=9;
    default:g_count=0;endcase end endfunction
  function automatic [127:0] g_a;input integer index;begin case(index)
    0:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    1:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    2:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    3:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    4:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    5:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    6:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    7:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    8:g_a=128'h7fff80007fffffc0ffe0004000200000;
    9:g_a=128'h80008000800080008000800080000000;
    10:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    11:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    12:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    13:g_a=128'h7fff20000000ffffe000dfffbfff8000;
    default:g_a=0;endcase end endfunction
  function automatic [127:0] g_b;input integer index;begin case(index)
    0:g_b=128'hc00040000001ffff0400fc007fff8000;
    1:g_b=128'hc00040000001ffff0400fc007fff8000;
    2:g_b=128'hc00040000001ffff0400fc007fff8000;
    3:g_b=128'hc00040000001ffff0400fc007fff8000;
    4:g_b=128'hc00040000001ffff0400fc007fff8000;
    5:g_b=128'hc00040000001ffff0400fc007fff8000;
    6:g_b=128'hc00040000001ffff0400fc007fff8000;
    7:g_b=128'hc00040000001ffff0400fc007fff8000;
    8:g_b=128'h04000400040004000400040004000400;
    9:g_b=128'hc00040000001ffff0400fc007fff8000;
    10:g_b=128'hc00040000001ffff0400fc007fff8000;
    11:g_b=128'hc00040000001ffff0400fc007fff8000;
    12:g_b=128'hc00040000001ffff0400fc007fff8000;
    13:g_b=128'hc00040000001ffff0400fc007fff8000;
    default:g_b=0;endcase end endfunction
  function automatic [127:0] g_mask_a;input integer index;begin case(index)
    0:g_mask_a=128'h7fff20000000ffffe000dfffbfff8000;
    1:g_mask_a=128'h7fff20000000ffffe000dfffbfff8000;
    2:g_mask_a=128'h7fff20000000ffffe000dfffbfff8000;
    3:g_mask_a=128'h7fff20000000ffffe000dfffbfff8000;
    4:g_mask_a=128'h7fff20000000ffffe000dfffbfff8000;
    5:g_mask_a=128'h7fff20000000ffffe000dfffbfff8000;
    6:g_mask_a=128'h7fff20000000ffffe000dfffbfff8000;
    7:g_mask_a=128'h7fff20000000ffffe000dfffbfff8000;
    8:g_mask_a=128'h000000000000ffc0ffe0004000200000;
    9:g_mask_a=128'h00000000000000000000000000000000;
    10:g_mask_a=128'h7fff20000000ffffe000dfffbfff8000;
    11:g_mask_a=128'h00000000000000000000000000008000;
    12:g_mask_a=128'h00000000000000000000000000000000;
    13:g_mask_a=128'h7fff20000000ffffe000dfffbfff8000;
    default:g_mask_a=0;endcase end endfunction
  function automatic [127:0] g_mask_b;input integer index;begin case(index)
    0:g_mask_b=128'h00000000000000000000000000000000;
    1:g_mask_b=128'hc00040000001ffff0400fc007fff8000;
    2:g_mask_b=128'h00000000000000000000000000000000;
    3:g_mask_b=128'hc00040000001ffff0400fc007fff8000;
    4:g_mask_b=128'h00000000000000000000000000000000;
    5:g_mask_b=128'hc00040000001ffff0400fc007fff8000;
    6:g_mask_b=128'h00000000000000000000000000000000;
    7:g_mask_b=128'hc00040000001ffff0400fc007fff8000;
    8:g_mask_b=128'h00000000000004000400040004000400;
    9:g_mask_b=128'h00000000000000000000000000000000;
    10:g_mask_b=128'hc00040000001ffff0400fc007fff8000;
    11:g_mask_b=128'h00000000000000000000000000000000;
    12:g_mask_b=128'h00000000000000000000000000000000;
    13:g_mask_b=128'hc00040000001ffff0400fc007fff8000;
    default:g_mask_b=0;endcase end endfunction
  function automatic [127:0] g_expected;input integer index;begin case(index)
    0:g_expected=128'h7fff1ffd00000000fffd000000000000;
    1:g_expected=128'h80007fff00000000fffd000000000000;
    2:g_expected=128'h40003ffb20001ffc0005000000000000;
    3:g_expected=128'hc0003ffb000000000000000000000000;
    4:g_expected=128'h7fff2000000000000000000000000000;
    5:g_expected=128'h80007fff000000000000000000000000;
    6:g_expected=128'h7fff200002c602c60000000000000000;
    7:g_expected=128'h80007fff0001ffff0000000000000000;
    8:g_expected=128'h000000000000ffe1fff0002100100000;
    9:g_expected=128'h000000000000000000000000000002c6;
    10:g_expected=128'h00000000000000000000000000000000;
    11:g_expected=128'h00000000000000000000000000000000;
    12:g_expected=128'h00000000000000000000000000000000;
    13:g_expected=128'h00000000000000000000000000000000;
    default:g_expected=0;endcase end endfunction
  function automatic integer g_error;input integer index;begin case(index)
    0:g_error=0;
    1:g_error=0;
    2:g_error=0;
    3:g_error=0;
    4:g_error=0;
    5:g_error=0;
    6:g_error=0;
    7:g_error=0;
    8:g_error=0;
    9:g_error=0;
    10:g_error=1;
    11:g_error=1;
    12:g_error=1;
    13:g_error=1;
    default:g_error=0;endcase end endfunction
  function automatic integer g_sat;input integer index;begin case(index)
    0:g_sat=0;
    1:g_sat=1;
    2:g_sat=0;
    3:g_sat=0;
    4:g_sat=0;
    5:g_sat=1;
    6:g_sat=0;
    7:g_sat=1;
    8:g_sat=0;
    9:g_sat=0;
    10:g_sat=0;
    11:g_sat=0;
    12:g_sat=0;
    13:g_sat=0;
    default:g_sat=0;endcase end endfunction
  function automatic integer g_reads;input integer index;begin case(index)
    0:g_reads=1;
    1:g_reads=2;
    2:g_reads=1;
    3:g_reads=2;
    4:g_reads=1;
    5:g_reads=2;
    6:g_reads=1;
    7:g_reads=2;
    8:g_reads=2;
    9:g_reads=1;
    10:g_reads=2;
    11:g_reads=1;
    12:g_reads=0;
    13:g_reads=0;
    default:g_reads=0;endcase end endfunction
  function automatic integer g_pairs;input integer index;begin case(index)
    0:g_pairs=4;
    1:g_pairs=4;
    2:g_pairs=4;
    3:g_pairs=4;
    4:g_pairs=4;
    5:g_pairs=4;
    6:g_pairs=4;
    7:g_pairs=4;
    8:g_pairs=3;
    9:g_pairs=1;
    10:g_pairs=4;
    11:g_pairs=1;
    12:g_pairs=0;
    13:g_pairs=0;
    default:g_pairs=0;endcase end endfunction
  function automatic [8*100-1:0] g_name;input integer index;begin case(index)
    0:g_name="W3_G_FN0_GATED0";
    1:g_name="W3_G_FN0_GATED1";
    2:g_name="W3_G_FN1_GATED0";
    3:g_name="W3_G_FN1_GATED1";
    4:g_name="W3_G_FN2_GATED0";
    5:g_name="W3_G_FN2_GATED1";
    6:g_name="W3_G_FN3_GATED0";
    7:g_name="W3_G_FN3_GATED1";
    8:g_name="W3_G_ODD5_GATED_TAIL";
    9:g_name="W3_G_SINGLE_SOFTPLUS_TAIL";
    10:g_name="W3_G_NATIVE_INVALID4_DRAIN";
    11:g_name="W3_G_NATIVE_INVALID7_SINGLE";
    12:g_name="W3_G_INVALID_COUNT0";
    13:g_name="W3_G_INVALID_COUNT9";
    default:g_name="BAD";endcase end endfunction

  reg clk=0;always #5 clk=~clk;
  reg reset=1;reg [1:0] owner=0;
  reg allow_mem_req=1,allow_mem_rsp=1,allow_native_ack=1,allow_e_input=1,allow_e_output=1,allow_g_input=1,allow_g_output=1;
  reg host_valid=0,host_write=1,host_rsp_ready=0;reg [9:0] host_addr=0;reg [127:0] host_data=0;
  reg e_req_valid=0,e_rsp_ready=0;wire e_req_ready,e_rsp_valid,e_rsp_error,e_rsp_saturated;
  reg [3:0] e_req_op=0,e_req_count=0;reg [4:0] e_req_shift=0;
  reg [9:0] e_req_src_a=700,e_req_src_b=701,e_req_src_c=702,e_req_dst=703;
  reg g_req_valid=0,g_rsp_ready=0,g_req_gated=0;wire g_req_ready,g_rsp_valid,g_rsp_error,g_rsp_saturated;
  reg [2:0] g_req_fn=0;reg [3:0] g_req_count=0;reg [9:0] g_req_src_a=700,g_req_src_b=701,g_req_dst=703;
  wire ev,er,ew,erv,err,ere;wire [9:0] ea;wire [127:0] ed,erd;
  wire gv,gr,gw,grv,grr,gre;wire [9:0] ga;wire [127:0] gd,grd;
  wire h_req_valid,h_req_ready,h_req_write,h_rsp_valid,h_rsp_ready,h_rsp_error;wire [9:0] h_req_addr;wire [127:0] h_req_data,h_rsp_data;
  wire s_req,s_we,s_ready,s_valid,s_take,helper_take;wire [9:0] s_addr;wire [127:0] s_din,s_dout;
  wire ein_valid,ein_ready,ein_leaf_ready,eout_leaf_valid,eout_ready,eout_error,eout_sat;wire [3:0] ein_op;wire [4:0] ein_shift;wire [127:0] ein_a,ein_b,ein_c,eout_data;
  wire gin_valid,gin_ready,gin_leaf_ready,gin_gated,gout_leaf_valid,gout_ready,gout_error,gout_sat;wire [2:0] gin_fn;wire [31:0] gin_x,gin_gate,gout_data;
  assign h_req_valid=!reset&&allow_mem_req&&(owner==1?ev:owner==2?gv:host_valid);
  assign h_req_write=owner==1?ew:owner==2?gw:host_write;
  assign h_req_addr=owner==1?ea:owner==2?ga:host_addr;
  assign h_req_data=owner==1?ed:owner==2?gd:host_data;
  assign er=!reset&&owner==1&&allow_mem_req&&h_req_ready;
  assign gr=!reset&&owner==2&&allow_mem_req&&h_req_ready;
  assign erv=!reset&&owner==1&&allow_mem_rsp&&h_rsp_valid;
  assign grv=!reset&&owner==2&&allow_mem_rsp&&h_rsp_valid;
  assign erd=h_rsp_data;assign grd=h_rsp_data;assign ere=h_rsp_error;assign gre=h_rsp_error;
  assign h_rsp_ready=!reset&&allow_mem_rsp&&(owner==1?err:owner==2?grr:host_rsp_ready);
  assign s_take=helper_take&&allow_native_ack;
  block_p2_s_ctrl u_helper(.clk(clk),.resetn(!reset),.req_valid(h_req_valid),.req_ready(h_req_ready),.req_write(h_req_write),.req_addr(h_req_addr),.req_data(h_req_data),.rsp_valid(h_rsp_valid),.rsp_ready(h_rsp_ready),.rsp_data(h_rsp_data),.rsp_error(h_rsp_error),.s_req(s_req),.s_we(s_we),.s_addr(s_addr),.s_din(s_din),.s_rsp_ready(helper_take),.s_ready(s_ready),.s_rsp_valid(s_valid&&allow_native_ack),.s_dout(s_dout));
  block_feed_s16k u_s(.clk(clk),.reset(reset),.req(s_req),.wr(s_we),.addr(s_addr),.din(s_din),.ready(s_ready),.valid(s_valid),.take(s_take),.dout(s_dout),.wide_req(1'b0),.wide_addr(8'd0),.wide_ready(),.wide_valid(),.wide_take(1'b1),.wide_dout());
  block_w3_e_ctrl u_e_ctrl(.clk(clk),.reset(reset),.req_valid(e_req_valid),.req_ready(e_req_ready),.req_op(e_req_op),.req_shift(e_req_shift),.req_count(e_req_count),.req_src_a(e_req_src_a),.req_src_b(e_req_src_b),.req_src_c(e_req_src_c),.req_dst(e_req_dst),.rsp_valid(e_rsp_valid),.rsp_ready(e_rsp_ready),.rsp_error(e_rsp_error),.rsp_saturated(e_rsp_saturated),.mem_req_valid(ev),.mem_req_ready(er),.mem_req_write(ew),.mem_req_addr(ea),.mem_req_data(ed),.mem_rsp_valid(erv),.mem_rsp_ready(err),.mem_rsp_data(erd),.mem_rsp_error(ere),.e_in_valid(ein_valid),.e_in_ready(ein_ready),.e_in_op(ein_op),.e_in_shift(ein_shift),.e_in_a(ein_a),.e_in_b(ein_b),.e_in_c(ein_c),.e_out_valid(eout_leaf_valid&&allow_e_output),.e_out_ready(eout_ready),.e_out_data(eout_data),.e_out_error(eout_error),.e_out_saturated(eout_sat));
  assign ein_ready=ein_leaf_ready&&allow_e_input;
  block_v2_e u_e(.clk(clk),.reset(reset),.in_valid(ein_valid&&allow_e_input),.in_ready(ein_leaf_ready),.in_op(ein_op),.in_shift(ein_shift),.in_a(ein_a),.in_b(ein_b),.in_c(ein_c),.out_valid(eout_leaf_valid),.out_ready(eout_ready&&allow_e_output),.out_data(eout_data),.out_error(eout_error),.out_saturated(eout_sat));
  block_w3_g_ctrl u_g_ctrl(.clk(clk),.reset(reset),.req_valid(g_req_valid),.req_ready(g_req_ready),.req_fn(g_req_fn),.req_gated(g_req_gated),.req_count(g_req_count),.req_src_a(g_req_src_a),.req_src_b(g_req_src_b),.req_dst(g_req_dst),.rsp_valid(g_rsp_valid),.rsp_ready(g_rsp_ready),.rsp_error(g_rsp_error),.rsp_saturated(g_rsp_saturated),.mem_req_valid(gv),.mem_req_ready(gr),.mem_req_write(gw),.mem_req_addr(ga),.mem_req_data(gd),.mem_rsp_valid(grv),.mem_rsp_ready(grr),.mem_rsp_data(grd),.mem_rsp_error(gre),.g_in_valid(gin_valid),.g_in_ready(gin_ready),.g_in_fn(gin_fn),.g_in_gated(gin_gated),.g_in_x(gin_x),.g_in_gate(gin_gate),.g_out_valid(gout_leaf_valid&&allow_g_output),.g_out_ready(gout_ready),.g_out_data(gout_data),.g_out_error(gout_error),.g_out_saturated(gout_sat));
  assign gin_ready=gin_leaf_ready&&allow_g_input;
  block_v2_g u_g(.clk(clk),.reset(reset),.in_valid(gin_valid&&allow_g_input),.in_ready(gin_leaf_ready),.in_fn(gin_fn),.in_gated(gin_gated),.in_x(gin_x),.in_gate(gin_gate),.out_valid(gout_leaf_valid),.out_ready(gout_ready&&allow_g_output),.out_data(gout_data),.out_error(gout_error),.out_saturated(gout_sat));

  localparam [127:0] POISON=128'hdeadbeef0123456789abcdeffeedface;
  integer cycles=0,cases=0,ci=0,memreads=0,memwrites=0,memacks=0,native_e=0,native_g=0,retired_g=0;
  integer qr0,qw0,qa0,ne0,ng0,rg0,max_flight=0;
  reg service_active=0,pending=0,pending_write;reg [127:0] pending_data;reg [9:0] pending_addr;
  reg sehold=0,sghold=0,memhold=0,eouthold=0,gouthold=0,sackhold=0;
  reg [4:0] peshift;reg [3:0] peop;reg [127:0] pea,peb,pec,pmdata,peout,psack;reg [9:0] pmaddr;reg pmwrite;
  reg [31:0] pgx,pggate,pgout;reg [2:0] pgfn;reg pggated,peerr,pesat,pgerr,pgsat;
  function automatic [127:0] ram703;
    input dummy;begin ram703=u_s.bank3[175];end
  endfunction
  always @(posedge clk)begin
    cycles=cycles+1;if(cycles>200000)$fatal(1,"FAIL_W3_ADAPTER watchdog");
    if(reset)begin pending=0;sehold=0;sghold=0;memhold=0;eouthold=0;gouthold=0;sackhold=0;end
    else begin
      if(sehold&&(!ein_valid||ein_op!==peop||ein_shift!==peshift||ein_a!==pea||ein_b!==peb||ein_c!==pec))$fatal(1,"FAIL_W3_ADAPTER E input hold");
      if(sghold&&(!gin_valid||gin_fn!==pgfn||gin_gated!==pggated||gin_x!==pgx||gin_gate!==pggate))$fatal(1,"FAIL_W3_ADAPTER G input hold");
      if(memhold&&(!(owner==1?ev:owner==2?gv:host_valid)||h_req_write!==pmwrite||h_req_addr!==pmaddr||h_req_data!==pmdata))$fatal(1,"FAIL_W3_ADAPTER helper request hold");
      if(eouthold&&(!eout_leaf_valid||eout_data!==peout||eout_error!==peerr||eout_sat!==pesat))$fatal(1,"FAIL_W3_ADAPTER native E output hold");
      if(gouthold&&(!gout_leaf_valid||gout_data!==pgout||gout_error!==pgerr||gout_sat!==pgsat))$fatal(1,"FAIL_W3_ADAPTER native G pipeline freeze");
      if(sackhold&&(!s_valid||s_dout!==psack))$fatal(1,"FAIL_W3_ADAPTER native write ACK hold");
      sehold=ein_valid&&!ein_ready;peop=ein_op;peshift=ein_shift;pea=ein_a;peb=ein_b;pec=ein_c;
      sghold=gin_valid&&!gin_ready;pgfn=gin_fn;pggated=gin_gated;pgx=gin_x;pggate=gin_gate;
      memhold=(owner==1?ev:owner==2?gv:host_valid)&&!(allow_mem_req&&h_req_ready);pmwrite=h_req_write;pmaddr=h_req_addr;pmdata=h_req_data;
      eouthold=eout_leaf_valid&&!(eout_ready&&allow_e_output);peout=eout_data;peerr=eout_error;pesat=eout_sat;
      gouthold=gout_leaf_valid&&!(gout_ready&&allow_g_output);pgout=gout_data;pgerr=gout_error;pgsat=gout_sat;
      sackhold=s_valid&&!s_take;psack=s_dout;
      if(s_req&&s_ready)begin
        if(pending)$fatal(1,"FAIL_W3_ADAPTER two S requests");pending=1;pending_write=s_we;pending_addr=s_addr;pending_data=s_din;
        if(service_active)begin
          if(s_we)begin
            if(s_addr!=703||s_din!==(owner==1?e_expected(ci):g_expected(ci)))$fatal(1,"FAIL_W3_ADAPTER wrong result write owner%0d case%0d got%032h",owner,ci,s_din);
            memwrites=memwrites+1;
          end else begin
            if(s_addr!==700+(memreads-qr0))$fatal(1,"FAIL_W3_ADAPTER operand mask/read order");memreads=memreads+1;
          end
        end
      end
      if(s_valid&&s_take)begin
        if(!pending)$fatal(1,"FAIL_W3_ADAPTER ACK without ownership");
        if(pending_write&&s_dout!==pending_data)$fatal(1,"FAIL_W3_ADAPTER write ACK echo");pending=0;if(service_active)memacks=memacks+1;
      end
      if(ein_valid&&ein_ready)begin
        if(owner!=1||ein_op!==e_op(ci)||ein_shift!==e_shift(ci)||ein_a!==e_mask_a(ci)||ein_b!==e_mask_b(ci)||ein_c!==e_mask_c(ci))$fatal(1,"FAIL_W3_ADAPTER E gather/mask/req capture");native_e=native_e+1;
      end
      if(gin_valid&&gin_ready)begin
        if(owner!=2||gin_fn!==g_fn(ci)||gin_gated!==g_gated(ci)||gin_x!==32'(g_mask_a(ci)>>(32*(native_g-ng0)))||gin_gate!==32'(g_mask_b(ci)>>(32*(native_g-ng0))))$fatal(1,"FAIL_W3_ADAPTER G lane/tail/gate capture");native_g=native_g+1;
      end
      if(gout_leaf_valid&&gout_ready&&allow_g_output)retired_g=retired_g+1;
      if(native_g-ng0-(retired_g-rg0)>max_flight)max_flight=native_g-ng0-(retired_g-rg0);
      if(service_active&&((owner==1&&e_rsp_valid&&!e_rsp_error)||(owner==2&&g_rsp_valid&&!g_rsp_error)))begin
        if(memwrites-qw0!=1||memacks-qa0!=(memreads-qr0)+1||pending)$fatal(1,"FAIL_W3_ADAPTER response before write ACK");
      end
    end
  end
  task automatic mark;
    input [8*100-1:0] name;begin cases=cases+1;$display("CASE_PASS %0s",name);end
  endtask
  task automatic store;
    input [9:0] addr;input [127:0] data;
    begin @(negedge clk);owner=0;host_addr=addr;host_data=data;host_valid=1;host_write=1;host_rsp_ready=0;
      while(!h_req_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);host_valid=0;
      while(!h_rsp_valid)@(negedge clk);if(h_rsp_data!==data||h_rsp_error)$fatal(1,"FAIL_W3_ADAPTER host init");
      host_rsp_ready=1;@(posedge clk);#1;@(negedge clk);host_rsp_ready=0;
    end
  endtask
  task automatic prepare;
    input integer which,index;
    begin
      ci=index;service_active=0;
      store(700,which==1?e_a(index):g_a(index));store(701,which==1?e_b(index):g_b(index));store(702,which==1?e_c(index):128'hbad);store(703,POISON);
      @(negedge clk);owner=which;qr0=memreads;qw0=memwrites;qa0=memacks;ne0=native_e;ng0=native_g;rg0=retired_g;max_flight=0;service_active=1;
    end
  endtask
  task automatic launch_e;
    begin @(negedge clk);e_req_op=e_op(ci);e_req_shift=e_shift(ci);e_req_count=e_count(ci);e_req_src_a=700;e_req_src_b=701;e_req_src_c=702;e_req_dst=703;e_req_valid=1;e_rsp_ready=0;
      while(!e_req_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);e_req_valid=0;
      // Upstream changes after handshake cannot alter the captured service.
      e_req_op=15;e_req_shift=31;e_req_count=0;e_req_src_a=999;e_req_src_b=998;e_req_src_c=997;e_req_dst=996;
    end
  endtask
  task automatic launch_g;
    begin @(negedge clk);g_req_fn=g_fn(ci);g_req_gated=g_gated(ci);g_req_count=g_count(ci);g_req_src_a=700;g_req_src_b=701;g_req_dst=703;g_req_valid=1;g_rsp_ready=0;
      while(!g_req_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);g_req_valid=0;
      g_req_fn=7;g_req_gated=0;g_req_count=0;g_req_src_a=999;g_req_src_b=998;g_req_dst=997;
    end
  endtask
  task automatic finish_e;
    integer j;
    begin while(!e_rsp_valid)@(negedge clk);
      for(j=0;j<5;j=j+1)begin if(!e_rsp_valid||e_rsp_error!==e_error(ci)||e_rsp_saturated!==e_sat(ci)||e_req_ready)$fatal(1,"FAIL_W3_ADAPTER E rsp flags/hold case%0d",ci);@(negedge clk);end
      if(memreads-qr0!=e_reads(ci)||native_e-ne0!=e_native(ci)||memwrites-qw0!=(e_error(ci)?0:1)||pending)$fatal(1,"FAIL_W3_ADAPTER E counts");
      if(ram703(0)!==(e_error(ci)?POISON:e_expected(ci)))$fatal(1,"FAIL_W3_ADAPTER E error overwrite/output");
      e_rsp_ready=1;@(posedge clk);#1;@(negedge clk);e_rsp_ready=0;service_active=0;owner=0;repeat(2)@(negedge clk);if(e_rsp_valid||!e_req_ready)$fatal(1,"FAIL_W3_ADAPTER E reuse");
    end
  endtask
  task automatic finish_g;
    integer j;
    begin while(!g_rsp_valid)@(negedge clk);
      for(j=0;j<5;j=j+1)begin if(!g_rsp_valid||g_rsp_error!==g_error(ci)||g_rsp_saturated!==g_sat(ci)||g_req_ready)$fatal(1,"FAIL_W3_ADAPTER G rsp flags/hold case%0d",ci);@(negedge clk);end
      if(memreads-qr0!=g_reads(ci)||native_g-ng0!=g_pairs(ci)||retired_g-rg0!=g_pairs(ci)||memwrites-qw0!=(g_error(ci)?0:1)||pending)$fatal(1,"FAIL_W3_ADAPTER G counts");
      if(ram703(0)!==(g_error(ci)?POISON:g_expected(ci)))$fatal(1,"FAIL_W3_ADAPTER G error overwrite/output");
      g_rsp_ready=1;@(posedge clk);#1;@(negedge clk);g_rsp_ready=0;service_active=0;owner=0;repeat(2)@(negedge clk);if(g_rsp_valid||!g_req_ready)$fatal(1,"FAIL_W3_ADAPTER G reuse");
    end
  endtask
  task automatic run_e;
    input integer index,stall;integer j;
    begin prepare(1,index);
      if(stall==1)allow_e_input=0;if(stall==2)allow_e_output=0;if(stall==4)allow_mem_req=0;
      launch_e();
      if(stall==1)begin while(!ein_valid)@(negedge clk);repeat(5)@(negedge clk);if(native_e!=ne0)$fatal(1,"FAIL_W3_ADAPTER E stalled native accepted");allow_e_input=1;end
      if(stall==2)begin while(!eout_leaf_valid)@(negedge clk);repeat(5)@(negedge clk);if(e_rsp_valid||memwrites!=qw0)$fatal(1,"FAIL_W3_ADAPTER E early output");allow_e_output=1;end
      if(stall==3)begin wait(ev&&ew);allow_native_ack=0;while(!s_valid)@(negedge clk);repeat(5)begin @(negedge clk);if(e_rsp_valid||ram703(0)!==e_expected(ci))$fatal(1,"FAIL_W3_ADAPTER E ACK gate");end allow_native_ack=1;end
      if(stall==4)begin repeat(5)@(negedge clk);allow_mem_req=1;allow_mem_rsp=0;while(!h_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);allow_mem_rsp=1;end
      finish_e();
    end
  endtask
  task automatic run_g;
    input integer index,stall;
    begin prepare(2,index);
      if(stall==1)allow_g_input=0;if(stall==2)allow_g_output=0;if(stall==4)allow_mem_req=0;
      launch_g();
      if(stall==1)begin while(!gin_valid)@(negedge clk);repeat(5)@(negedge clk);if(native_g!=ng0)$fatal(1,"FAIL_W3_ADAPTER G stalled input accepted");allow_g_input=1;end
      if(stall==2)begin while(!gout_leaf_valid)@(negedge clk);repeat(5)@(negedge clk);if(g_rsp_valid||memwrites!=qw0||max_flight<2)$fatal(1,"FAIL_W3_ADAPTER G did not hold multiple in-flight");allow_g_output=1;end
      if(stall==3)begin wait(gv&&gw);allow_native_ack=0;while(!s_valid)@(negedge clk);repeat(5)begin @(negedge clk);if(g_rsp_valid||ram703(0)!==g_expected(ci))$fatal(1,"FAIL_W3_ADAPTER G ACK gate");end allow_native_ack=1;end
      if(stall==4)begin repeat(5)@(negedge clk);allow_mem_req=1;allow_mem_rsp=0;while(!h_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);allow_mem_rsp=1;end
      finish_g();
    end
  endtask
  task automatic coordinated_reset;
    begin @(negedge clk);reset=1;e_req_valid=0;g_req_valid=0;host_valid=0;e_rsp_ready=0;g_rsp_ready=0;host_rsp_ready=0;
      repeat(3)@(negedge clk);owner=0;service_active=0;reset=0;
      allow_mem_req=1;allow_mem_rsp=1;allow_native_ack=1;allow_e_input=1;allow_e_output=1;allow_g_input=1;allow_g_output=1;
      repeat(8)@(negedge clk);if(e_rsp_valid||g_rsp_valid||eout_leaf_valid||gout_leaf_valid||!e_req_ready||!g_req_ready||pending)$fatal(1,"FAIL_W3_ADAPTER reset stale service");
    end
  endtask
  integer index;
  initial begin
    repeat(4)@(negedge clk);reset=0;repeat(2)@(negedge clk);
    for(index=0;index<NE;index=index+1)begin run_e(index,0);mark(e_name(index));end
    for(index=0;index<NG;index=index+1)begin run_g(index,0);mark(g_name(index));end
    run_e(3,1);mark("W3_E_NATIVE_INPUT_HOLD_CAPTURED_REQ");run_e(3,2);mark("W3_E_NATIVE_OUTPUT_BACKPRESSURE");
    run_e(13,3);mark("W3_E_DESTINATION_REAL_WRITE_ACK_GATE");run_e(3,4);mark("W3_E_MEM_REQ_RSP_HOLD_GATHER");
    run_g(0,1);mark("W3_G_NATIVE_INPUT_HOLD_CAPTURED_REQ");run_g(1,2);mark("W3_G_MULTIPLE_INFLIGHT_OUTPUT_FREEZE");
    run_g(1,3);mark("W3_G_DESTINATION_REAL_WRITE_ACK_GATE");run_g(0,4);mark("W3_G_MEM_REQ_RSP_HOLD_GATHER");
    prepare(1,3);allow_e_output=0;launch_e();while(!eout_leaf_valid)@(negedge clk);coordinated_reset();run_e(3,0);mark("W3_E_COORDINATED_RESET_NATIVE_RESPONSE_RECOVER");
    prepare(2,1);allow_g_output=0;launch_g();while(!gout_leaf_valid)@(negedge clk);if(max_flight<2)$fatal(1,"FAIL_W3_ADAPTER G reset setup");coordinated_reset();run_g(1,0);mark("W3_G_COORDINATED_RESET_INFLIGHT_RECOVER");
    $display("PASS_W3_ADAPTERS cases=%0d cycles=%0d E=%0d Gissued=%0d Gretired=%0d Sread=%0d Swrite=%0d Sack=%0d",cases,cycles,native_e,native_g,retired_g,memreads,memwrites,memacks);$finish;
  end

endmodule
