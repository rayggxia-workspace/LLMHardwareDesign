`timescale 1ns/1ps
// Independent mathematical literals; no DUT-derived expected values.
module block_w4_a8_tb;
// Independent generated A8 literals. Include inside an SV TB module.
// Q/K/V S8Fin7; score S16Fin10; EXP U16; prob S16Q14; final S16Fin10.
localparam integer A8_VECTOR_COUNT=8;
function automatic [127:0] a8_input_word;
input integer vector_no,word_index;
begin case(vector_no*16+word_index)
 0:a8_input_word=128'h00000000000000008070a050c030e010;
 1:a8_input_word=128'h00000000000000000000000000000000;
 2:a8_input_word=128'h00000000000000000000000000000000;
 3:a8_input_word=128'h00000000000000000000000000000000;
 4:a8_input_word=128'h5643301d0af7e4d1311e0bf8e5d2bfac;
 5:a8_input_word=128'he1cebba854412e1bbca955422f1c09f6;
 6:a8_input_word=128'h2b1805f2dfccb9a606f3e0cdbaa75340;
 7:a8_input_word=128'hb6a34f3c291603f0503d2a1704f1decb;
 8:a8_input_word=128'hc1ae5a4734210efb5b4835220ffce9d6;
 9:a8_input_word=128'h0bf8e5d2bfac5845e6d3c0ad59463320;
 10:a8_input_word=128'h55422f1c09f6e3d0301d0af7e4d1beab;
 11:a8_input_word=128'he0cdbaa753402d1abba854412e1b08f5;
 16:a8_input_word=128'h0000000000000000fd07eb23cf3fb35b;
 17:a8_input_word=128'h00000000000000000000000000000000;
 18:a8_input_word=128'h00000000000000000000000000000000;
 19:a8_input_word=128'h00000000000000000000000000000000;
 20:a8_input_word=128'hfd07f50fed17e51ffd07f50fed17e51f;
 21:a8_input_word=128'hfd07f50fed17e51ffd07f50fed17e51f;
 22:a8_input_word=128'hfd07f50fed17e51ffd07f50fed17e51f;
 23:a8_input_word=128'hfd07f50fed17e51ffd07f50fed17e51f;
 24:a8_input_word=128'hdbc8b5a24e3b2815b6a34f3c291603f0;
 25:a8_input_word=128'h2512ffecd9c6b35f00eddac7b4a14d3a;
 26:a8_input_word=128'hb05c49362310fdea4a372411feebd8c5;
 27:a8_input_word=128'hfae7d4c1ae5a4734d5c2af5b4835220f;
 32:a8_input_word=128'h00000000000000000000000000000000;
 33:a8_input_word=128'h00000000000000000000000000000000;
 34:a8_input_word=128'h00000000000000000000000000000000;
 35:a8_input_word=128'h00000000000000000000000000000000;
 36:a8_input_word=128'heddac7b4a14d3a27c8b5a24e3b281502;
 37:a8_input_word=128'h372411feebd8c5b212ffecd9c6b35f4c;
 38:a8_input_word=128'hc2af5b4835220ffc5c49362310fdead7;
 39:a8_input_word=128'h0cf9e6d3c0ad5946e7d4c1ae5a473421;
 40:a8_input_word=128'h1704f1decbb8a551f2dfccb9a6523f2c;
 41:a8_input_word=128'ha24e3b281502efdc3c291603f0ddcab7;
 42:a8_input_word=128'hecd9c6b35f4c3926c7b4a14d3a271401;
 43:a8_input_word=128'h362310fdead7c4b111feebd8c5b25e4b;
 48:a8_input_word=128'h00000000000000007f7f7f7f7f7f7f7f;
 49:a8_input_word=128'h00000000000000000000000000000000;
 50:a8_input_word=128'h00000000000000000000000000000000;
 51:a8_input_word=128'h00000000000000000000000000000000;
 52:a8_input_word=128'h80808080808080808080808080808080;
 53:a8_input_word=128'h80808080808080808080808080808080;
 54:a8_input_word=128'h80808080808080808080808080808080;
 55:a8_input_word=128'h7f7f7f7f7f7f7f7f8080808080808080;
 56:a8_input_word=128'h5c49362310fdead7372411feebd8c5b2;
 57:a8_input_word=128'he7d4c1ae5a473421c2af5b4835220ffc;
 58:a8_input_word=128'h311e0bf8e5d2bfac0cf9e6d3c0ad5946;
 59:a8_input_word=128'hbca955422f1c09f65643301d0af7e4d1;
 64:a8_input_word=128'h00000000000000007f807f807f807f80;
 65:a8_input_word=128'h00000000000000000000000000000000;
 66:a8_input_word=128'h00000000000000000000000000000000;
 67:a8_input_word=128'h00000000000000000000000000000000;
 68:a8_input_word=128'h807f807f807f807f7f807f807f807f80;
 69:a8_input_word=128'h807f807f807f807f7f807f807f807f80;
 70:a8_input_word=128'h807f807f807f807f7f807f807f807f80;
 71:a8_input_word=128'h807f807f807f807f7f807f807f807f80;
 72:a8_input_word=128'h807f7f7f80807f7f7f80807f7f7f8080;
 73:a8_input_word=128'h80807f7f7f80807f7f7f80807f7f7f80;
 74:a8_input_word=128'h7f80807f7f7f80807f7f7f80807f7f7f;
 75:a8_input_word=128'h7f7f80807f7f7f80807f7f7f80807f7f;
 80:a8_input_word=128'h00000000000000000240c00100ff7f80;
 81:a8_input_word=128'h00000000000000000000000000000000;
 82:a8_input_word=128'h00000000000000000000000000000000;
 83:a8_input_word=128'h00000000000000000000000000000000;
 84:a8_input_word=128'h0000000000007f00000000000000007f;
 85:a8_input_word=128'h000000007f00000000000000007f0000;
 86:a8_input_word=128'h00007f00000000000000007f00000000;
 87:a8_input_word=128'h7f00000000000000007f000000000000;
 88:a8_input_word=128'h5c46301a04eed8c2eee3d8cdc2b7aca1;
 89:a8_input_word=128'h390de1b5895c3004cbaa8967462504e3;
 90:a8_input_word=128'h16d4924f0dcb8946a8703902cb945c25;
 91:a8_input_word=128'hf39b42ea9239e1898537ea9d4f02b567;
 96:a8_input_word=128'h0000000000000000f5e3d5c3ad9f8f81;
 97:a8_input_word=128'h00000000000000000000000000000000;
 98:a8_input_word=128'h00000000000000000000000000000000;
 99:a8_input_word=128'h00000000000000000000000000000000;
 100:a8_input_word=128'hbba854412e1b08f555422f1c09f6e3d0;
 101:a8_input_word=128'h05f2dfccb9a6523fe0cdbaa753402d1a;
 102:a8_input_word=128'h4f3c291603f0ddca2a1704f1decbb8a5;
 103:a8_input_word=128'hdac7b4a14d3a2714b5a24e3b281502ef;
 104:a8_input_word=128'h05f2dfccb9a6523fe0cdbaa753402d1a;
 105:a8_input_word=128'h4f3c291603f0ddca2a1704f1decbb8a5;
 106:a8_input_word=128'hdac7b4a14d3a2714b5a24e3b281502ef;
 107:a8_input_word=128'h2411feebd8c5b25effecd9c6b35f4c39;
 112:a8_input_word=128'h0000000000000000807f807f807f807f;
 113:a8_input_word=128'h00000000000000000000000000000000;
 114:a8_input_word=128'h00000000000000000000000000000000;
 115:a8_input_word=128'h00000000000000000000000000000000;
 116:a8_input_word=128'h4e3b281502efdcc9291603f0ddcab7a4;
 117:a8_input_word=128'hd9c6b35f4c392613b4a14d3a271401ee;
 118:a8_input_word=128'h2310fdead7c4b15dfeebd8c5b25e4b38;
 119:a8_input_word=128'hae5a4734210efbe84835220ffce9d6c3;
 120:a8_input_word=128'h9f9f9f9f9f9f9f9f8080808080808080;
 121:a8_input_word=128'hffffffffffffffffe1e1e1e1e1e1e1e1;
 122:a8_input_word=128'h01010101010101010000000000000000;
 123:a8_input_word=128'h7f7f7f7f7f7f7f7f3f3f3f3f3f3f3f3f;
 default:a8_input_word=128'hbad;
endcase end
endfunction
function automatic [127:0] a8_stage_word;
input integer vector_no,address;
begin case(vector_no*1024+address)
 460:a8_stage_word=128'hff83ff74ffa8ff99ff8aff7bff6cffa0;
 461:a8_stage_word=128'h7b7679aa80007e247c4e7a7f78b87f02;
 464:a8_stage_word=128'h07f307d6083e0820080107e407c6082e;
 465:a8_stage_word=128'h00000000000000000000000000000000;
 466:a8_stage_word=128'h00000000000000000000000000000000;
 467:a8_stage_word=128'h00000000000000000000000000000000;
 468:a8_stage_word=128'hffe400430094ff6cffc10014007300c4;
 1484:a8_stage_word=128'h00b300b300b300b300b300b300b300b3;
 1485:a8_stage_word=128'h80008000800080008000800080008000;
 1488:a8_stage_word=128'h08000800080008000800080008000800;
 1489:a8_stage_word=128'h00000000000000000000000000000000;
 1490:a8_stage_word=128'h00000000000000000000000000000000;
 1491:a8_stage_word=128'h00000000000000000000000000000000;
 1492:a8_stage_word=128'hfff9004f00a5003cffd3ff6affc00016;
 2508:a8_stage_word=128'h00000000000000000000000000000000;
 2509:a8_stage_word=128'h80008000800080008000800080008000;
 2512:a8_stage_word=128'h08000800080008000800080008000800;
 2513:a8_stage_word=128'h00000000000000000000000000000000;
 2514:a8_stage_word=128'h00000000000000000000000000000000;
 2515:a8_stage_word=128'h00000000000000000000000000000000;
 2516:a8_stage_word=128'hff9cfff20048ffdf0035ffccff63ffb9;
 3532:a8_stage_word=128'h0b23f4c6f4c6f4c6f4c6f4c6f4c6f4c6;
 3533:a8_stage_word=128'h8000007a007a007a007a007a007a007a;
 3536:a8_stage_word=128'h3e60003b003b003b003b003b003b003b;
 3537:a8_stage_word=128'h00000000000000000000000000000000;
 3538:a8_stage_word=128'h00000000000000000000000000000000;
 3539:a8_stage_word=128'h00000000000000000000000000000000;
 3540:a8_stage_word=128'hfdf202a10179005cff3ffe2202d101a9;
 4556:a8_stage_word=128'hf4c60b3af4c60b3af4c60b3af4c60b3a;
 4557:a8_stage_word=128'h00788000007880000078800000788000;
 4560:a8_stage_word=128'h000f0ff1000f0ff1000f0ff1000f0ff1;
 4561:a8_stage_word=128'h00000000000000000000000000000000;
 4562:a8_stage_word=128'h00000000000000000000000000000000;
 4563:a8_stage_word=128'h00000000000000000000000000000000;
 4564:a8_stage_word=128'hfffe01f8fffc01fafffcfffe01f8fffc;
 5580:a8_stage_word=128'h000600b4ff4c00030000fffd0164fe99;
 5581:a8_stage_word=128'h5af26bc94bd75aae5a6a5a2680003fad;
 5584:a8_stage_word=128'h07e4095b069507df07d907d30b1c0587;
 5585:a8_stage_word=128'h00000000000000000000000000000000;
 5586:a8_stage_word=128'h00000000000000000000000000000000;
 5587:a8_stage_word=128'h00000000000000000000000000000000;
 5588:a8_stage_word=128'hfeecff82ff390059000fffc5007efe3f;
 6604:a8_stage_word=128'hff53ff69008d025b0033ff08ff1e0043;
 6605:a8_stage_word=128'h3bff3d4c518680004aaa37c138f84bd7;
 6608:a8_stage_word=128'h0677069b08c80dca080b06020623082c;
 6609:a8_stage_word=128'h00000000000000000000000000000000;
 6610:a8_stage_word=128'h00000000000000000000000000000000;
 6611:a8_stage_word=128'h00000000000000000000000000000000;
 6612:a8_stage_word=128'hffd4ffceff6600590069ff41ff6fff96;
 7628:a8_stage_word=128'h0142ff29014501440143ff2aff29ff2c;
 7629:a8_stage_word=128'h7fa14b8b80007fe07fc04b9e4b8b4bc4;
 7632:a8_stage_word=128'h0a0a05f10a110a0f0a0c05f305f105f6;
 7633:a8_stage_word=128'h00000000000000000000000000000000;
 7634:a8_stage_word=128'h00000000000000000000000000000000;
 7635:a8_stage_word=128'h00000000000000000000000000000000;
 7636:a8_stage_word=128'h03f801f800080000fff8ff08fcf8fc00;
 default:a8_stage_word=128'hbad;
endcase end
endfunction
function automatic [127:0] a8_qk_carrier;
input integer vector_no,half_index;
begin case(vector_no*2+half_index)
 0:a8_qk_carrier=128'hffffff8affffff7bffffff6cffffffa0;
 1:a8_qk_carrier=128'hffffff83ffffff74ffffffa8ffffff99;
 2:a8_qk_carrier=128'h000000b3000000b3000000b3000000b3;
 3:a8_qk_carrier=128'h000000b3000000b3000000b3000000b3;
 4:a8_qk_carrier=128'h00000000000000000000000000000000;
 5:a8_qk_carrier=128'h00000000000000000000000000000000;
 6:a8_qk_carrier=128'hfffff4c6fffff4c6fffff4c6fffff4c6;
 7:a8_qk_carrier=128'h00000b23fffff4c6fffff4c6fffff4c6;
 8:a8_qk_carrier=128'hfffff4c600000b3afffff4c600000b3a;
 9:a8_qk_carrier=128'hfffff4c600000b3afffff4c600000b3a;
 10:a8_qk_carrier=128'h00000000fffffffd00000164fffffe99;
 11:a8_qk_carrier=128'h00000006000000b4ffffff4c00000003;
 12:a8_qk_carrier=128'h00000033ffffff08ffffff1e00000043;
 13:a8_qk_carrier=128'hffffff53ffffff690000008d0000025b;
 14:a8_qk_carrier=128'h00000143ffffff2affffff29ffffff2c;
 15:a8_qk_carrier=128'h00000142ffffff290000014500000144;
 default:a8_qk_carrier=128'hbad;
endcase end
endfunction
function automatic [127:0] a8_pv_carrier;
input integer vector_no,half_index;
begin case(vector_no*2+half_index)
 0:a8_pv_carrier=128'hffffffc10000001400000073000000c4;
 1:a8_pv_carrier=128'hffffffe40000004300000094ffffff6c;
 2:a8_pv_carrier=128'hffffffd3ffffff6affffffc000000016;
 3:a8_pv_carrier=128'hfffffff90000004f000000a50000003c;
 4:a8_pv_carrier=128'h00000035ffffffccffffff63ffffffb9;
 5:a8_pv_carrier=128'hffffff9cfffffff200000048ffffffdf;
 6:a8_pv_carrier=128'hffffff3ffffffe22000002d1000001a9;
 7:a8_pv_carrier=128'hfffffdf2000002a1000001790000005c;
 8:a8_pv_carrier=128'hfffffffcfffffffe000001f8fffffffc;
 9:a8_pv_carrier=128'hfffffffe000001f8fffffffc000001fa;
 10:a8_pv_carrier=128'h0000000fffffffc50000007efffffe3f;
 11:a8_pv_carrier=128'hfffffeecffffff82ffffff3900000059;
 12:a8_pv_carrier=128'h00000069ffffff41ffffff6fffffff96;
 13:a8_pv_carrier=128'hffffffd4ffffffceffffff6600000059;
 14:a8_pv_carrier=128'hfffffff8ffffff08fffffcf8fffffc00;
 15:a8_pv_carrier=128'h000003f8000001f80000000800000000;
 default:a8_pv_carrier=128'hbad;
endcase end
endfunction
function automatic a8_expected_saturated;input integer vector_no;begin case(vector_no)
 0:a8_expected_saturated=1'b0;
 1:a8_expected_saturated=1'b0;
 2:a8_expected_saturated=1'b0;
 3:a8_expected_saturated=1'b0;
 4:a8_expected_saturated=1'b0;
 5:a8_expected_saturated=1'b0;
 6:a8_expected_saturated=1'b0;
 7:a8_expected_saturated=1'b0;
 default:a8_expected_saturated=1'bx;endcase end endfunction
function automatic [8*100-1:0] a8_vector_name;input integer vector_no;begin case(vector_no)
 0:a8_vector_name="nonconstant_asymmetric";
 1:a8_vector_name="equal_scores_distinct_values";
 2:a8_vector_name="zero_query_nonzero_values";
 3:a8_vector_name="last_key_newmax_extreme";
 4:a8_vector_name="alternating_signed_extreme";
 5:a8_vector_name="sparse_identity_layout";
 6:a8_vector_name="negative_query_mixed_keys";
 7:a8_vector_name="constant_value_channels";
 default:a8_vector_name="invalid";endcase end endfunction

function automatic [8*100-1:0] case_name;input integer index;begin case(index)
 0:case_name="A8_INPUT12_STORED_PADDING_ACK_GATE";
 1:case_name="A8_NONCONSTANT_STAGES_COUNTS_HELD_START";
 2:case_name="A8_EQUAL_SCORES_UNIFORM_PROB";
 3:case_name="A8_ZERO_QUERY_NONZERO_VALUES";
 4:case_name="A8_LAST_KEY_NEWMAX_EXTREME";
 5:case_name="A8_ALTERNATING_SIGNED_EXTREME";
 6:case_name="A8_SPARSE_IDENTITY_LAYOUT";
 7:case_name="A8_NEGATIVE_QUERY_MIXED_KEYS";
 8:case_name="A8_CONSTANT_VALUE_CHANNELS";
 9:case_name="A8_HELD_START_AFTER_LAST_ACK_REPEAT";
 10:case_name="A8_M_CMD_RSP_LOADER_N_COMPLETION_BACKPRESSURE";
 11:case_name="A8_ABORT_CAPTURED_BEFORE_S_ACCEPT_RECOVER";
 12:case_name="A8_ABORT_INPUT_PENDING_ACK_RECOVER";
 13:case_name="A8_ABORT_COMPLETE_PRESTART_RECOVER";
 14:case_name="A8_ABORT_RUN_SCORE_ACK_RECOVER";
 15:case_name="A8_ABORT_AFTER_CONSUMED_PREFIX_RECOVER";
 16:case_name="A8_DONE_ABORT_READY_EXACTLY_ONCE";
 17:case_name="A8_RESET_PARTIAL_INPUT_RECOVER";
 18:case_name="A8_RESET_HELD_N_SERVICE_RECOVER";
 19:case_name="A8_RESET_COMMITTED_T_STALL_RECOVER";
 20:case_name="A8_NATIVE_N_ERROR_NO_PV_COORDINATED_RECOVER";
 21:case_name="A8_NATIVE_QK_EXEC_ERROR_RECOVER";
 22:case_name="A8_NATIVE_PV_EXEC_ERROR_RECOVER";
 23:case_name="A8_ABORT_EXP_WRITE_ACK_COORDINATED_RECOVER";
 24:case_name="A8_RESET_HELD_M_RESPONSE_RECOVER";
 25:case_name="A8_PROBABILITY_DESTINATION_ACK_GATES_PV";
 default:case_name="invalid";endcase end endfunction

 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;
 reg [127:0] in_data=0;
 wire in_ready,input_stored,start_ready,busy,done_valid,done_error,done_saturated,out_valid,out_last;
 wire [127:0] out_data;wire [9:0] out_index;
 block_w4_a8_top dut(.*);
 integer cycles=0,cases=0,v=0,ingress=0,sreq=0,sack=0,writes=0,reads=0;
 integer mcmd=0,mrsp=0,loads=0,ldone=0,abeats=0,bbeats=0,ncmd=0,nrsp=0,nservice=0,nservice_rsp=0;
 integer tbegin=0,twrite=0,tcommit=0,ttake=0,trelease=0,starts=0,dtake=0;
 integer i0,q0,a0,w0,r0,mc0,mr0,l0,ld0,ab0,bb0,nc0,nr0,ns0,nsr0,tb0,tw0,tc0,tt0,tr0,st0;
 integer stage_acks[0:6],input_acks=0,input_reqs=0,run_writes=0,run_reads=0;
 reg frame_open=0,job=0,pending=0,pending_write,strict_native=1,load_completed=0;
 reg [9:0] pending_addr;reg [127:0] pending_data;
 reg hold_out=0,hold_done=0,hold_s=0,hold_m=0,hold_n=0,hold_in=0;
 reg [127:0] old_out,old_s,old_m,old_in;reg [9:0] old_index;reg old_last,old_de,old_ds,old_ne,old_ns;
 integer projection_execs=0;
 function automatic integer stage_index;input integer address;
  begin case(address)460:stage_index=0;461:stage_index=1;464:stage_index=2;465:stage_index=3;466:stage_index=4;467:stage_index=5;468:stage_index=6;default:stage_index=-1;endcase end
 endfunction
 function automatic [127:0] ram;input integer address;
  begin case(address%4)0:ram=dut.u_s.storage.bank0[address/4];1:ram=dut.u_s.storage.bank1[address/4];2:ram=dut.u_s.storage.bank2[address/4];3:ram=dut.u_s.storage.bank3[address/4];endcase end
 endfunction
 function automatic [127:0] dirty_input;input integer vec,beat;reg [127:0] data;
  begin data=a8_input_word(vec,beat);if(beat==0)data[127:64]=64'hbadc0ffee55aacc1;else if(beat<4)data=128'hfedcba98765432100123456789abcdef;dirty_input=data;end
 endfunction
 function automatic signed [7:0] byte_at;input integer vec,base,offset;reg [127:0] data;
  begin data=a8_input_word(vec,base+offset/16);byte_at=data[8*(offset%16)+:8];end
 endfunction
 function automatic signed [15:0] lane;input integer vec,address,index;reg [127:0] data;
  begin data=a8_stage_word(vec,address);lane=$signed(data[16*index+:16]);end
 endfunction
 function automatic signed [63:0] round_even;input signed [63:0] value;input integer shift;reg signed [63:0] q;reg [63:0] r,h;
  begin q=value>>>shift;r=$unsigned(value)&((64'd1<<shift)-1);h=64'd1<<(shift-1);round_even=q+((r>h)||((r==h)&&q[0]));end
 endfunction
 task automatic crosscheck;input integer vec;integer t,d,c;reg signed [63:0] raw;
  begin for(t=0;t<8;t=t+1)begin raw=0;for(d=0;d<8;d=d+1)raw=raw+byte_at(vec,0,d)*byte_at(vec,4,8*t+d);
   if(round_even(raw*64'sd11585,19)!==$signed(lane(vec,460,t)))$fatal(1,"FAIL_A8 independent QK formula");
  end
  for(c=0;c<8;c=c+1)begin raw=0;for(t=0;t<8;t=t+1)raw=raw+lane(vec,464,t)*byte_at(vec,8,8*c+t);
   if(round_even(raw,11)!==$signed(lane(vec,468,c)))$fatal(1,"FAIL_A8 independent PV/layout formula");
  end end
 endtask
 function automatic integer native_n_op;input integer index;
  begin case(index)0:native_n_op=0;1:native_n_op=1;2:native_n_op=2;3:native_n_op=3;4:native_n_op=4;5:native_n_op=6;default:native_n_op=-1;endcase end
 endfunction
 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>400000)$fatal(1,"FAIL_A8 watchdog");
  // Public DONE survives abort/internal leaf reset; only hard reset cancels it.
  if(reset)hold_done=0;else begin
   if(hold_done&&(!done_valid||done_error!==old_de||done_saturated!==old_ds))$fatal(1,"FAIL_A8 held DONE changed");
   hold_done=done_valid&&!done_ready;old_de=done_error;old_ds=done_saturated;
   if(done_valid&&done_ready)dtake=dtake+1;
  end
  if(reset||dut.leaf_reset)begin hold_out=0;hold_s=0;hold_m=0;hold_n=0;hold_in=0;pending=0;end
  else begin
   if(hold_in&&(!in_valid||in_data!==old_in))$fatal(1,"FAIL_A8 TB ingress unstable");
   if(hold_out&&(!out_valid||out_data!==old_out||out_index!==old_index||out_last!==old_last))$fatal(1,"FAIL_A8 output hold");
   if(hold_s&&(!dut.s_valid||dut.s_dout!==old_s))$fatal(1,"FAIL_A8 S ACK hold");
   if(hold_m&&(!dut.m_rsp_valid||dut.m_rsp_data!==old_m))$fatal(1,"FAIL_A8 M response hold");
   if(hold_n&&(!dut.n_rsp_valid||dut.n_rsp_error!==old_ne||dut.n_rsp_saturated!==old_ns))$fatal(1,"FAIL_A8 N service hold");
   hold_in=in_valid&&!in_ready;old_in=in_data;hold_out=out_valid&&!out_ready;old_out=out_data;old_index=out_index;old_last=out_last;
   hold_s=dut.s_valid&&!dut.s_take;old_s=dut.s_dout;hold_m=dut.m_rsp_valid&&!dut.m_rsp_ready;old_m=dut.m_rsp_data;
   hold_n=dut.n_rsp_valid&&!dut.n_rsp_ready;old_ne=dut.n_rsp_error;old_ns=dut.n_rsp_saturated;
   if(in_valid&&in_ready)begin if(!frame_open||job||ingress-i0>=12)$fatal(1,"FAIL_A8 ingress ownership");ingress=ingress+1;end
   if(dut.s_req&&dut.s_ready)begin
    if(pending)$fatal(1,"FAIL_A8 multiple ordinary S owners");pending=1;pending_write=dut.s_we;pending_addr=dut.s_addr;pending_data=dut.s_din;sreq=sreq+1;
    if(dut.s_we)begin writes=writes+1;
     if(dut.s_addr>=448&&dut.s_addr<=459)begin
      if(job||dut.s_addr!=448+input_reqs||dut.s_din!==a8_input_word(v,dut.s_addr-448))$fatal(1,"FAIL_A8 ingress canonicalization/order");input_reqs=input_reqs+1;
     end else if(stage_index(dut.s_addr)>=0)begin
      if(!job||dut.s_din!==a8_stage_word(v,dut.s_addr))$fatal(1,"FAIL_A8 math S write addr%0d got%032h expected%032h",dut.s_addr,dut.s_din,a8_stage_word(v,dut.s_addr));run_writes=run_writes+1;
     end else $fatal(1,"FAIL_A8 forbidden S write/unused462..463");
    end else begin
     reads=reads+1;run_reads=run_reads+1;
     if(!job||!(dut.s_addr==460||dut.s_addr==461||dut.s_addr==468))$fatal(1,"FAIL_A8 forbidden S read");
    end
   end
   if(dut.s_valid&&dut.s_take)begin
    if(!pending)$fatal(1,"FAIL_A8 ACK without ownership");
    if(pending_write&&dut.s_dout!==pending_data)$fatal(1,"FAIL_A8 ACK echo");
    if(!pending_write&&dut.s_dout!==a8_stage_word(v,pending_addr))$fatal(1,"FAIL_A8 stage read lineage");
    if(pending_write&&pending_addr<460)input_acks=input_acks+1;
    if(pending_write&&stage_index(pending_addr)>=0)stage_acks[stage_index(pending_addr)]=stage_acks[stage_index(pending_addr)]+1;
    pending=0;sack=sack+1;
   end
   if(input_stored&&(ingress-i0!=12||input_acks!=12||(!job&&pending)))$fatal(1,"FAIL_A8 stored before12ACK");
   if(start_ready&&!input_stored)$fatal(1,"FAIL_A8 early start ready");
   if(start_valid&&start_ready)begin if(job||input_acks!=12||!input_stored)$fatal(1,"FAIL_A8 duplicate/early start");job=1;starts=starts+1;end
   if(dut.load_valid&&dut.load_ready)begin
    if(!job||loads-l0>1||pending||dut.u_s.load_a_wide!==(loads-l0==1)||dut.u_s.load_b_wide||dut.u_s.load_rows!=1||dut.u_s.load_tiles!=1)$fatal(1,"FAIL_A8 loader geometry/ownership");
    if(loads-l0==1&&(stage_acks[2]!=1||stage_acks[3]!=1||stage_acks[4]!=1||stage_acks[5]!=1))$fatal(1,"FAIL_A8 PV before prob/padding ACK");
    loads=loads+1;load_completed=0;
   end
   if(dut.load_done_valid&&dut.load_done_take)begin ldone=ldone+1;load_completed=!dut.load_done_error;end
   if(dut.a_valid&&dut.a_ready)begin if(dut.a_data!==(loads-l0==1?a8_input_word(v,0):a8_stage_word(v,464)))$fatal(1,"FAIL_A8 A payload/narrow-v-wide format");abeats=abeats+1;end
   if(dut.b_valid&&dut.b_ready)begin
    if(dut.b_data!=={a8_input_word(v,loads-l0==1?7:11),a8_input_word(v,loads-l0==1?6:10),a8_input_word(v,loads-l0==1?5:9),a8_input_word(v,loads-l0==1?4:8)})$fatal(1,"FAIL_A8 full512 B K/V layout");bbeats=bbeats+1;
   end
   if(dut.m_cmd_valid&&dut.m_cmd_ready)begin
    if(!job)$fatal(1,"FAIL_A8 M beforeRUN");
    if(strict_native)case(dut.m_phase)
     0:if(dut.m_cmd_op!=6||dut.m_cmd_data!=0)$fatal(1,"FAIL_A8 CLEAR is opcode6");
     1:if(dut.m_cmd_op!=4||dut.m_cmd_data!=(dut.projection==0?11585:1))$fatal(1,"FAIL_A8 factor signedS16/left0");
     2:if(dut.m_cmd_op!=10||dut.m_cmd_index!=0||dut.m_cmd_data!=(dut.projection==0?64'h9884:64'h9885))$fatal(1,"FAIL_A8 EXEC layout");
     3,4:if(dut.m_cmd_op!=5||dut.m_cmd_index!=(dut.m_phase==4)||dut.m_cmd_data!=(dut.projection==0?64'h113:64'h10b))$fatal(1,"FAIL_A8 quantization/read half");
    endcase
    if(dut.m_cmd_op==10)begin if(!load_completed)$fatal(1,"FAIL_A8 EXEC before load complete");projection_execs=projection_execs+1;end
    mcmd=mcmd+1;
   end
   if(dut.m_rsp_valid&&dut.m_rsp_ready)begin
    if(!dut.m_rsp_error&&(dut.m_phase==3||dut.m_phase==4)&&dut.m_rsp_data!==(dut.projection==0?a8_qk_carrier(v,dut.m_phase==4):a8_pv_carrier(v,dut.m_phase==4)))$fatal(1,"FAIL_A8 M fourS32 carriers");mrsp=mrsp+1;
   end
   if(dut.n_req_valid&&dut.n_req_ready)begin if(stage_acks[0]!=1||dut.owner!=3)$fatal(1,"FAIL_A8 N before scoreACK/owner");nservice=nservice+1;end
   if(dut.n_rsp_valid&&dut.n_rsp_ready)begin if(!dut.n_rsp_error&&(stage_acks[1]!=1||stage_acks[2]!=1))$fatal(1,"FAIL_A8 N completion before EXP/probACK");nservice_rsp=nservice_rsp+1;end
   if(dut.n_cmd_valid&&dut.n_cmd_ready)begin
    if(strict_native)begin
     if(dut.n_cmd_op!=native_n_op(ncmd-nc0))$fatal(1,"FAIL_A8 N phase order");
     if(dut.n_cmd_op==1||dut.n_cmd_op==3||dut.n_cmd_op==6)begin
      if(dut.n_cmd_count!=8||dut.n_cmd_data!==(dut.n_cmd_op==6?a8_stage_word(v,461):a8_stage_word(v,460)))$fatal(1,"FAIL_A8 N raw/EXP lineage and count");
     end
    end
    ncmd=ncmd+1;
   end
   if(dut.n_native_rsp_valid&&dut.n_native_rsp_ready)nrsp=nrsp+1;
   if(dut.u_t.begin_valid&&dut.u_t.begin_ready)tbegin=tbegin+1;
   if(dut.u_t.write_valid&&dut.u_t.write_ready)begin if(dut.u_t.write_index!=0||dut.u_t.write_data!==a8_stage_word(v,468))$fatal(1,"FAIL_A8 T word");twrite=twrite+1;end
   if(dut.u_t.commit_valid&&dut.u_t.commit_ready)tcommit=tcommit+1;
   if(out_valid&&out_ready)begin if(ttake-tt0!=0||out_index!=0||!out_last||out_data!==a8_stage_word(v,468))$fatal(1,"FAIL_A8 final math");ttake=ttake+1;end
   if(dut.u_t.release_valid&&dut.u_t.release_ready)trelease=trelease+1;
  end
 end
 task automatic mark;input integer which;begin cases=cases+1;$display("CASE_PASS %0s",case_name(which));end endtask
 task automatic new_frame;input integer vec;integer k;
  begin @(negedge clk);if(busy||done_valid||input_stored||out_valid||!in_ready||start_ready)$fatal(1,"FAIL_A8 stale lifecycle");
   v=vec;crosscheck(v);frame_open=1;job=0;strict_native=1;input_acks=0;input_reqs=0;run_writes=0;run_reads=0;load_completed=0;projection_execs=0;
   for(k=0;k<7;k=k+1)stage_acks[k]=0;
   i0=ingress;q0=sreq;a0=sack;w0=writes;r0=reads;mc0=mcmd;mr0=mrsp;l0=loads;ld0=ldone;ab0=abeats;bb0=bbeats;nc0=ncmd;nr0=nrsp;ns0=nservice;nsr0=nservice_rsp;tb0=tbegin;tw0=twrite;tc0=tcommit;tt0=ttake;tr0=trelease;st0=starts;
   in_valid=0;start_valid=0;out_ready=0;done_ready=0;
   dut.u_s.storage.bank0[112]=128'hffffffffffffffffffffffffffffffff;dut.u_s.storage.bank1[112]=128'hffffffffffffffffffffffffffffffff;dut.u_s.storage.bank2[112]=128'hffffffffffffffffffffffffffffffff;dut.u_s.storage.bank3[112]=128'hffffffffffffffffffffffffffffffff;
   dut.u_s.storage.bank1[116]=128'hffffffffffffffffffffffffffffffff;dut.u_s.storage.bank2[116]=128'hffffffffffffffffffffffffffffffff;dut.u_s.storage.bank3[116]=128'hffffffffffffffffffffffffffffffff;
  end
 endtask
 task automatic send;input integer beat;
  begin @(negedge clk);in_valid=1;in_data=dirty_input(v,beat);while(!in_ready)@(negedge clk);@(posedge clk);#1;if(!busy)$fatal(1,"FAIL_A8 accepted data notbusy");@(negedge clk);in_valid=0;end
 endtask
 task automatic fill;integer k;
  begin for(k=0;k<12;k=k+1)send(k);while(!input_stored)@(negedge clk);if(input_acks!=12||!busy||in_ready)$fatal(1,"FAIL_A8 frame notstored");end
 endtask
 task automatic start_job;input hold_start;
  begin @(negedge clk);if(!start_ready)$fatal(1,"FAIL_A8 notstartready");start_valid=1;@(posedge clk);#1;@(negedge clk);if(starts-st0!=1||!busy||start_ready)$fatal(1,"FAIL_A8 start");if(!hold_start)start_valid=0;end
 endtask
 task automatic take_output;integer k;
  begin while(!out_valid)@(negedge clk);repeat(7)begin if(out_data!==a8_stage_word(v,468)||out_index!=0||!out_last)$fatal(1,"FAIL_A8 held output data");@(negedge clk);end
   out_ready=1;@(posedge clk);#1;@(negedge clk);out_ready=0;
  end
 endtask
 task automatic finish;input error_expected,abort_at_done;integer before_take;
  begin while(!done_valid)@(negedge clk);repeat(5)begin if(!done_valid||done_error!==error_expected||in_ready||start_ready||!busy||done_saturated!==a8_expected_saturated(v))$fatal(1,"FAIL_A8 completion hold/status");@(negedge clk);end
   if(!error_expected&&(ttake-tt0!=1||trelease-tr0!=1||dut.t_busy))$fatal(1,"FAIL_A8 done before RELEASE");
   before_take=dtake;start_valid=0;done_ready=1;abort=abort_at_done;@(posedge clk);#1;@(negedge clk);done_ready=0;abort=0;frame_open=0;job=0;repeat(3)@(negedge clk);
   if(dtake!=before_take+1||busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_A8 done duplicate/stale");
  end
 endtask
 task automatic normal_counts;integer k;
  begin if(ingress-i0!=12||input_acks!=12||sreq-q0!=23||sack-a0!=23||writes-w0!=19||reads-r0!=4||run_writes!=7||run_reads!=4||pending)$fatal(1,"FAIL_A8 23S/19W4R");
   if(mcmd-mc0!=10||mrsp-mr0!=10||projection_execs!=2||loads-l0!=2||ldone-ld0!=2||abeats-ab0!=2||bbeats-bb0!=2)$fatal(1,"FAIL_A8 M10/load2");
   if(nservice-ns0!=1||nservice_rsp-nsr0!=1||ncmd-nc0!=6||nrsp-nr0!=6)$fatal(1,"FAIL_A8 N service/native6");
   if(tbegin-tb0!=1||twrite-tw0!=1||tcommit-tc0!=1||ttake-tt0!=1||trelease-tr0!=1||starts-st0!=1)$fatal(1,"FAIL_A8 T lifecycle");
   for(k=0;k<7;k=k+1)if(stage_acks[k]!=1)$fatal(1,"FAIL_A8 stageACK count");
   if(ram(460)!==a8_stage_word(v,460)||ram(461)!==a8_stage_word(v,461)||ram(464)!==a8_stage_word(v,464)||ram(465)!=0||ram(466)!=0||ram(467)!=0||ram(468)!==a8_stage_word(v,468))$fatal(1,"FAIL_A8 finalRAM");
  end
 endtask
 task automatic run_normal;input integer vec;begin new_frame(vec);fill();start_job(0);take_output();finish(0,0);normal_counts();end endtask
 task automatic prestart_abort;
  begin @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;in_valid=0;start_valid=0;frame_open=0;job=0;repeat(3)@(negedge clk);
   if(busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_A8 prestartabort fabricated DONE");
  end
 endtask
 task automatic hard_reset;
  begin @(negedge clk);reset=1;in_valid=0;start_valid=0;out_ready=0;done_ready=0;repeat(3)@(negedge clk);reset=0;frame_open=0;job=0;repeat(3)@(negedge clk);
   if(busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_A8 reset lifecycle");
  end
 endtask
 integer k;
 initial begin
  repeat(4)@(negedge clk);reset=0;@(negedge clk);
  new_frame(0);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);start_valid=1;
  repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0||mcmd!=mc0)$fatal(1,"FAIL_A8 pendingACK start");end
  start_valid=0;release dut.permit_s_rsp;for(k=1;k<11;k=k+1)send(k);while(input_acks<11)@(negedge clk);
  force dut.permit_s_rsp=1'b0;send(11);while(!dut.s_valid)@(negedge clk);start_valid=1;
  repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0)$fatal(1,"FAIL_A8 lastunACKed start");end
  start_valid=0;release dut.permit_s_rsp;while(!input_stored)@(negedge clk);repeat(3)@(negedge clk);
  if(starts!=st0)$fatal(1,"FAIL_A8 earlypulse queued");for(k=0;k<12;k=k+1)if(ram(448+k)!==a8_input_word(v,k))$fatal(1,"FAIL_A8 stored input");mark(0);
  start_job(1);take_output();finish(0,0);normal_counts();mark(1);
  for(k=1;k<8;k=k+1)begin run_normal(k);mark(k+1);end
  new_frame(5);for(k=0;k<11;k=k+1)send(k);while(input_acks<11)@(negedge clk);force dut.permit_s_rsp=1'b0;send(11);start_valid=1;
  repeat(4)@(negedge clk);if(starts!=st0||input_stored)$fatal(1,"FAIL_A8 heldstart early");release dut.permit_s_rsp;while(starts==st0)@(negedge clk);start_valid=0;
  take_output();finish(0,0);normal_counts();mark(9);
  new_frame(3);fill();force dut.permit_m_cmd=1'b0;start_job(0);repeat(5)@(negedge clk);if(mcmd!=mc0)$fatal(1,"FAIL_A8 command backpressure");
  force dut.permit_m_rsp=1'b0;release dut.permit_m_cmd;while(!dut.m_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);force dut.permit_load=1'b0;release dut.permit_m_rsp;
  wait(dut.state==7);repeat(5)@(negedge clk);if(loads!=l0)$fatal(1,"FAIL_A8 loader backpressure");force dut.permit_n_rsp=1'b0;release dut.permit_load;
  while(!dut.n_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);if(stage_acks[2]!=1||stage_acks[3]!=0||loads-l0!=1)$fatal(1,"FAIL_A8 servicecompleted yet PV early");release dut.permit_n_rsp;
  take_output();finish(0,0);normal_counts();mark(10);
  new_frame(0);force dut.permit_s_req=1'b0;send(0);repeat(4)@(negedge clk);prestart_abort();release dut.permit_s_req;run_normal(6);mark(11);
  new_frame(3);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);prestart_abort();release dut.permit_s_rsp;run_normal(0);mark(12);
  new_frame(2);fill();prestart_abort();run_normal(5);mark(13);
  new_frame(4);fill();force dut.permit_s_rsp=1'b0;start_job(0);while(!dut.s_valid)@(negedge clk);
  @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;finish(1,0);run_normal(1);mark(14);
  new_frame(3);fill();start_job(0);take_output();abort=1;@(posedge clk);#1;@(negedge clk);abort=0;
  if(ttake-tt0!=1)$fatal(1,"FAIL_A8 consumedprefix retracted");finish(1,0);run_normal(4);mark(15);
  new_frame(0);fill();start_job(0);take_output();while(!done_valid)@(negedge clk);@(negedge clk);abort=1;
  repeat(3)begin @(negedge clk);if(!done_valid||done_error||done_saturated)$fatal(1,"FAIL_A8 existingDONE changed underabort");end
  abort=0;finish(0,1);normal_counts();mark(16);
  new_frame(4);send(0);send(1);hard_reset();run_normal(3);mark(17);
  new_frame(4);fill();force dut.permit_n_rsp=1'b0;start_job(0);while(!dut.n_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();release dut.permit_n_rsp;run_normal(0);mark(18);
  new_frame(4);fill();start_job(0);while(!out_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();run_normal(5);mark(19);
  new_frame(4);fill();strict_native=0;start_job(0);wait(dut.n_cmd_valid&&dut.n_cmd_ready&&dut.n_cmd_op==1);
  @(negedge clk);force dut.n_cmd_op=4'd15;@(posedge clk);#1;@(negedge clk);release dut.n_cmd_op;
  finish(1,0);if(stage_acks[1]!=0||stage_acks[2]!=0||loads-l0!=1||twrite!=tw0)$fatal(1,"FAIL_A8 nativeN error published/PV");run_normal(6);mark(20);
  new_frame(4);fill();strict_native=0;start_job(0);wait(dut.state==5&&dut.projection==0&&dut.m_phase==2);
  @(negedge clk);force dut.m_cmd_data=64'h988c;@(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;
  finish(1,0);if(stage_acks[0]!=0||nservice!=ns0||twrite!=tw0)$fatal(1,"FAIL_A8 QKerror escaped");run_normal(3);mark(21);
  new_frame(5);fill();strict_native=0;start_job(0);wait(dut.state==5&&dut.projection==1&&dut.m_phase==2);
  @(negedge clk);force dut.m_cmd_data=64'h988d;@(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;
  finish(1,0);if(stage_acks[6]!=0||twrite!=tw0)$fatal(1,"FAIL_A8 PVerror output");run_normal(2);mark(22);
  new_frame(3);fill();start_job(0);wait(dut.n_mem_req_valid&&dut.n_mem_req_write&&dut.n_mem_req_addr==461);force dut.permit_s_rsp=1'b0;while(!dut.s_valid)@(negedge clk);repeat(4)@(negedge clk);
  @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;finish(1,0);run_normal(1);mark(23);
  new_frame(5);fill();force dut.permit_m_rsp=1'b0;start_job(0);while(!dut.m_rsp_valid)@(negedge clk);repeat(4)@(negedge clk);hard_reset();release dut.permit_m_rsp;run_normal(7);mark(24);
  new_frame(3);fill();start_job(0);wait(dut.n_mem_req_valid&&dut.n_mem_req_write&&dut.n_mem_req_addr==464);force dut.permit_s_rsp=1'b0;while(!dut.s_valid)@(negedge clk);
  repeat(5)begin @(negedge clk);if(stage_acks[2]!=0||loads-l0!=1||mcmd-mc0!=5)$fatal(1,"FAIL_A8 PV beforeprobACK");end release dut.permit_s_rsp;
  take_output();finish(0,0);normal_counts();mark(25);
  $display("PASS_W4_A8 cases=%0d cycles=%0d input=%0d Sreq=%0d Sack=%0d Mcmd=%0d Mrsp=%0d Ncmd=%0d Nrsp=%0d Ttake=%0d",cases,cycles,ingress,sreq,sack,mcmd,mrsp,ncmd,nrsp,ttake);$finish;
 end

endmodule
