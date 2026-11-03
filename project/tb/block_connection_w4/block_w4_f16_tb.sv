`timescale 1ns/1ps
// Frozen expectations from independent math oracle, not DUT values.
module block_w4_f16_tb;
  function automatic [127:0] input_word;
    input integer vector_no,beat;
    begin case(vector_no*17+beat)
      0:input_word=128'he0010ffff82f0601fc010309fefd000d;
      1:input_word=128'h00000000000000000000000000000000;
      2:input_word=128'h00000000000000000000000000000000;
      3:input_word=128'h00000000000000000000000000000000;
      4:input_word=128'hfae91706f5e412011c0bfae91706f5e4;
      5:input_word=128'hf5e41201f01e0dfc1706f5e41201f01e;
      6:input_word=128'hf01e0dfceb1908f71201f01e0dfceb19;
      7:input_word=128'heb1908f7e61403f20dfceb1908f7e614;
      8:input_word=128'h0af9e81605f4e311ed1b0af9e81605f4;
      9:input_word=128'h05f4e31100ef1d0ce81605f4e31100ef;
      10:input_word=128'h00ef1d0cfbea1807e31100ef1d0cfbea;
      11:input_word=128'hfbea1807f6e513021d0cfbea1807f6e5;
      12:input_word=128'he10ffeed1b0af9e803f2e10ffeed1b0a;
      13:input_word=128'h1b0af9e81605f4e3feed1b0af9e81605;
      14:input_word=128'h1605f4e31100ef1df9e81605f4e31100;
      15:input_word=128'h1100ef1d0cfbea18f4e31100ef1d0cfb;
      16:input_word=128'h04000400040004000400040004000400;
      17:input_word=128'h00000000000000000000000000000000;
      18:input_word=128'h00000000000000000000000000000000;
      19:input_word=128'h00000000000000000000000000000000;
      20:input_word=128'h00000000000000000000000000000000;
      21:input_word=128'hfeed1b0af9e81605e10ffeed1b0af9e8;
      22:input_word=128'hf9e81605f4e311001b0af9e81605f4e3;
      23:input_word=128'hf4e31100ef1d0cfb1605f4e31100ef1d;
      24:input_word=128'hef1d0cfbea1807f61100ef1d0cfbea18;
      25:input_word=128'h02f11f0efdec1a09e51302f11f0efdec;
      26:input_word=128'hfdec1a09f8e715041f0efdec1a09f8e7;
      27:input_word=128'hf8e71504f3e210ff1a09f8e71504f3e2;
      28:input_word=128'hf3e210ffee1c0bfa1504f3e210ffee1c;
      29:input_word=128'h08f7e61403f2e10feb1908f7e61403f2;
      30:input_word=128'h03f2e10ffeed1b0ae61403f2e10ffeed;
      31:input_word=128'hfeed1b0af9e81605e10ffeed1b0af9e8;
      32:input_word=128'hf9e81605f4e311001b0af9e81605f4e3;
      33:input_word=128'h80007ffffc000c00040002000000f800;
      34:input_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      35:input_word=128'h00000000000000000000000000000000;
      36:input_word=128'h00000000000000000000000000000000;
      37:input_word=128'h00000000000000000000000000000000;
      38:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      39:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      40:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      41:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      42:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      43:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      44:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      45:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      46:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      47:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      48:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      49:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      50:input_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      51:input_word=128'h80008000800080008000800080008000;
      52:input_word=128'h00000000000000000000000000000000;
      53:input_word=128'h00000000000000000000000000000000;
      54:input_word=128'h00000000000000000000000000000000;
      55:input_word=128'h80808080808080808080808080808080;
      56:input_word=128'h80808080808080808080808080808080;
      57:input_word=128'h80808080808080808080808080808080;
      58:input_word=128'h80808080808080808080808080808080;
      59:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      60:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      61:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      62:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      63:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      64:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      65:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      66:input_word=128'h7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f;
      67:input_word=128'h80008000800080008000800080008000;
      68:input_word=128'hfcb902a5ffb90071fda901a303cdfb8f;
      69:input_word=128'h00000000000000000000000000000000;
      70:input_word=128'h00000000000000000000000000000000;
      71:input_word=128'h00000000000000000000000000000000;
      72:input_word=128'h1403f2e10ffeed1bf7e61403f2e10ffe;
      73:input_word=128'h0ffeed1b0af9e816f2e10ffeed1b0af9;
      74:input_word=128'h0af9e81605f4e311ed1b0af9e81605f4;
      75:input_word=128'h05f4e31100ef1d0ce81605f4e31100ef;
      76:input_word=128'he71504f3e210ffee09f8e71504f3e210;
      77:input_word=128'he210ffee1c0bfae904f3e210ffee1c0b;
      78:input_word=128'h1c0bfae91706f5e4ffee1c0bfae91706;
      79:input_word=128'h1706f5e41201f01efae91706f5e41201;
      80:input_word=128'hf3e210ffee1c0bfa1504f3e210ffee1c;
      81:input_word=128'hee1c0bfae91706f510ffee1c0bfae917;
      82:input_word=128'he91706f5e41201f00bfae91706f5e412;
      83:input_word=128'he41201f01e0dfceb06f5e41201f01e0d;
      84:input_word=128'h0400f4000c00fc00060000000200f800;
      85:input_word=128'h80007ffffff1000ffff90007ffff0001;
      86:input_word=128'h00000000000000000000000000000000;
      87:input_word=128'h00000000000000000000000000000000;
      88:input_word=128'h00000000000000000000000000000000;
      89:input_word=128'h0efdec1a09f8e715f11f0efdec1a09f8;
      90:input_word=128'h09f8e71504f3e210ec1a09f8e71504f3;
      91:input_word=128'h04f3e210ffee1c0be71504f3e210ffee;
      92:input_word=128'hffee1c0bfae91706e210ffee1c0bfae9;
      93:input_word=128'h1605f4e31100ef1df9e81605f4e31100;
      94:input_word=128'h1100ef1d0cfbea18f4e31100ef1d0cfb;
      95:input_word=128'h0cfbea1807f6e513ef1d0cfbea1807f6;
      96:input_word=128'h07f6e51302f11f0eea1807f6e51302f1;
      97:input_word=128'h1c0bfae91706f5e4ffee1c0bfae91706;
      98:input_word=128'h1706f5e41201f01efae91706f5e41201;
      99:input_word=128'h1201f01e0dfceb19f5e41201f01e0dfc;
      100:input_word=128'h0dfceb1908f7e614f01e0dfceb1908f7;
      101:input_word=128'h00000000000000000000000000000000;
      102:input_word=128'h00133ffbc00300010000ffff7fff8000;
      103:input_word=128'h00000000000000000000000000000000;
      104:input_word=128'h00000000000000000000000000000000;
      105:input_word=128'h00000000000000000000000000000000;
      106:input_word=128'h0000000000007f00000000000000007f;
      107:input_word=128'h000000007f00000000000000007f0000;
      108:input_word=128'h00007f00000000000000007f00000000;
      109:input_word=128'h7f00000000000000007f000000000000;
      110:input_word=128'h0000008000000000000000007f000000;
      111:input_word=128'h008000000000000000007f0000000000;
      112:input_word=128'h00000000000000807f00000000000000;
      113:input_word=128'h00000000008000000000000000007f00;
      114:input_word=128'h04f3e210ffee1c0be71504f3e210ffee;
      115:input_word=128'hffee1c0bfae91706e210ffee1c0bfae9;
      116:input_word=128'hfae91706f5e412011c0bfae91706f5e4;
      117:input_word=128'hf5e41201f01e0dfc1706f5e41201f01e;
      118:input_word=128'h0c000600fe0002000000fc0008000400;
      119:input_word=128'h627b0c04772da1b730a56378a9f258c3;
      120:input_word=128'h00000000000000000000000000000000;
      121:input_word=128'h00000000000000000000000000000000;
      122:input_word=128'h00000000000000000000000000000000;
      123:input_word=128'hc40a95817a96c0ba921b7d49bee6b9b1;
      124:input_word=128'h505d4c5f6d9892facdac458fd528e9d0;
      125:input_word=128'h83b9e8d5cfff79a499903a1ddbe009da;
      126:input_word=128'h5b7c0075c301ad67728b7def454662f3;
      127:input_word=128'h5fefbd6095ce36afdaa67e26aa634210;
      128:input_word=128'hb49b6a11c9df796c638284d5ce628bc4;
      129:input_word=128'h2b95052e2b47c9e4c8a241d2b8dd4a10;
      130:input_word=128'h52cfcd57e101f788f5c16387bf333d36;
      131:input_word=128'h8169d4fb7542e4be1b1d1fc19ad16c86;
      132:input_word=128'hee008f20efc70fb3c0cbc8816e86b531;
      133:input_word=128'hbbfd6439db29222bce0458c9e4d55a16;
      134:input_word=128'h07ea3bf65e288954a2770571333d9492;
      135:input_word=128'h61e2ffd02f4160c6ea546bb209431756;
      136:input_word=128'h1f939897cfeaf22f329d943b24e35573;
      137:input_word=128'h00000000000000000000000000000000;
      138:input_word=128'h00000000000000000000000000000000;
      139:input_word=128'h00000000000000000000000000000000;
      140:input_word=128'hde1d801b1bad164bbcf1113a6a4ce02a;
      141:input_word=128'h24d55a582a53d7c5926f0d7922cd44ce;
      142:input_word=128'h7afe3181987446e772b783f374bc02bd;
      143:input_word=128'hdd60e79f7650f413ee713cce57529300;
      144:input_word=128'ha5c444d2ca2f91ef6e9d9ce7b5a8c703;
      145:input_word=128'h953d7f27a4b17b3b3edc2e98770a525e;
      146:input_word=128'hec7cd4682b224f9c9dc93b94964361a9;
      147:input_word=128'h792110e7afc67970d04155af2df0244c;
      148:input_word=128'ha3062153b829c19b30b8e7af84d0644e;
      149:input_word=128'h7e96a9871771df593985c91f27120f26;
      150:input_word=128'hdd168c58f3b0080e9c38ca1defa8cb88;
      151:input_word=128'h5dfb8067de2c80134ee2462a1793803a;
      152:input_word=128'hfb45b950107d103f4799fe70fe25910b;
      153:input_word=128'h0043ffc50033ffd50023ffe50013000b;
      154:input_word=128'h00000000000000000000000000000000;
      155:input_word=128'h00000000000000000000000000000000;
      156:input_word=128'h00000000000000000000000000000000;
      157:input_word=128'he31100ef1d0cfbea05f4e31100ef1d0c;
      158:input_word=128'h1d0cfbea1807f6e500ef1d0cfbea1807;
      159:input_word=128'h1807f6e51302f11ffbea1807f6e51302;
      160:input_word=128'h1302f11f0efdec1af6e51302f11f0efd;
      161:input_word=128'heb1908f7e61403f20dfceb1908f7e614;
      162:input_word=128'he61403f2e10ffeed08f7e61403f2e10f;
      163:input_word=128'he10ffeed1b0af9e803f2e10ffeed1b0a;
      164:input_word=128'h1b0af9e81605f4e3feed1b0af9e81605;
      165:input_word=128'hf5e41201f01e0dfc1706f5e41201f01e;
      166:input_word=128'hf01e0dfceb1908f71201f01e0dfceb19;
      167:input_word=128'heb1908f7e61403f20dfceb1908f7e614;
      168:input_word=128'he61403f2e10ffeed08f7e61403f2e10f;
      169:input_word=128'h00000000000000000000000000000000;
      default:input_word=128'hbad;
    endcase end
  endfunction
  function automatic [127:0] stage_word;
    input integer vector_no,address;
    begin case(vector_no*1024+address)
      464:stage_word=128'h02a2ff880267ff4dffcafe2dff1bfdef;
      465:stage_word=128'hff0ffde3fed4026affc102c6ffac028b;
      466:stage_word=128'he0010ffff82f0601fc010309fefd000d;
      467:stage_word=128'he0010ffff82f0601fc010309fefd000d;
      468:stage_word=128'hff98001eff8cffcf0002ff830008ff83;
      469:stage_word=128'h00000000000000000000000000000000;
      470:stage_word=128'h00000000000000000000000000000000;
      471:stage_word=128'h00000000000000000000000000000000;
      472:stage_word=128'hffe3ffddffe800070013fff50033001b;
      473:stage_word=128'hdfe40fdcf8170608fc1402feff300028;
      474:stage_word=128'hf65604d5fda401d0fecb00ebffb20004;
      475:stage_word=128'h04000400040004000400040004000400;
      1488:stage_word=128'h00000000000000000000000000000000;
      1489:stage_word=128'h00000000000000000000000000000000;
      1490:stage_word=128'h00000000000000000000000000000000;
      1491:stage_word=128'h00000000000000000000000000000000;
      1492:stage_word=128'h00000000000000000000000000000000;
      1493:stage_word=128'h00000000000000000000000000000000;
      1494:stage_word=128'h00000000000000000000000000000000;
      1495:stage_word=128'h00000000000000000000000000000000;
      1496:stage_word=128'h00000000000000000000000000000000;
      1497:stage_word=128'h00000000000000000000000000000000;
      1498:stage_word=128'h00000000000000000000000000000000;
      1499:stage_word=128'h80007ffffc000c00040002000000f800;
      2512:stage_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      2513:stage_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      2514:stage_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      2515:stage_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      2516:stage_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      2517:stage_word=128'h00000000000000000000000000000000;
      2518:stage_word=128'h00000000000000000000000000000000;
      2519:stage_word=128'h00000000000000000000000000000000;
      2520:stage_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      2521:stage_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      2522:stage_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      2523:stage_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      3536:stage_word=128'h80008000800080008000800080008000;
      3537:stage_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      3538:stage_word=128'h80008000800080008000800080008000;
      3539:stage_word=128'h80008000800080008000800080008000;
      3540:stage_word=128'h00000000000000000000000000000000;
      3541:stage_word=128'h00000000000000000000000000000000;
      3542:stage_word=128'h00000000000000000000000000000000;
      3543:stage_word=128'h00000000000000000000000000000000;
      3544:stage_word=128'h00000000000000000000000000000000;
      3545:stage_word=128'h80008000800080008000800080008000;
      3546:stage_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
      3547:stage_word=128'h80008000800080008000800080008000;
      4560:stage_word=128'h02edfe5d0144fe1100f8037500fe0329;
      4561:stage_word=128'h00d002fbfa2602b0fc3402fcfe6c0153;
      4562:stage_word=128'hfcb902a5ffb90071fda901a303cdfb8f;
      4563:stage_word=128'hfcb902a5ffb90071fda901a303cdfb8f;
      4564:stage_word=128'h0067ff84feedff81ff7c01d0ffc800b8;
      4565:stage_word=128'h00000000000000000000000000000000;
      4566:stage_word=128'h00000000000000000000000000000000;
      4567:stage_word=128'h00000000000000000000000000000000;
      4568:stage_word=128'hffda0004001c0021001d0023005c0063;
      4569:stage_word=128'hfc9302a9ffd50092fdc601c60429fbf2;
      4570:stage_word=128'hfb3af472fecaff5bfae3000002c50cf0;
      4571:stage_word=128'h0400f4000c00fc00060000000200f800;
      5584:stage_word=128'h00000000000000000000000000000000;
      5585:stage_word=128'h00000000000000000000000000000000;
      5586:stage_word=128'h80007ffffff1000ffff90007ffff0001;
      5587:stage_word=128'h80007ffffff1000ffff90007ffff0001;
      5588:stage_word=128'h00000000000000000000000000000000;
      5589:stage_word=128'h00000000000000000000000000000000;
      5590:stage_word=128'h00000000000000000000000000000000;
      5591:stage_word=128'h00000000000000000000000000000000;
      5592:stage_word=128'h00000000000000000000000000000000;
      5593:stage_word=128'h80007ffffff1000ffff90007ffff0001;
      5594:stage_word=128'h00000000000000000000000000000000;
      5595:stage_word=128'h00000000000000000000000000000000;
      6608:stage_word=128'h0003055201c60000000000000e33f8e6;
      6609:stage_word=128'h00000e3307280003faa301c600000000;
      6610:stage_word=128'h00133ffbc00300010000ffff7fff8000;
      6611:stage_word=128'h00133ffbc00300010000ffff7fff8000;
      6612:stage_word=128'h00000eef01ee00000000000000000000;
      6613:stage_word=128'h00000000000000000000000000000000;
      6614:stage_word=128'h00000000000000000000000000000000;
      6615:stage_word=128'h00000000000000000000000000000000;
      6616:stage_word=128'hfd010089fdaa0131fe5201dafe080283;
      6617:stage_word=128'hfd144084bdad0132fe5201d97e078283;
      6618:stage_word=128'h0003055d01ca0000000000000e50f8d8;
      6619:stage_word=128'h0c000600fe0002000000fc0008000400;
      7632:stage_word=128'h0eba7fff94bf8960b62d76b083fa87bc;
      7633:stage_word=128'hd41c7fff4114f8eed6c77fffa8bf6566;
      7634:stage_word=128'h627b0c04772da1b730a56378a9f258c3;
      7635:stage_word=128'h627b0c04772da1b730a56378a9f258c3;
      7636:stage_word=128'h80007fff0000000000007fff00000000;
      7637:stage_word=128'h00000000000000000000000000000000;
      7638:stage_word=128'h00000000000000000000000000000000;
      7639:stage_word=128'h00000000000000000000000000000000;
      7640:stage_word=128'h0b007fff6b000b00d90091017fffd300;
      7641:stage_word=128'h6d7b7fff7fffacb709a5f47929f12bc3;
      7642:stage_word=128'h6eddfff940c59710f3e07b34f6d517d3;
      7643:stage_word=128'h61e2ffd02f4160c6ea546bb209431756;
      8656:stage_word=128'h75b37fffea763e6c1f3c7fffe256f55d;
      8657:stage_word=128'h8508f7dd7ffffc5fc4b1b247c682914e;
      8658:stage_word=128'h1f939897cfeaf22f329d943b24e35573;
      8659:stage_word=128'h1f939897cfeaf22f329d943b24e35573;
      8660:stage_word=128'h80008000fce0c75f800080000048133e;
      8661:stage_word=128'h00000000000000000000000000000000;
      8662:stage_word=128'h00000000000000000000000000000000;
      8663:stage_word=128'h00000000000000000000000000000000;
      8664:stage_word=128'h80001a2648067755a8f6026041277fff;
      8665:stage_word=128'h9f93b2bd17f06984db93969b660a7fff;
      8666:stage_word=128'hfdce6b70f459fcb33543027afefe8000;
      8667:stage_word=128'hfb45b950107d103f4799fe70fe25910b;
      9680:stage_word=128'h00000000000000000000000000000000;
      9681:stage_word=128'h00000000000000000000000000000000;
      9682:stage_word=128'h0043ffc50033ffd50023ffe50013000b;
      9683:stage_word=128'h0043ffc50033ffd50023ffe50013000b;
      9684:stage_word=128'h00000000000000000000000000000000;
      9685:stage_word=128'h00000000000000000000000000000000;
      9686:stage_word=128'h00000000000000000000000000000000;
      9687:stage_word=128'h00000000000000000000000000000000;
      9688:stage_word=128'h00000000000000000000000000000000;
      9689:stage_word=128'h0043ffc50033ffd50023ffe50013000b;
      9690:stage_word=128'h00000000000000000000000000000000;
      9691:stage_word=128'h00000000000000000000000000000000;
      default:stage_word=128'hbad;
    endcase end
  endfunction
  function automatic [127:0] norm_word;input integer vector_no;begin case(vector_no)
    0:norm_word=128'hf65604d5fda401d0fecb00ebffb20004;
    1:norm_word=128'h00000000000000000000000000000000;
    2:norm_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
    3:norm_word=128'h7fff7fff7fff7fff7fff7fff7fff7fff;
    4:norm_word=128'hfb3af472fecaff5bfae3000002c50cf0;
    5:norm_word=128'h00000000000000000000000000000000;
    6:norm_word=128'h0003055d01ca0000000000000e50f8d8;
    7:norm_word=128'h6eddfff940c59710f3e07b34f6d517d3;
    8:norm_word=128'hfdce6b70f459fcb33543027afefe8000;
    9:norm_word=128'h00000000000000000000000000000000;
    default:norm_word=0;endcase end endfunction
  function automatic expected_sat;input integer vector_no;begin case(vector_no)
    0:expected_sat=1'b0;
    1:expected_sat=1'b0;
    2:expected_sat=1'b1;
    3:expected_sat=1'b1;
    4:expected_sat=1'b0;
    5:expected_sat=1'b0;
    6:expected_sat=1'b0;
    7:expected_sat=1'b1;
    8:expected_sat=1'b1;
    9:expected_sat=1'b0;
    default:expected_sat=1'bx;endcase end endfunction

  reg clk=0; always #5 clk=~clk;
  reg reset=1,abort=0,in_valid=0,start_valid=0,done_ready=0,out_ready=0;
  reg [127:0] in_data=0;
  wire in_ready,input_stored,start_ready,busy,done_valid,done_error,done_saturated,out_valid,out_last;
  wire [127:0] out_data; wire [9:0] out_index;
  block_w4_f16_top dut(.*);
  integer cycles=0,cases=0,v=0,ingress=0,sreq=0,sack=0,writes=0,reads=0;
  integer mcmd=0,mrsp=0,loads=0,ldone=0,abeats=0,bbeats=0,ecmd=0,ersp=0,gcmd=0,grsp=0;
  integer enative=0,gnative=0,gretired=0,tbegin=0,twrite=0,tcommit=0,ttake=0,trelease=0,starts=0,dtake=0;
  integer i0,q0,a0,w0,r0,mc0,mr0,l0,ld0,ab0,bb0,e0,er0,g0,gr0,en0,gn0,go0,tb0,tw0,tc0,tt0,tr0,st0;
  integer nservice=0,nservice_rsp=0,ncommands=0,nresponses=0,ns0,nr0,nc0,np0,norm_acks=0;
  integer stage_acks[0:11]; integer frame_ingress_acks=0,frame_ingress_reqs=0,run_writes=0,run_reads=0;
  reg frame_open=0,job=0,pending=0,pending_write;reg [9:0] pending_addr;reg [127:0] pending_data;
  reg hold_out=0,hold_done=0,hold_s=0,hold_m=0,hold_e=0,hold_g=0,hold_in=0;
  reg [127:0] prev_out,prev_s,prev_m,prev_in;reg [9:0] prev_index;
  reg prev_last,prev_de,prev_ds,prev_ee,prev_es,prev_ge,prev_gs;
  reg load_completed=0; integer projection_execs=0;

  function automatic [127:0] raw_word;
    input integer vector_no,beat;reg [127:0] word;
    begin word=input_word(vector_no,beat);
      if(beat>=1&&beat<4)word=128'hfedcba98765432100123456789abcdef;
      raw_word=word;
    end
  endfunction
  function automatic signed [7:0] byte_at;
    input integer vector_no,base,offset;reg [127:0] word;
    begin word=input_word(vector_no,base+offset/16);byte_at=word[8*(offset%16)+:8];end
  endfunction
  function automatic signed [15:0] projection_byte;
    input integer vector_no,lane;reg [127:0] word;
    begin word=norm_word(vector_no);projection_byte=$signed(word[16*lane+:16]);end
  endfunction
  function automatic signed [15:0] stage_lane;
    input integer vector_no,address,lane;reg [127:0] word;
    begin word=stage_word(vector_no,address);stage_lane=word[16*lane+:16];end
  endfunction
  function automatic signed [63:0] rne64;
    input signed [63:0] value;input integer shift;reg signed [63:0] q;reg [63:0] remn,half;
    begin if(shift==0)rne64=value;else begin q=value>>>shift;remn=$unsigned(value)&((64'd1<<shift)-1);half=64'd1<<(shift-1);rne64=q+((remn>half)||((remn==half)&&q[0]));end end
  endfunction
  function automatic signed [15:0] clip16;
    input signed [63:0] value;
    begin if(value>32767)clip16=32767;else if(value< -32768)clip16=-32768;else clip16=value[15:0];end
  endfunction
  task automatic crosscheck_frozen;
    input integer nvec;integer n,k;reg signed [63:0] sg,su,sd;reg signed [15:0] residual;
    begin for(n=0;n<8;n=n+1)begin sg=0;su=0;sd=0;
      for(k=0;k<8;k=k+1)begin
        sg=sg+projection_byte(nvec,k)*byte_at(nvec,4,8*n+k);
        su=su+projection_byte(nvec,k)*byte_at(nvec,8,8*n+k);
        sd=sd+stage_lane(nvec,468,k)*byte_at(nvec,12,8*n+k);
      end
      residual=stage_lane(nvec,466,n);
      if(clip16(rne64(sg,7))!==stage_lane(nvec,464,n)||clip16(rne64(su,7))!==stage_lane(nvec,465,n)||
         clip16(rne64(sd,7))!==stage_lane(nvec,472,n)||residual!==stage_lane(nvec,467,n)||
         clip16($signed(stage_lane(nvec,472,n))+$signed(residual))!==stage_lane(nvec,473,n))
        $fatal(1,"FAIL_F16 independent S16M/RNE7/original residual formula mismatch");
    end end
  endtask
  function automatic [127:0] ram_word;
    input integer address;
    begin case(address%4)
      0:ram_word=dut.u_s.storage.bank0[address/4];1:ram_word=dut.u_s.storage.bank1[address/4];
      2:ram_word=dut.u_s.storage.bank2[address/4];3:ram_word=dut.u_s.storage.bank3[address/4];
    endcase end
  endfunction

  always @(posedge clk)begin
    cycles=cycles+1;if(cycles>300000)$fatal(1,"FAIL_F16 FFN watchdog");
    // DONE is a public transaction and survives leaf abort/internal reset.
    if(reset)hold_done=0;else begin
      if(hold_done&&(!done_valid||done_error!==prev_de||done_saturated!==prev_ds))$fatal(1,"FAIL_F16 DONE changed under stall/abort");
      hold_done=done_valid&&!done_ready;prev_de=done_error;prev_ds=done_saturated;
      if(done_valid&&done_ready)dtake=dtake+1;
    end
    if(reset||dut.leaf_reset)begin hold_out=0;hold_s=0;hold_m=0;hold_e=0;hold_g=0;hold_in=0;pending=0;end
    else begin
      if(hold_in&&(!in_valid||in_data!==prev_in))$fatal(1,"FAIL_F16 TB ingress changed while stalled");
      if(hold_out&&(!out_valid||out_data!==prev_out||out_index!==prev_index||out_last!==prev_last))$fatal(1,"FAIL_F16 output stall");
      if(hold_s&&(!dut.s_valid||dut.s_dout!==prev_s))$fatal(1,"FAIL_F16 S ACK stall");
      if(hold_m&&(!dut.m_rsp_valid||dut.m_rsp_data!==prev_m))$fatal(1,"FAIL_F16 M response stall");
      if(hold_e&&(!dut.e_rsp_valid||dut.e_rsp_error!==prev_ee||dut.e_rsp_saturated!==prev_es))$fatal(1,"FAIL_F16 E response stall");
      if(hold_g&&(!dut.g_rsp_valid||dut.g_rsp_error!==prev_ge||dut.g_rsp_saturated!==prev_gs))$fatal(1,"FAIL_F16 G response stall");
      hold_in=in_valid&&!in_ready;prev_in=in_data;
      hold_out=out_valid&&!out_ready;prev_out=out_data;prev_index=out_index;prev_last=out_last;
      hold_s=dut.s_valid&&!dut.s_take;prev_s=dut.s_dout;
      hold_m=dut.m_rsp_valid&&!dut.m_rsp_ready;prev_m=dut.m_rsp_data;
      hold_e=dut.e_rsp_valid&&!dut.e_rsp_ready;prev_ee=dut.e_rsp_error;prev_es=dut.e_rsp_saturated;
      hold_g=dut.g_rsp_valid&&!dut.g_rsp_ready;prev_ge=dut.g_rsp_error;prev_gs=dut.g_rsp_saturated;
      if(in_valid&&in_ready)begin if(!frame_open||job||ingress-i0>=17)$fatal(1,"FAIL_F16 ingress ownership");ingress=ingress+1;end
      if(dut.s_req&&dut.s_ready)begin
        if(pending)$fatal(1,"FAIL_F16 two ordinary S owners");pending=1;pending_addr=dut.s_addr;pending_write=dut.s_we;pending_data=dut.s_din;sreq=sreq+1;
        if(dut.s_we)begin writes=writes+1;
          if(dut.s_addr==448&&job)begin
            if(dut.s_din!==norm_word(v))$fatal(1,"FAIL_F16 complete S16 norm overwrite originalA");run_writes=run_writes+1;
          end else if((dut.s_addr>=448&&dut.s_addr<=463)||(dut.s_addr==475&&!job))begin
            if(job||dut.s_addr!==(frame_ingress_reqs<16?448+frame_ingress_reqs:475)||dut.s_din!==input_word(v,frame_ingress_reqs))$fatal(1,"FAIL_F16 input order/canonical/literal clobber");frame_ingress_reqs=frame_ingress_reqs+1;
          end else if(dut.s_addr>=464&&dut.s_addr<=475)begin
            if(!job||dut.s_din!==stage_word(v,dut.s_addr))$fatal(1,"FAIL_F16 stage%0d data=%032h expected=%032h",dut.s_addr,dut.s_din,stage_word(v,dut.s_addr));run_writes=run_writes+1;
          end else $fatal(1,"FAIL_F16 unexpected S write");
        end else begin reads=reads+1;run_reads=run_reads+1;if(!job||dut.s_addr<464||dut.s_addr>475)$fatal(1,"FAIL_F16 unexpected S read");end
      end
      if(dut.s_valid&&dut.s_take)begin
        if(!pending)$fatal(1,"FAIL_F16 S ACK without owner");
        if(pending_write&&dut.s_dout!==pending_data)$fatal(1,"FAIL_F16 write echo ACK");
        if(!pending_write&&dut.s_dout!==stage_word(v,pending_addr))$fatal(1,"FAIL_F16 S stage read mismatch");
        if(pending_write&&(pending_addr<464||pending_addr==475)&&!job)frame_ingress_acks=frame_ingress_acks+1;
        if(pending_write&&pending_addr==448&&job)norm_acks=norm_acks+1;
        if(pending_write&&pending_addr>=464)stage_acks[pending_addr-464]=stage_acks[pending_addr-464]+1;
        pending=0;sack=sack+1;
      end
      if(input_stored&&(ingress-i0!=17||frame_ingress_acks!=17||(!job&&pending)))$fatal(1,"FAIL_F16 marker before17 input/ACK");
      if(start_ready&&!input_stored)$fatal(1,"FAIL_F16 early ready");
      if(start_valid&&start_ready)begin if(job||!input_stored||frame_ingress_acks!=17)$fatal(1,"FAIL_F16 early/duplicate start");job=1;starts=starts+1;end
      if(dut.load_valid&&dut.load_ready)begin
        if(!job||loads-l0>2)$fatal(1,"FAIL_F16 loader lifecycle");
        if(dut.u_s.load_a_wide!==1'b1||dut.u_s.load_b_wide||dut.u_s.load_rows!=1||dut.u_s.load_tiles!=1)$fatal(1,"FAIL_F16 loader format");
        load_completed=0;loads=loads+1;
      end
      if(dut.load_done_valid&&dut.load_done_take)begin ldone=ldone+1;load_completed=!dut.load_done_error;end
      if(dut.a_valid&&dut.a_ready)begin
        if(dut.a_data!==(loads-l0==3?stage_word(v,468):norm_word(v)))$fatal(1,"FAIL_F16 loader A payload");abeats=abeats+1;
      end
      if(dut.b_valid&&dut.b_ready)bbeats=bbeats+1;
      if(dut.m_cmd_valid&&dut.m_cmd_ready)begin
        if(!job)$fatal(1,"FAIL_F16 M before start");mcmd=mcmd+1;
        if(dut.m_cmd_op==10)begin if(!load_completed)$fatal(1,"FAIL_F16 EXEC before load done");projection_execs=projection_execs+1;end
      end
      if(dut.m_rsp_valid&&dut.m_rsp_ready)mrsp=mrsp+1;
      if(dut.n_req_valid&&dut.n_req_ready)nservice=nservice+1;
      if(dut.n_rsp_valid&&dut.n_rsp_ready)begin
        if(!dut.n_rsp_error&&stage_acks[10]!=1)$fatal(1,"FAIL_F16 N completion before474ACK");nservice_rsp=nservice_rsp+1;
      end
      if(dut.n_cmd_valid&&dut.n_cmd_ready)begin
        if(dut.owner!=3)$fatal(1,"FAIL_F16 N service lost S owner");
        if(dut.n_cmd_op==1||dut.n_cmd_op==5)begin
          if(dut.n_cmd_count!=8||dut.n_cmd_data!==stage_word(v,466))$fatal(1,"FAIL_F16 raw originalX replay");
          if(dut.n_cmd_op==5&&dut.n_cmd_aux!==stage_word(v,475))$fatal(1,"FAIL_F16 gamma");
        end
        ncommands=ncommands+1;
      end
      if(dut.n_native_rsp_valid&&dut.n_native_rsp_ready)nresponses=nresponses+1;
      if(dut.e_req_valid&&dut.e_req_ready)ecmd=ecmd+1;
      if(dut.e_rsp_valid&&dut.e_rsp_ready)begin
        if(!dut.e_rsp_error&&stage_acks[dut.e_final?9:3]!=1)$fatal(1,"FAIL_F16 E completion before destination ACK");ersp=ersp+1;
      end
      if(dut.g_req_valid&&dut.g_req_ready)gcmd=gcmd+1;
      if(dut.g_rsp_valid&&dut.g_rsp_ready)begin if(!dut.g_rsp_error&&stage_acks[4]!=1)$fatal(1,"FAIL_F16 G completion before destination ACK");grsp=grsp+1;end
      if(dut.e_in_valid&&dut.e_in_ready)enative=enative+1;
      if(dut.g_in_valid&&dut.g_in_ready)gnative=gnative+1;
      if(dut.g_out_valid&&dut.g_out_ready)gretired=gretired+1;
      if(dut.u_t.begin_valid&&dut.u_t.begin_ready)tbegin=tbegin+1;
      if(dut.u_t.write_valid&&dut.u_t.write_ready)begin if(dut.u_t.write_index!=0||dut.u_t.write_data!==stage_word(v,473))$fatal(1,"FAIL_F16 T data/index");twrite=twrite+1;end
      if(dut.u_t.commit_valid&&dut.u_t.commit_ready)tcommit=tcommit+1;
      if(out_valid&&out_ready)begin if(ttake-tt0!=0||out_index!=0||!out_last||out_data!==stage_word(v,473))$fatal(1,"FAIL_F16 final oracle");ttake=ttake+1;end
      if(dut.u_t.release_valid&&dut.u_t.release_ready)trelease=trelease+1;
    end
  end
  task automatic mark;
    input [8*100-1:0] name;
    begin cases=cases+1;$display("CASE_PASS %0s",name);end
  endtask
  task automatic new_frame;
    input integer nv;integer k;
    begin @(negedge clk);if(busy||done_valid||input_stored||out_valid||!in_ready||start_ready)$fatal(1,"FAIL_F16 nonempty frame");
      v=nv;crosscheck_frozen(v);frame_open=1;job=0;load_completed=0;projection_execs=0;frame_ingress_acks=0;frame_ingress_reqs=0;run_writes=0;run_reads=0;
      for(k=0;k<12;k=k+1)stage_acks[k]=0;norm_acks=0;ns0=nservice;nr0=nservice_rsp;nc0=ncommands;np0=nresponses;
      i0=ingress;q0=sreq;a0=sack;w0=writes;r0=reads;mc0=mcmd;mr0=mrsp;l0=loads;ld0=ldone;ab0=abeats;bb0=bbeats;e0=ecmd;er0=ersp;g0=gcmd;gr0=grsp;en0=enative;gn0=gnative;go0=gretired;tb0=tbegin;tw0=twrite;tc0=tcommit;tt0=ttake;tr0=trelease;st0=starts;
      in_valid=0;start_valid=0;out_ready=0;done_ready=0;
      // Dirty A padding and mid padding are overwritten, never supplied by reset.
      dut.u_s.storage.bank0[112]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank1[112]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank2[112]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank3[112]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank1[117]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank2[117]=128'hffffffffffffffffffffffffffffffff;
      dut.u_s.storage.bank3[117]=128'hffffffffffffffffffffffffffffffff;
    end
  endtask
  task automatic send;
    input integer beat;
    begin @(negedge clk);in_valid=1;in_data=raw_word(v,beat);while(!in_ready)@(negedge clk);@(posedge clk);#1;if(!busy)$fatal(1,"FAIL_F16 accepted ingress not busy");@(negedge clk);in_valid=0;end
  endtask
  task automatic fill;
    integer beat;
    begin for(beat=0;beat<17;beat=beat+1)send(beat);while(!input_stored)@(negedge clk);if(frame_ingress_acks!=17||!busy||in_ready)$fatal(1,"FAIL_F16 incomplete stored frame");end
  endtask
  task automatic start_job;
    input hold_start;
    begin @(negedge clk);if(!start_ready)$fatal(1,"FAIL_F16 not start ready");start_valid=1;@(posedge clk);#1;@(negedge clk);if(starts-st0!=1||!busy||start_ready)$fatal(1,"FAIL_F16 start acceptance");if(!hold_start)start_valid=0;end
  endtask
  task automatic take_output;
    integer j;
    begin while(!out_valid)@(negedge clk);for(j=0;j<7;j=j+1)begin if(out_data!==stage_word(v,473)||out_index!=0||!out_last)$fatal(1,"FAIL_F16 held output");@(negedge clk);end
      out_ready=1;@(posedge clk);#1;@(negedge clk);out_ready=0;
    end
  endtask
  task automatic finish;
    input error_expected,abort_at_done;integer j,before_take;
    begin while(!done_valid)@(negedge clk);
      for(j=0;j<5;j=j+1)begin
        if(!done_valid||done_error!==error_expected||in_ready||start_ready||!busy)$fatal(1,"FAIL_F16 retained completion");
        if(!error_expected&&done_saturated!==expected_sat(v))$fatal(1,"FAIL_F16 accumulated saturation");@(negedge clk);
      end
      if(!error_expected&&(ttake-tt0!=1||trelease-tr0!=1||dut.t_busy))$fatal(1,"FAIL_F16 completion before T release");
      before_take=dtake;start_valid=0;done_ready=1;abort=abort_at_done;
      @(posedge clk);#1;@(negedge clk);done_ready=0;abort=0;frame_open=0;job=0;repeat(3)@(negedge clk);
      if(dtake!=before_take+1||busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_F16 duplicate or stale completion");
    end
  endtask
  task automatic normal_counts;
    integer k;
    begin
      if(ingress-i0!=17||frame_ingress_acks!=17||sreq-q0!=39||sack-a0!=39||writes-w0!=29||reads-r0!=10||run_writes!=12||run_reads!=10||pending)$fatal(1,"FAIL_F16 39 S/29write/10read counts");
      if(mcmd-mc0!=15||mrsp-mr0!=15||projection_execs!=3||loads-l0!=3||ldone-ld0!=3||abeats-ab0!=3||bbeats-bb0!=3)$fatal(1,"FAIL_F16 projection counts");
      if(ecmd-e0!=2||ersp-er0!=2||gcmd-g0!=1||grsp-gr0!=1||enative-en0!=2||gnative-gn0!=4||gretired-go0!=4)$fatal(1,"FAIL_F16 native/adapter counts");
      if(tbegin-tb0!=1||twrite-tw0!=1||tcommit-tc0!=1||ttake-tt0!=1||trelease-tr0!=1||starts-st0!=1)$fatal(1,"FAIL_F16 T counts");
      if(nservice-ns0!=1||nservice_rsp-nr0!=1||ncommands-nc0!=4||nresponses-np0!=4||norm_acks!=1||ram_word(448)!==norm_word(v))$fatal(1,"FAIL_F16 N/narrow counts");
      for(k=0;k<12;k=k+1)if(stage_acks[k]!=1||ram_word(464+k)!==stage_word(v,464+k))$fatal(1,"FAIL_F16 final intermediate RAM%0d",464+k);
    end
  endtask
  task automatic run_normal;
    input integer nv;
    begin new_frame(nv);fill();start_job(0);take_output();finish(0,0);normal_counts();end
  endtask
  task automatic prestart_abort;
    begin @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;in_valid=0;start_valid=0;frame_open=0;job=0;repeat(3)@(negedge clk);
      if(busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_F16 prestart abort fabricated done");
    end
  endtask
  task automatic hard_reset;
    begin @(negedge clk);reset=1;in_valid=0;start_valid=0;out_ready=0;done_ready=0;repeat(3)@(negedge clk);reset=0;frame_open=0;job=0;repeat(3)@(negedge clk);
      if(busy||done_valid||input_stored||out_valid||start_ready||!in_ready)$fatal(1,"FAIL_F16 hard reset stale lifecycle");end
  endtask
  integer beat,k;
  initial begin
    repeat(4)@(negedge clk);reset=0;@(negedge clk);
    new_frame(0);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);
    start_valid=1;repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0||mcmd!=mc0)$fatal(1,"FAIL_F16 early pending ACK start");end
    start_valid=0;release dut.permit_s_rsp;for(beat=1;beat<16;beat=beat+1)send(beat);
    while(frame_ingress_acks<16)@(negedge clk);force dut.permit_s_rsp=1'b0;send(16);while(!dut.s_valid)@(negedge clk);
    start_valid=1;repeat(5)begin @(negedge clk);if(input_stored||start_ready||starts!=st0)$fatal(1,"FAIL_F16 last input accept before ACK");end
    start_valid=0;release dut.permit_s_rsp;while(!input_stored)@(negedge clk);repeat(3)@(negedge clk);
    if(starts!=st0)$fatal(1,"FAIL_F16 early start pulse queued");
    for(beat=0;beat<17;beat=beat+1)if(ram_word(beat<16?448+beat:475)!==input_word(v,beat))$fatal(1,"FAIL_F16 canonical ingress RAM");
    mark("F16_INPUT17_STORED_AND_PADDING_ACK_GATE");
    start_job(1);take_output();finish(0,0);normal_counts();mark("F16_H8I8_NORMAL_STAGES_COUNTS_HELD_START");
    run_normal(1);mark("F16_ZERO_X_VARIABLE_GAMMA");run_normal(2);mark("F16_POSITIVE_EXTREME_SATURATION");
    run_normal(3);mark("F16_NEGATIVE_EXTREME_SATURATION");run_normal(4);mark("F16_SIGNED_NONUNITY_GAMMA");run_normal(5);mark("F16_ZERO_GAMMA_PRESERVES_FULL_S16_X");
    run_normal(6);mark("F16_SPARSE_LAYOUT");run_normal(7);mark("F16_SEEDED_RANDOM_0");
    run_normal(8);mark("F16_SEEDED_RANDOM_1");run_normal(9);mark("F16_ZERO_GAMMA_NON8_RESIDUAL");
    new_frame(4);for(beat=0;beat<16;beat=beat+1)send(beat);while(frame_ingress_acks<16)@(negedge clk);
    force dut.permit_s_rsp=1'b0;send(16);start_valid=1;repeat(4)@(negedge clk);
    if(starts!=st0||input_stored)$fatal(1,"FAIL_F16 held start early");release dut.permit_s_rsp;while(starts==st0)@(negedge clk);start_valid=0;
    take_output();finish(0,0);normal_counts();mark("F16_HELD_START_AFTER_FINAL_ACK_REPEAT");
    new_frame(0);force dut.permit_s_req=1'b0;send(0);repeat(4)@(negedge clk);prestart_abort();release dut.permit_s_req;run_normal(4);mark("F16_ABORT_CAPTURED_BEFORE_S_ACCEPT_RECOVER");
    new_frame(3);force dut.permit_s_rsp=1'b0;send(0);while(!dut.s_valid)@(negedge clk);prestart_abort();release dut.permit_s_rsp;run_normal(0);mark("F16_ABORT_INPUT_PENDING_ACK_RECOVER");
    new_frame(2);fill();prestart_abort();run_normal(5);mark("F16_ABORT_COMPLETE_PRESTART_RECOVER");
    new_frame(4);fill();force dut.permit_s_rsp=1'b0;start_job(0);while(!dut.s_valid)@(negedge clk);
    @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;finish(1,0);run_normal(1);mark("F16_ABORT_RUN_S_ACK_RECOVER");
    new_frame(2);fill();start_job(0);take_output();abort=1;@(posedge clk);#1;@(negedge clk);abort=0;
    if(ttake-tt0!=1)$fatal(1,"FAIL_F16 consumed output retracted");finish(1,0);run_normal(4);mark("F16_ABORT_AFTER_CONSUMED_PREFIX_RECOVER");
    new_frame(2);fill();start_job(0);take_output();while(!done_valid)@(negedge clk);
    @(negedge clk);abort=1;repeat(3)begin @(negedge clk);if(!done_valid||done_error||!done_saturated)$fatal(1,"FAIL_F16 existing DONE flags changed");end
    abort=0;finish(0,1);normal_counts();mark("F16_DONE_ABORT_READY_EXACTLY_ONCE_SAT_HOLD");
    new_frame(4);send(0);send(1);hard_reset();run_normal(3);mark("F16_RESET_PARTIAL_INPUT_RECOVER");
    new_frame(4);fill();force dut.permit_g_rsp=1'b0;start_job(0);while(!dut.g_rsp_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();release dut.permit_g_rsp;run_normal(0);mark("F16_RESET_RETAINED_G_RESPONSE_RECOVER");
    new_frame(4);fill();start_job(0);while(!out_valid)@(negedge clk);repeat(5)@(negedge clk);hard_reset();run_normal(5);mark("F16_RESET_COMMITTED_T_STALL_RECOVER");
    new_frame(4);fill();start_job(0);wait(dut.state==5&&dut.m_phase==2);
    @(negedge clk);force dut.m_cmd_data=64'h988c;@(posedge clk);#1;@(negedge clk);release dut.m_cmd_data;
    finish(1,0);if(ttake!=tt0)$fatal(1,"FAIL_F16 error published output");run_normal(3);mark("F16_NATIVE_EXEC_ERROR_RECOVER");
    // Actual newly integrated native E error, not a fabricated adapter flag.
    new_frame(4);fill();start_job(0);wait(dut.e_in_valid&&dut.e_in_ready);
    @(negedge clk);force dut.e_in_op=4'd14;@(posedge clk);#1;@(negedge clk);release dut.e_in_op;
    finish(1,0);if(ttake!=tt0||twrite!=tw0||stage_acks[3]!=0)$fatal(1,"FAIL_F16 native E error wrote residual/output");
    run_normal(5);mark("F16_NATIVE_E_ERROR_NO_WRITE_RECOVER");
    // One invalid G beat among valid beats must error the whole service only
    // after every accepted pair is retired; no partial mid/T publication.
    new_frame(4);fill();start_job(0);wait(dut.g_in_valid&&dut.g_in_ready);
    @(negedge clk);force dut.g_in_fn=3'd4;@(posedge clk);#1;@(negedge clk);release dut.g_in_fn;
    finish(1,0);if(gnative-gn0!=4||gretired-go0!=4||stage_acks[4]!=0||ttake!=tt0||twrite!=tw0)$fatal(1,"FAIL_F16 native G error did not drain or wrote mid/output");
    run_normal(3);mark("F16_ONE_NATIVE_G_BEAT_ERROR_DRAIN_NO_WRITE_RECOVER");
    // E/G response stalls are real held service outputs after destination ACK.
    new_frame(4);fill();force dut.permit_e_rsp=1'b0;start_job(0);while(!dut.e_rsp_valid)@(negedge clk);repeat(6)@(negedge clk);release dut.permit_e_rsp;
    force dut.permit_g_rsp=1'b0;while(!dut.g_rsp_valid)@(negedge clk);repeat(6)@(negedge clk);release dut.permit_g_rsp;
    take_output();finish(0,0);normal_counts();mark("F16_E_G_RESPONSE_HOLD_AFTER_REAL_WRITE_ACK");
    new_frame(4);fill();force dut.permit_n_rsp=1'b0;start_job(0);while(!dut.n_rsp_valid)@(negedge clk);repeat(6)@(negedge clk);
    if(stage_acks[10]!=1||norm_acks!=0||mcmd!=mc0)$fatal(1,"FAIL_F16 N completed but top consumed early");release dut.permit_n_rsp;
    take_output();finish(0,0);normal_counts();mark("F16_N_SERVICE_RESPONSE_HOLD_AFTER474ACK");
    new_frame(4);fill();start_job(0);wait(dut.n_cmd_valid&&dut.n_cmd_ready&&dut.n_cmd_op==1);
    @(negedge clk);force dut.n_cmd_op=4'd15;@(posedge clk);#1;@(negedge clk);release dut.n_cmd_op;
    finish(1,0);if(stage_acks[10]!=0||norm_acks!=0||mcmd!=mc0||twrite!=tw0)$fatal(1,"FAIL_F16 native N error escaped preNorm");
    run_normal(5);mark("F16_NATIVE_N_ERROR_NO_PROJECTION_COORDINATED_RECOVER");
    new_frame(4);fill();force dut.permit_n_rsp=1'b0;start_job(0);while(!dut.n_rsp_valid)@(negedge clk);repeat(4)@(negedge clk);hard_reset();release dut.permit_n_rsp;
    run_normal(0);mark("F16_RESET_HELD_N_SERVICE_RESPONSE_RECOVER");
    new_frame(4);fill();start_job(0);wait(dut.n_mem_req_valid&&dut.n_mem_req_write&&dut.n_mem_req_addr==474);
    force dut.permit_s_rsp=1'b0;while(!dut.s_valid)@(negedge clk);repeat(4)@(negedge clk);
    if(stage_acks[10]!=0||norm_acks!=0||mcmd!=mc0)$fatal(1,"FAIL_F16 N finalwrite missingACK early projection");
    @(negedge clk);abort=1;@(posedge clk);#1;@(negedge clk);abort=0;release dut.permit_s_rsp;
    finish(1,0);run_normal(1);mark("F16_ABORT_N_DESTINATION_ACK_COORDINATED_RECOVER");
    // Helper has no native S error output. Inject its defined service-error
    // boundary, after a real accepted write, to check partial/no-output recovery.
    new_frame(4);fill();start_job(0);wait(dut.h_rsp_valid&&dut.h_rsp_ready&&dut.owner==0);
    @(negedge clk);force dut.h_rsp_error=1'b1;@(posedge clk);#1;@(negedge clk);release dut.h_rsp_error;
    finish(1,0);if(twrite!=tw0||ttake!=tt0)$fatal(1,"FAIL_F16 S helper response error published output");
    run_normal(9);mark("F16_S_SERVICE_ERROR_NO_OUTPUT_RECOVER");
    $display("F16_STATS cycles=%0d input=%0d Sreq=%0d Sack=%0d Mcmd=%0d Mrsp=%0d Ncmd=%0d Nrsp=%0d Ttake=%0d",cycles,ingress,sreq,sack,mcmd,mrsp,ncommands,nresponses,ttake);
    $display("PASS_W4_F16 cases=%0d",cases);$finish;
  end

endmodule
