`timescale 1ns/1ps
// Independent generated math expectations, real leaf N/S/helper.
module block_w4_n_tb;
 function automatic [127:0] n_raw;input integer vec,word;begin case(vec*64+word)
  0:n_raw=128'hff800070ffa00050ffc00030ffe00010;
  64:n_raw=128'h00000000000000000000000000000000;
  128:n_raw=128'h000700000001ffff7fff80007fff8000;
  192:n_raw=128'h00000000000000000000000000008000;
  256:n_raw=128'h9b43975e93798f948baf87ca83e58000;
  257:n_raw=128'hba6bb686b2a1aebcaad7a6f2a30d9f28;
  258:n_raw=128'hd993d5aed1c9cde4c9ffc61ac235be50;
  259:n_raw=128'hf8bbf4d6f0f1ed0ce927e542e15ddd78;
  260:n_raw=128'h17e313fe10190c34084f046a0085fca0;
  261:n_raw=128'h370b33262f412b5c277723921fad1bc8;
  262:n_raw=128'h5633524e4e694a84469f42ba3ed53af0;
  263:n_raw=128'h755b71766d9169ac65c761e25dfd5a18;
  264:n_raw=128'h9483909e8cb988d484ef810a7d257940;
  265:n_raw=128'hb3abafc6abe1a7fca417a0329c4d9868;
  266:n_raw=128'hd2d3ceeecb09c724c33fbf5abb75b790;
  267:n_raw=128'hf1fbee16ea31e64ce267de82da9dd6b8;
  268:n_raw=128'h11230d3e09590574018ffdaaf9c5f5e0;
  269:n_raw=128'h304b2c662881249c20b71cd218ed1508;
  270:n_raw=128'h4f734b8e47a943c43fdf3bfa38153430;
  271:n_raw=128'h6e9b6ab666d162ec5f075b22573d5358;
  272:n_raw=128'h8dc389de85f982147e2f7a4a76657280;
  273:n_raw=128'haceba906a521a13c9d579972958d91a8;
  274:n_raw=128'hcc13c82ec449c064bc7fb89ab4b5b0d0;
  275:n_raw=128'heb3be756e371df8cdba7d7c2d3ddcff8;
  276:n_raw=128'h0a63067e0299feb4facff6eaf305ef20;
  277:n_raw=128'h298b25a621c11ddc19f71612122d0e48;
  278:n_raw=128'h48b344ce40e93d04391f353a31552d70;
  279:n_raw=128'h67db63f660115c2c58475462507d4c98;
  280:n_raw=128'h8703831e7f397b54776f738a6fa56bc0;
  281:n_raw=128'ha62ba2469e619a7c969792b28ecd8ae8;
  282:n_raw=128'hc553c16ebd89b9a4b5bfb1daadf5aa10;
  283:n_raw=128'he47be096dcb1d8ccd4e7d102cd1dc938;
  284:n_raw=128'h03a3ffbefbd9f7f4f40ff02aec45e860;
  285:n_raw=128'h22cb1ee61b01171c13370f520b6d0788;
  286:n_raw=128'h41f33e0e3a293644325f2e7a2a9526b0;
  287:n_raw=128'h611b5d365951556c51874da249bd45d8;
  288:n_raw=128'h00000000000000000000000000006500;
  320:n_raw=128'h0000ffff0003fff9000fffe1003fff81;
  384:n_raw=128'hf4bbf40ef361f2b4f207f15af0adf000;
  385:n_raw=128'hfa23f976f8c9f81cf76ff6c2f615f568;
  386:n_raw=128'hff8bfedefe31fd84fcd7fc2afb7dfad0;
  387:n_raw=128'h04f30446039902ec023f019200e50038;
  388:n_raw=128'h0a5b09ae0901085407a706fa064d05a0;
  389:n_raw=128'h0fc30f160e690dbc0d0f0c620bb50b08;
  390:n_raw=128'hf52bf47ef3d1f324f277f1caf11df070;
  391:n_raw=128'hfa93f9e6f939f88cf7dff732f685f5d8;
  392:n_raw=128'hfffbff4efea1fdf4fd47fc9afbedfb40;
  393:n_raw=128'h056304b60409035c02af0202015500a8;
  394:n_raw=128'h0acb0a1e097108c40817076a06bd0610;
  395:n_raw=128'hf0330f860ed90e2c0d7f0cd20c250b78;
  396:n_raw=128'hf59bf4eef441f394f2e7f23af18df0e0;
  397:n_raw=128'hfb03fa56f9a9f8fcf84ff7a2f6f5f648;
  398:n_raw=128'h006bffbeff11fe64fdb7fd0afc5dfbb0;
  399:n_raw=128'h05d30526047903cc031f027201c50118;
  400:n_raw=128'h0b3b0a8e09e10934088707da072d0680;
  401:n_raw=128'hf0a30ff60f490e9c0def0d420c950be8;
  402:n_raw=128'hf60bf55ef4b1f404f357f2aaf1fdf150;
  403:n_raw=128'hfb73fac6fa19f96cf8bff812f765f6b8;
  404:n_raw=128'h00db002eff81fed4fe27fd7afccdfc20;
  405:n_raw=128'h0643059604e9043c038f02e202350188;
  406:n_raw=128'h0bab0afe0a5109a408f7084a079d06f0;
  407:n_raw=128'hf113f0660fb90f0c0e5f0db20d050c58;
  408:n_raw=128'hf67bf5cef521f474f3c7f31af26df1c0;
  409:n_raw=128'hfbe3fb36fa89f9dcf92ff882f7d5f728;
  410:n_raw=128'h014b009efff1ff44fe97fdeafd3dfc90;
  411:n_raw=128'h06b30606055904ac03ff035202a501f8;
  412:n_raw=128'h0c1b0b6e0ac10a14096708ba080d0760;
  413:n_raw=128'hf183f0d6f0290f7c0ecf0e220d750cc8;
  414:n_raw=128'hf6ebf63ef591f4e4f437f38af2ddf230;
  415:n_raw=128'hfc53fba6faf9fa4cf99ff8f2f845f798;
  416:n_raw=128'h0000000000000000000000000000fd00;
  448:n_raw=128'hf0cbf0aef091f074f057f03af01df000;
  449:n_raw=128'hf1b3f196f179f15cf13ff122f105f0e8;
  450:n_raw=128'hf29bf27ef261f244f227f20af1edf1d0;
  451:n_raw=128'hf383f366f349f32cf30ff2f2f2d5f2b8;
  452:n_raw=128'hf46bf44ef431f414f3f7f3daf3bdf3a0;
  453:n_raw=128'hf553f536f519f4fcf4dff4c2f4a5f488;
  454:n_raw=128'hf63bf61ef601f5e4f5c7f5aaf58df570;
  455:n_raw=128'hf723f706f6e9f6ccf6aff692f675f658;
  456:n_raw=128'hf80bf7eef7d1f7b4f797f77af75df740;
  457:n_raw=128'hf8f3f8d6f8b9f89cf87ff862f845f828;
  458:n_raw=128'hf9dbf9bef9a1f984f967f94af92df910;
  459:n_raw=128'hfac3faa6fa89fa6cfa4ffa32fa15f9f8;
  460:n_raw=128'hfbabfb8efb71fb54fb37fb1afafdfae0;
  461:n_raw=128'hf093f076f059f03cf01ff002fbe5fbc8;
  462:n_raw=128'hf17bf15ef141f124f107f0eaf0cdf0b0;
  463:n_raw=128'hf263f246f229f20cf1eff1d2f1b5f198;
  464:n_raw=128'hf34bf32ef311f2f4f2d7f2baf29df280;
  465:n_raw=128'hf433f416f3f9f3dcf3bff3a2f385f368;
  466:n_raw=128'hf51bf4fef4e1f4c4f4a7f48af46df450;
  467:n_raw=128'hf603f5e6f5c9f5acf58ff572f555f538;
  468:n_raw=128'hf6ebf6cef6b1f694f677f65af63df620;
  469:n_raw=128'hf7d3f7b6f799f77cf75ff742f725f708;
  470:n_raw=128'hf8bbf89ef881f864f847f82af80df7f0;
  471:n_raw=128'hf9a3f986f969f94cf92ff912f8f5f8d8;
  472:n_raw=128'hfa8bfa6efa51fa34fa17f9faf9ddf9c0;
  473:n_raw=128'hfb73fb56fb39fb1cfafffae2fac5faa8;
  474:n_raw=128'hf05bf03ef021f004fbe7fbcafbadfb90;
  475:n_raw=128'hf143f126f109f0ecf0cff0b2f095f078;
  476:n_raw=128'hf22bf20ef1f1f1d4f1b7f19af17df160;
  477:n_raw=128'hf313f2f6f2d9f2bcf29ff282f265f248;
  478:n_raw=128'hf3fbf3def3c1f3a4f387f36af34df330;
  479:n_raw=128'hf4e3f4c6f4a9f48cf46ff452f435f418;
  480:n_raw=128'h00000000000000000000000000000c00;
  512:n_raw=128'hff85ff85ff85ff85ff85ff85ff85ff85;
  576:n_raw=128'hfffffff8fff0ffefc001c000bfff8000;
  577:n_raw=128'h00000000000000000000000000000000;
  640:n_raw=128'h00000000000000000000000000007fff;
  default:n_raw=128'h0;endcase end endfunction
 function automatic [127:0] n_gamma;input integer vec,word;begin case(vec*64+word)
  0:n_gamma=128'h04000400040004000400040004000400;
  64:n_gamma=128'h04000400040004000400040004000400;
  128:n_gamma=128'h0c000000fc00040080007fff80007fff;
  192:n_gamma=128'h00000000000000000000000000008000;
  256:n_gamma=128'h0400f8000400f8000400f8000400f800;
  257:n_gamma=128'h0400f8000400f8000400f8000400f800;
  258:n_gamma=128'h0400f8000400f8000400f8000400f800;
  259:n_gamma=128'h0400f8000400f8000400f8000400f800;
  260:n_gamma=128'h0400f8000400f8000400f8000400f800;
  261:n_gamma=128'h0400f8000400f8000400f8000400f800;
  262:n_gamma=128'h0400f8000400f8000400f8000400f800;
  263:n_gamma=128'h0400f8000400f8000400f8000400f800;
  264:n_gamma=128'h0400f8000400f8000400f8000400f800;
  265:n_gamma=128'h0400f8000400f8000400f8000400f800;
  266:n_gamma=128'h0400f8000400f8000400f8000400f800;
  267:n_gamma=128'h0400f8000400f8000400f8000400f800;
  268:n_gamma=128'h0400f8000400f8000400f8000400f800;
  269:n_gamma=128'h0400f8000400f8000400f8000400f800;
  270:n_gamma=128'h0400f8000400f8000400f8000400f800;
  271:n_gamma=128'h0400f8000400f8000400f8000400f800;
  272:n_gamma=128'h0400f8000400f8000400f8000400f800;
  273:n_gamma=128'h0400f8000400f8000400f8000400f800;
  274:n_gamma=128'h0400f8000400f8000400f8000400f800;
  275:n_gamma=128'h0400f8000400f8000400f8000400f800;
  276:n_gamma=128'h0400f8000400f8000400f8000400f800;
  277:n_gamma=128'h0400f8000400f8000400f8000400f800;
  278:n_gamma=128'h0400f8000400f8000400f8000400f800;
  279:n_gamma=128'h0400f8000400f8000400f8000400f800;
  280:n_gamma=128'h0400f8000400f8000400f8000400f800;
  281:n_gamma=128'h0400f8000400f8000400f8000400f800;
  282:n_gamma=128'h0400f8000400f8000400f8000400f800;
  283:n_gamma=128'h0400f8000400f8000400f8000400f800;
  284:n_gamma=128'h0400f8000400f8000400f8000400f800;
  285:n_gamma=128'h0400f8000400f8000400f8000400f800;
  286:n_gamma=128'h0400f8000400f8000400f8000400f800;
  287:n_gamma=128'h0400f8000400f8000400f8000400f800;
  288:n_gamma=128'h0000000000000000000000000000f800;
  320:n_gamma=128'h0001000080007ffff8000800fc000400;
  384:n_gamma=128'h04000400040004000400040004000400;
  385:n_gamma=128'h04000400040004000400040004000400;
  386:n_gamma=128'h04000400040004000400040004000400;
  387:n_gamma=128'h04000400040004000400040004000400;
  388:n_gamma=128'h04000400040004000400040004000400;
  389:n_gamma=128'h04000400040004000400040004000400;
  390:n_gamma=128'h04000400040004000400040004000400;
  391:n_gamma=128'h04000400040004000400040004000400;
  392:n_gamma=128'h04000400040004000400040004000400;
  393:n_gamma=128'h04000400040004000400040004000400;
  394:n_gamma=128'h04000400040004000400040004000400;
  395:n_gamma=128'h04000400040004000400040004000400;
  396:n_gamma=128'h04000400040004000400040004000400;
  397:n_gamma=128'h04000400040004000400040004000400;
  398:n_gamma=128'h04000400040004000400040004000400;
  399:n_gamma=128'h04000400040004000400040004000400;
  400:n_gamma=128'h04000400040004000400040004000400;
  401:n_gamma=128'h04000400040004000400040004000400;
  402:n_gamma=128'h04000400040004000400040004000400;
  403:n_gamma=128'h04000400040004000400040004000400;
  404:n_gamma=128'h04000400040004000400040004000400;
  405:n_gamma=128'h04000400040004000400040004000400;
  406:n_gamma=128'h04000400040004000400040004000400;
  407:n_gamma=128'h04000400040004000400040004000400;
  408:n_gamma=128'h04000400040004000400040004000400;
  409:n_gamma=128'h04000400040004000400040004000400;
  410:n_gamma=128'h04000400040004000400040004000400;
  411:n_gamma=128'h04000400040004000400040004000400;
  412:n_gamma=128'h04000400040004000400040004000400;
  413:n_gamma=128'h04000400040004000400040004000400;
  414:n_gamma=128'h04000400040004000400040004000400;
  415:n_gamma=128'h04000400040004000400040004000400;
  416:n_gamma=128'h00000000000000000000000000000400;
  default:n_gamma=128'h0;endcase end endfunction
 function automatic [127:0] n_output;input integer vec,word;begin case(vec*64+word)
  0:n_output=128'hf9aa058bfb3f03f6fcd50260fe6a00cb;
  64:n_output=128'h00000000000000000000000000000000;
  128:n_output=128'h00010000000000008000800080008000;
  192:n_output=128'h00000000000000000000000000007fff;
  256:n_output=128'hfa750b84fa070c5ff9990d3bf92c0e16;
  257:n_output=128'hfc2c0816fbbe08f2fb5009cdfae30aa8;
  258:n_output=128'hfde304a8fd750584fd07065ffc9a073b;
  259:n_output=128'hff9a013bff2c0216febe02f1fe5003cd;
  260:n_output=128'h0150fdcd00e3fea80075ff840007005f;
  261:n_output=128'h0307fa5f029afb3a022cfc1601befcf1;
  262:n_output=128'h04bef6f10451f7cd03e3f8a80375f984;
  263:n_output=128'h0675f3830607f45f059af53a052cf616;
  264:n_output=128'hfa160c42f9a80d1ef93a0df906e3f2a8;
  265:n_output=128'hfbcd08d4fb5f09b0faf10a8bfa840b67;
  266:n_output=128'hfd840566fd160642fca8071dfc3a07f9;
  267:n_output=128'hff3b01f9fecd02d4fe5f03b0fdf1048b;
  268:n_output=128'h00f1fe8b0084ff6600160042ffa8011d;
  269:n_output=128'h02a8fb1d023bfbf901cdfcd4015ffdaf;
  270:n_output=128'h045ff7af03f1f88b0384f9660316fa42;
  271:n_output=128'h0616f44205a8f51d053bf5f804cdf6d4;
  272:n_output=128'hf9b70d00f9490ddc06f2f28b0684f366;
  273:n_output=128'hfb6e0992fb000a6efa920b49fa240c25;
  274:n_output=128'hfd250625fcb70700fc4907dcfbdb08b7;
  275:n_output=128'hfedb02b7fe6e0392fe00046efd920549;
  276:n_output=128'h0092ff4900250025ffb70100ff4901db;
  277:n_output=128'h0249fbdb01dbfcb7016efd920100fe6e;
  278:n_output=128'h0400f86e0392f9490325fa2402b7fb00;
  279:n_output=128'h05b7f5000549f5db04dcf6b7046ef792;
  280:n_output=128'hf9580dbe0700f26d0692f3490625f424;
  281:n_output=128'hfb0f0a51faa10b2cfa330c08f9c50ce3;
  282:n_output=128'hfcc506e3fc5807befbea089afb7c0975;
  283:n_output=128'hfe7c0375fe0f0451fda1052cfd330607;
  284:n_output=128'h00330007ffc600e3ff5801befeea029a;
  285:n_output=128'h01eafc99017cfd75010ffe5000a1ff2c;
  286:n_output=128'h03a1f92c0333fa0702c6fae30258fbbe;
  287:n_output=128'h0558f5be04eaf699047cf775040ff850;
  288:n_output=128'h0000000000000000000000000000f4e2;
  320:n_output=128'h00000000fd5ff9deff2efe4dfe46fc86;
  384:n_output=128'hffb3ffaeffaaffa5ffa0ff9cff97ff92;
  385:n_output=128'hffd8ffd3ffcfffcaffc5ffc1ffbcffb7;
  386:n_output=128'hfffdfff8fff4ffefffeaffe6ffe1ffdc;
  387:n_output=128'h0022001d00190014000f000b00060001;
  388:n_output=128'h00470042003e003900340030002b0027;
  389:n_output=128'h006c00670063005e005900550050004c;
  390:n_output=128'hffb6ffb1ffadffa8ffa3ff9fff9aff95;
  391:n_output=128'hffdbffd6ffd2ffcdffc8ffc4ffbfffba;
  392:n_output=128'h0000fffbfff7fff2ffedffe9ffe4ffdf;
  393:n_output=128'h00250020001c00170012000e00090004;
  394:n_output=128'h004a00450041003c00370033002e002a;
  395:n_output=128'hff94006a00660061005c00580053004f;
  396:n_output=128'hffb9ffb4ffb0ffabffa6ffa2ff9dff98;
  397:n_output=128'hffdeffd9ffd5ffd0ffcbffc7ffc2ffbd;
  398:n_output=128'h0003fffefffafff5fff0ffecffe7ffe2;
  399:n_output=128'h00280023001f001a00150011000c0007;
  400:n_output=128'h004d00480044003f003a00360031002d;
  401:n_output=128'hff97006d00690064005f005b00560052;
  402:n_output=128'hffbcffb7ffb3ffaeffa9ffa5ffa0ff9b;
  403:n_output=128'hffe1ffdcffd8ffd3ffceffcaffc5ffc0;
  404:n_output=128'h00060001fffdfff8fff3ffefffeaffe5;
  405:n_output=128'h002b00260022001d00180014000f000a;
  406:n_output=128'h0050004b00470042003d003900340030;
  407:n_output=128'hff9aff95006c00670062005e00590055;
  408:n_output=128'hffbfffbaffb6ffb1ffacffa8ffa3ff9e;
  409:n_output=128'hffe4ffdfffdbffd6ffd1ffcdffc8ffc3;
  410:n_output=128'h000900040000fffbfff6fff2ffedffe8;
  411:n_output=128'h002e002900250020001b00170012000d;
  412:n_output=128'h0053004e004a00450040003c00370033;
  413:n_output=128'hff9dff98ff93006a00650061005c0058;
  414:n_output=128'hffc2ffbdffb9ffb4ffafffabffa6ffa1;
  415:n_output=128'hffe7ffe2ffdeffd9ffd4ffd0ffcbffc6;
  416:n_output=128'h0000000000000000000000000000ffeb;
  448:n_output=128'h00080008000700070007000700070007;
  449:n_output=128'h000a000a000900090009000900080008;
  450:n_output=128'h000d000c000c000b000b000b000b000a;
  451:n_output=128'h0010000f000f000e000e000e000d000d;
  452:n_output=128'h00140013001300120011001100110010;
  453:n_output=128'h00190018001700170016001500150014;
  454:n_output=128'h001f001e001d001c001c001b001a0019;
  455:n_output=128'h00270026002500240023002200210020;
  456:n_output=128'h0031002f002e002d002b002a00290028;
  457:n_output=128'h003d003c003a00380036003500330032;
  458:n_output=128'h004d004a00480046004400420041003f;
  459:n_output=128'h0060005d005b0058005600530051004f;
  460:n_output=128'h007800750072006f006c006800660063;
  461:n_output=128'h0007000700070007000700070080007c;
  462:n_output=128'h00090009000900090008000800080008;
  463:n_output=128'h000c000b000b000b000b000a000a000a;
  464:n_output=128'h000f000e000e000e000d000d000d000c;
  465:n_output=128'h0013001200120011001100100010000f;
  466:n_output=128'h00170017001600150015001400140013;
  467:n_output=128'h001d001d001c001b001a001900190018;
  468:n_output=128'h002500240023002200210020001f001e;
  469:n_output=128'h002e002d002c002a0029002800270026;
  470:n_output=128'h003a003800360035003400320031002f;
  471:n_output=128'h00480046004400430041003f003d003c;
  472:n_output=128'h005b0058005600530051004f004d004b;
  473:n_output=128'h0072006f006c0069006600630060005e;
  474:n_output=128'h00070007000700070080007c00790075;
  475:n_output=128'h00090009000900080008000800070007;
  476:n_output=128'h000b000b000b000a000a000a00090009;
  477:n_output=128'h000e000e000d000d000d000c000c000b;
  478:n_output=128'h00120011001100100010000f000f000e;
  479:n_output=128'h00160016001500140014001300130012;
  480:n_output=128'h00000000000000000000000000001be6;
  512:n_output=128'h08000800080008000800080008000800;
  576:n_output=128'h0ce40cce0cb40cb10000000000000000;
  577:n_output=128'h00000000000000000000000000000ce8;
  640:n_output=128'h00000000000000000000000000004000;
  default:n_output=128'hbad;endcase end endfunction
 function automatic [127:0] n_expword;input integer vec,word;begin case(vec*64+word)
  448:n_expword=128'h002500230022002100200020001f001e;
  449:n_expword=128'h002e002c002b002a0029002800260025;
  450:n_expword=128'h003a003800360034003300320031002f;
  451:n_expword=128'h00480046004400420040003e003c003b;
  452:n_expword=128'h005a0058005500530050004f004c004a;
  453:n_expword=128'h0071006e006b006800650062005f005c;
  454:n_expword=128'h008e008a00860082007f007b00780074;
  455:n_expword=128'h00b200ad00a800a4009f009a00960092;
  456:n_expword=128'h00df00d900d300cd00c700c200bc00b7;
  457:n_expword=128'h011801110108010100fa00f200ec00e6;
  458:n_expword=128'h015f0155014b01420139013101280120;
  459:n_expword=128'h01b801ac01a00194018a017e01740169;
  460:n_expword=128'h02280219020a01fb01ee01df01d201c5;
  461:n_expword=128'h0022002100210020001f001e02490238;
  462:n_expword=128'h002b002a002900280026002600250023;
  463:n_expword=128'h00360034003400320031002f002e002c;
  464:n_expword=128'h004400420040003e003c003b003a0038;
  465:n_expword=128'h005500530051004f004c004a00480046;
  466:n_expword=128'h006b006800650062005f005d005b0058;
  467:n_expword=128'h00860083007f007c007800740072006e;
  468:n_expword=128'h00a800a4009f009b00960092008e008a;
  469:n_expword=128'h00d400cd00c800c200bd00b700b200ae;
  470:n_expword=128'h0109010200fa00f300ed00e600df00d9;
  471:n_expword=128'h014c0143013a01320129012001180111;
  472:n_expword=128'h01a10195018a017f0175016a01600156;
  473:n_expword=128'h020b01fc01ee01e001d301c601b901ad;
  474:n_expword=128'h00210020001f001e024a023a0229021a;
  475:n_expword=128'h00290028002700260025002300220021;
  476:n_expword=128'h003400320031002f002e002d002b002a;
  477:n_expword=128'h0040003e003d003b003a003800360034;
  478:n_expword=128'h0051004f004c004a0048004600440042;
  479:n_expword=128'h006500630060005d005b005800550053;
  480:n_expword=128'h00000000000000000000000000008000;
  512:n_expword=128'h80008000800080008000800080008000;
  576:n_expword=128'h7fe07f027e047de50000000000000000;
  577:n_expword=128'h00000000000000000000000000008000;
  640:n_expword=128'h00000000000000000000000000008000;
  default:n_expword=128'h0;endcase end endfunction
 function automatic [1:0] n_mode;input integer vec;begin case(vec)
  0:n_mode=1;
  1:n_mode=1;
  2:n_mode=1;
  3:n_mode=1;
  4:n_mode=1;
  5:n_mode=2;
  6:n_mode=2;
  7:n_mode=0;
  8:n_mode=0;
  9:n_mode=0;
  10:n_mode=0;
  default:n_mode=0;endcase end endfunction
 function automatic [15:0] n_count;input integer vec;begin case(vec)
  0:n_count=8;
  1:n_count=8;
  2:n_count=8;
  3:n_count=1;
  4:n_count=257;
  5:n_count=8;
  6:n_count=257;
  7:n_count=257;
  8:n_count=8;
  9:n_count=9;
  10:n_count=1;
  default:n_count=0;endcase end endfunction
 function automatic [31:0] n_epsilon;input integer vec;begin case(vec)
  0:n_epsilon=1;
  1:n_epsilon=1;
  2:n_epsilon=1;
  3:n_epsilon=1;
  4:n_epsilon=17;
  5:n_epsilon=1;
  6:n_epsilon=9;
  7:n_epsilon=0;
  8:n_epsilon=0;
  9:n_epsilon=0;
  10:n_epsilon=0;
  default:n_epsilon=0;endcase end endfunction
 function automatic [7:0] n_words;input integer vec;begin case(vec)
  0:n_words=1;
  1:n_words=1;
  2:n_words=1;
  3:n_words=1;
  4:n_words=33;
  5:n_words=1;
  6:n_words=33;
  7:n_words=33;
  8:n_words=1;
  9:n_words=2;
  10:n_words=1;
  default:n_words=0;endcase end endfunction
 function automatic n_sat;input integer vec;begin case(vec)
  0:n_sat=1'b0;
  1:n_sat=1'b0;
  2:n_sat=1'b1;
  3:n_sat=1'b1;
  4:n_sat=1'b0;
  5:n_sat=1'b0;
  6:n_sat=1'b0;
  7:n_sat=1'b0;
  8:n_sat=1'b0;
  9:n_sat=1'b0;
  10:n_sat=1'b0;
  default:n_sat=0;endcase end endfunction
 function automatic [8*100-1:0] case_name;input integer index;begin case(index)
  0:case_name="W4_N_RMS8_MIXED";
  1:case_name="W4_N_RMS8_ZERO";
  2:case_name="W4_N_RMS8_EXTREME_GAMMA_SAT";
  3:case_name="W4_N_RMS1_TAIL";
  4:case_name="W4_N_RMS257_TAIL";
  5:case_name="W4_N_L2_8_SIGNED_GAMMA";
  6:case_name="W4_N_L2_257_TAIL";
  7:case_name="W4_N_SOFTMAX257_LAST_NEWMAX";
  8:case_name="W4_N_SOFTMAX8_EQUAL_UNSIGNED32768";
  9:case_name="W4_N_SOFTMAX9_CUTOFF_AND_ROUND";
  10:case_name="W4_N_SOFTMAX1";
  default:case_name="unknown";endcase end endfunction
 function automatic [8*100-1:0] guard_name;input integer index;begin case(index)
  0:guard_name="W4_N_GUARD_ZERO_COUNT";
  1:guard_name="W4_N_GUARD_COUNT258";
  2:guard_name="W4_N_GUARD_MODE3";
  3:guard_name="W4_N_GUARD_ZERO_EPSILON";
  4:guard_name="W4_N_GUARD_RANGE_END";
  5:guard_name="W4_N_GUARD_SRC_DST_OVERLAP";
  6:guard_name="W4_N_GUARD_GAMMA_DST_OVERLAP";
  7:guard_name="W4_N_GUARD_SRC_EXP_OVERLAP";
  default:guard_name="unknown";endcase end endfunction
 function automatic integer native_word_index;input integer ix;integer w;begin w=n_words(ci);if(ix>=1&&ix<=w)native_word_index=ix-1;else if(n_mode(ci)!=0)native_word_index=ix-w-2;else if(ix<=2*w+1)native_word_index=ix-w-2;else native_word_index=ix-2*w-3;end endfunction

 reg clk=0;always #5 clk=~clk;
 reg reset=1,owner=0,service_active=0,strict=1;
 reg allow_mem_req=1,allow_mem_rsp=1,allow_s_ack=1,allow_n_cmd=1,allow_n_rsp=1;
 reg corrupt_n=0,inject_mem_error=0;
 reg req_valid=0,rsp_ready=0;wire req_ready,rsp_valid,rsp_error,rsp_saturated,busy;
 reg [1:0] req_mode;reg [15:0] req_count;reg [31:0] req_epsilon;
 reg [9:0] req_src_addr=100,req_gamma_addr=200,req_exp_addr=300,req_dst_addr=400;
 wire mv,mr,mw,mrv,mrr,mre;wire [9:0] ma;wire [127:0] md,mrd;
 wire cv,cr,leaf_cr,rv,rr,re,rsat;wire [3:0] cop,ccount;wire [31:0] cp;wire [127:0] cd,ca,rd;
 wire hv,hr,hw,hrv,hrr,hre;wire [9:0] ha;wire [127:0] hd,hrd;
 reg host_valid=0,host_write=1,host_rsp_ready=0;reg [9:0] host_addr;reg [127:0] host_data;
 wire s_req,s_we,s_ready,s_valid,s_take,helper_take;wire [9:0] s_addr;wire [127:0] s_din,s_dout;
 assign hv=!reset&&allow_mem_req&&(owner?mv:host_valid);assign hw=owner?mw:host_write;
 assign ha=owner?ma:host_addr;assign hd=owner?md:host_data;assign mr=!reset&&owner&&allow_mem_req&&hr;
 assign mrv=!reset&&owner&&allow_mem_rsp&&hrv;assign mrd=hrd;assign mre=hre||inject_mem_error;
 assign hrr=!reset&&allow_mem_rsp&&(owner?mrr:host_rsp_ready);
 assign cr=leaf_cr&&allow_n_cmd;assign s_take=helper_take&&allow_s_ack;
 block_w4_n_ctrl u_ctrl(.clk(clk),.reset(reset),.req_valid(req_valid),.req_ready(req_ready),.req_mode(req_mode),.req_count(req_count),.req_epsilon(req_epsilon),.req_src_addr(req_src_addr),.req_gamma_addr(req_gamma_addr),.req_exp_addr(req_exp_addr),.req_dst_addr(req_dst_addr),.rsp_valid(rsp_valid),.rsp_ready(rsp_ready),.rsp_error(rsp_error),.rsp_saturated(rsp_saturated),.busy(busy),.n_cmd_valid(cv),.n_cmd_ready(cr),.n_cmd_op(cop),.n_cmd_count(ccount),.n_cmd_param(cp),.n_cmd_data(cd),.n_cmd_aux(ca),.n_rsp_valid(rv&&allow_n_rsp),.n_rsp_ready(rr),.n_rsp_data(rd),.n_rsp_error(re),.n_rsp_saturated(rsat),.mem_req_valid(mv),.mem_req_ready(mr),.mem_req_write(mw),.mem_req_addr(ma),.mem_req_data(md),.mem_rsp_valid(mrv),.mem_rsp_ready(mrr),.mem_rsp_data(mrd),.mem_rsp_error(mre));
 block_v2_n u_n(.clk(clk),.reset(reset),.cmd_valid(cv&&allow_n_cmd),.cmd_ready(leaf_cr),.cmd_op(corrupt_n?4'd15:cop),.cmd_count(ccount),.cmd_param(cp),.cmd_data(cd),.cmd_aux(ca),.rsp_valid(rv),.rsp_ready(rr&&allow_n_rsp),.rsp_data(rd),.rsp_error(re),.rsp_saturated(rsat),.busy());
 block_p2_s_ctrl u_helper(.clk(clk),.resetn(!reset),.req_valid(hv),.req_ready(hr),.req_write(hw),.req_addr(ha),.req_data(hd),.rsp_valid(hrv),.rsp_ready(hrr),.rsp_data(hrd),.rsp_error(hre),.s_req(s_req),.s_we(s_we),.s_addr(s_addr),.s_din(s_din),.s_rsp_ready(helper_take),.s_ready(s_ready),.s_rsp_valid(s_valid&&allow_s_ack),.s_dout(s_dout));
 block_feed_s16k u_s(.clk(clk),.reset(reset),.req(s_req),.wr(s_we),.addr(s_addr),.din(s_din),.ready(s_ready),.valid(s_valid),.take(s_take),.dout(s_dout),.wide_req(1'b0),.wide_addr(8'd0),.wide_ready(),.wide_valid(),.wide_take(1'b1),.wide_dout());
 localparam [127:0] POISON=128'hdeadbeef0123456789abcdeffeedface;
 integer cycles=0,cases=0,ci=0,reads=0,writes=0,acks=0,commands=0,responses=0,completions=0;
 integer r0,w0,a0,c0,p0,d0,mem_index=0,cmd_index=0;
 reg pending=0,pending_write;reg [127:0] pending_data;reg [9:0] pending_addr;
 reg hold_cmd=0,hold_mem=0,hold_rsp=0,hold_native=0,hold_s=0;
 reg [127:0] old_cd,old_ca,old_md,old_rd,old_sd;reg [3:0] old_op,old_count;reg [31:0] old_param;reg [9:0] old_addr;
 reg old_mw,old_error,old_sat,old_ne,old_ns;
 function automatic [127:0] ram;
  input integer addr;begin case(addr%4)
   0:ram=u_s.bank0[addr/4];1:ram=u_s.bank1[addr/4];2:ram=u_s.bank2[addr/4];3:ram=u_s.bank3[addr/4];
  endcase end
 endfunction
 function automatic integer expected_op;
  input integer index;integer words;begin words=n_words(ci);
   if(index==0)expected_op=0;else if(index<=words)expected_op=1;else if(index==words+1)expected_op=2;
   else if(n_mode(ci)!=0)expected_op=5;
   else if(index<=2*words+1)expected_op=3;else if(index==2*words+2)expected_op=4;else expected_op=6;
  end
 endfunction
 function automatic integer expected_mem_addr;
  input integer index;integer w,k,t;begin w=n_words(ci);
   if(index<w)expected_mem_addr=100+index;
   else if(n_mode(ci)!=0)begin t=index-w;k=t/3;case(t%3)0:expected_mem_addr=100+k;1:expected_mem_addr=200+k;2:expected_mem_addr=400+k;endcase end
   else if(index<3*w)begin t=index-w;k=t/2;expected_mem_addr=(t%2==0?100:300)+k;end
   else begin t=index-3*w;k=t/2;expected_mem_addr=(t%2==0?300:400)+k;end
  end
 endfunction
 function automatic expected_mem_write;
  input integer index;integer w;begin w=n_words(ci);if(index<w)expected_mem_write=0;
   else if(n_mode(ci)!=0)expected_mem_write=((index-w)%3==2);
   else if(index<3*w)expected_mem_write=((index-w)%2==1);else expected_mem_write=((index-3*w)%2==1);
  end
 endfunction
 always @(posedge clk)begin
  cycles=cycles+1;if(cycles>800000)$fatal(1,"FAIL_W4_N watchdog");
  if(reset)begin pending=0;hold_cmd=0;hold_mem=0;hold_rsp=0;hold_native=0;hold_s=0;end else begin
   if(hold_cmd&&(!cv||cop!==old_op||ccount!==old_count||cp!==old_param||cd!==old_cd||ca!==old_ca))$fatal(1,"FAIL_W4_N command changed under stall");
   if(hold_mem&&(!mv||ma!==old_addr||md!==old_md||mw!==old_mw))$fatal(1,"FAIL_W4_N mem request changed under stall");
   if(hold_rsp&&(!rsp_valid||rsp_error!==old_error||rsp_saturated!==old_sat))$fatal(1,"FAIL_W4_N completion changed under stall");
   if(hold_native&&(!rv||rd!==old_rd||re!==old_ne||rsat!==old_ns))$fatal(1,"FAIL_W4_N native response changed under stall");
   if(hold_s&&(!s_valid||s_dout!==old_sd))$fatal(1,"FAIL_W4_N S ACK changed under stall");
   hold_cmd=cv&&!cr;old_op=cop;old_count=ccount;old_param=cp;old_cd=cd;old_ca=ca;
   hold_mem=owner&&mv&&!mr;old_addr=ma;old_md=md;old_mw=mw;
   hold_rsp=rsp_valid&&!rsp_ready;old_error=rsp_error;old_sat=rsp_saturated;
   hold_native=rv&&!(rr&&allow_n_rsp);old_rd=rd;old_ne=re;old_ns=rsat;
   hold_s=s_valid&&!s_take;old_sd=s_dout;
   if(rsp_valid&&rsp_ready)completions=completions+1;
   if(s_req&&s_ready)begin
    if(pending)$fatal(1,"FAIL_W4_N multiple S owners");pending=1;pending_write=s_we;pending_data=s_din;pending_addr=s_addr;
    if(service_active)begin
     if(strict)begin
      if(s_addr!=expected_mem_addr(mem_index)||s_we!==expected_mem_write(mem_index))$fatal(1,"FAIL_W4_N mem sequence ci%0d step%0d got%0d wr%0d expected%0d",ci,mem_index,s_addr,s_we,expected_mem_addr(mem_index));
      if(s_we&&s_din!==(s_addr>=400?n_output(ci,s_addr-400):n_expword(ci,s_addr-300)))$fatal(1,"FAIL_W4_N write math mismatch ci%0d addr%0d got%032h",ci,s_addr,s_din);
     end
     mem_index=mem_index+1;if(s_we)writes=writes+1;else reads=reads+1;
    end
   end
   if(s_valid&&s_take)begin
    if(!pending)$fatal(1,"FAIL_W4_N response without request");
    if(pending_write&&s_dout!==pending_data)$fatal(1,"FAIL_W4_N write ACK echo");
    pending=0;if(service_active)acks=acks+1;
   end
   if(cv&&cr)begin
    if(strict)begin
     if(cop!=expected_op(cmd_index))$fatal(1,"FAIL_W4_N command phase ci%0d index%0d op%0d",ci,cmd_index,cop);
     if(cop==0&&(cp!==n_mode(ci)||cd[31:0]!==n_epsilon(ci)))$fatal(1,"FAIL_W4_N BEGIN captured params");
     if(cop==1||cop==3||cop==5||cop==6)begin
      if(ccount!=(n_count(ci)-8*native_word_index(cmd_index)>8?8:n_count(ci)-8*native_word_index(cmd_index)))$fatal(1,"FAIL_W4_N native count/tail");
      if(cd!==(cop==6?n_expword(ci,native_word_index(cmd_index)):n_raw(ci,native_word_index(cmd_index))))$fatal(1,"FAIL_W4_N raw vs EXP/mask ci%0d op%0d word%0d got%032h",ci,cop,native_word_index(cmd_index),cd);
      if(cop==5&&ca!==n_gamma(ci,native_word_index(cmd_index)))$fatal(1,"FAIL_W4_N gamma replay/mask");
     end
    end
    commands=commands+1;cmd_index=cmd_index+1;
   end
   if(rv&&rr&&allow_n_rsp)responses=responses+1;
   if(service_active&&strict&&rsp_valid&&!rsp_error&&(pending||acks-a0!=n_words(ci)*(n_mode(ci)==0?5:4)))$fatal(1,"FAIL_W4_N completion before all write ACKs");
  end
 end
 task automatic mark;input [8*100-1:0] name;begin cases=cases+1;$display("CASE_PASS %0s",name);end endtask
 task automatic store;input integer address;input [127:0] data;
  begin @(negedge clk);owner=0;host_addr=address;host_data=data;host_valid=1;host_rsp_ready=0;
   while(!hr)@(negedge clk);@(posedge clk);#1;@(negedge clk);host_valid=0;
   while(!hrv)@(negedge clk);if(hrd!==data||hre)$fatal(1,"FAIL_W4_N host store ACK");host_rsp_ready=1;@(posedge clk);#1;@(negedge clk);host_rsp_ready=0;
  end
 endtask
 task automatic prepare;input integer index;integer k;reg [127:0] raw,g;
  begin ci=index;service_active=0;strict=1;
   for(k=0;k<n_words(ci);k=k+1)begin
    raw=n_raw(ci,k);g=n_gamma(ci,k);
    // Nonzero inactive source/gamma lanes must be masked, not included.
    if(k==n_words(ci)-1&&n_count(ci)%8)begin raw=raw|(128'hffffffffffffffffffffffffffffffff<<(16*(n_count(ci)%8)));g=g|(128'h0123456789abcdeffedcba9876543210<<(16*(n_count(ci)%8)));end
    store(100+k,raw);store(200+k,g);store(300+k,POISON);store(400+k,POISON);
   end
   @(negedge clk);owner=1;service_active=1;r0=reads;w0=writes;a0=acks;c0=commands;p0=responses;d0=completions;mem_index=0;cmd_index=0;
  end
 endtask
 task automatic launch;
  begin @(negedge clk);req_mode=n_mode(ci);req_count=n_count(ci);req_epsilon=n_epsilon(ci);req_src_addr=100;req_gamma_addr=200;req_exp_addr=300;req_dst_addr=400;req_valid=1;rsp_ready=0;
   while(!req_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);req_valid=0;
   req_mode=3;req_count=0;req_epsilon=0;req_src_addr=999;req_gamma_addr=998;req_exp_addr=997;req_dst_addr=996;
  end
 endtask
 task automatic finish;input error_expected,poison_expected;integer k;
  begin while(!rsp_valid)@(negedge clk);
   repeat(5)begin if(!rsp_valid||rsp_error!==error_expected||req_ready||!busy)$fatal(1,"FAIL_W4_N held completion flags");if(!error_expected&&rsp_saturated!==n_sat(ci))$fatal(1,"FAIL_W4_N saturation OR");@(negedge clk);end
   if(!error_expected)begin
    if(reads-r0!=3*n_words(ci)||writes-w0!=(n_mode(ci)==0?2:1)*n_words(ci)||acks-a0!=(n_mode(ci)==0?5:4)*n_words(ci)||commands-c0!=(n_mode(ci)==0?3+3*n_words(ci):2+2*n_words(ci))||responses-p0!=commands-c0||pending)$fatal(1,"FAIL_W4_N conservation ci%0d R%0d W%0d ACK%0d C%0d P%0d",ci,reads-r0,writes-w0,acks-a0,commands-c0,responses-p0);
    for(k=0;k<n_words(ci);k=k+1)begin if(ram(400+k)!==n_output(ci,k))$fatal(1,"FAIL_W4_N stored output");if(n_mode(ci)==0&&ram(300+k)!==n_expword(ci,k))$fatal(1,"FAIL_W4_N exact EXP stored/replayed");end
   end
   rsp_ready=1;@(posedge clk);#1;@(negedge clk);rsp_ready=0;service_active=0;owner=0;repeat(3)@(negedge clk);
   if(completions!=d0+1||rsp_valid||req_ready===poison_expected||busy!==poison_expected)$fatal(1,"FAIL_W4_N completion/reuse/poison");
  end
 endtask
 task automatic hard_reset;
  begin @(negedge clk);reset=1;req_valid=0;host_valid=0;rsp_ready=0;host_rsp_ready=0;service_active=0;owner=0;corrupt_n=0;inject_mem_error=0;
   allow_mem_req=1;allow_mem_rsp=1;allow_s_ack=1;allow_n_cmd=1;allow_n_rsp=1;
   repeat(3)@(negedge clk);reset=0;repeat(3)@(negedge clk);if(rsp_valid||busy||!req_ready||s_valid||rv)$fatal(1,"FAIL_W4_N reset recovery");
  end
 endtask
 task automatic run;input integer index,stall;
  begin prepare(index);if(stall==1)allow_n_cmd=0;if(stall==2)allow_n_rsp=0;if(stall==4)allow_mem_req=0;
   launch();
   if(stall==1)begin while(!cv)@(negedge clk);repeat(5)@(negedge clk);if(commands!=c0)$fatal(1,"FAIL_W4_N command stall accepted");allow_n_cmd=1;end
   if(stall==2)begin while(!rv)@(negedge clk);repeat(5)@(negedge clk);if(responses!=p0||rsp_valid)$fatal(1,"FAIL_W4_N response stall retired");allow_n_rsp=1;end
   if(stall==3)begin wait(mv&&mw&&ma>=400);allow_s_ack=0;while(!s_valid)@(negedge clk);repeat(5)begin @(negedge clk);if(rsp_valid)$fatal(1,"FAIL_W4_N destination write before ACK");end allow_s_ack=1;end
   if(stall==4)begin repeat(5)@(negedge clk);allow_mem_req=1;allow_mem_rsp=0;while(!hrv)@(negedge clk);repeat(5)@(negedge clk);allow_mem_rsp=1;end
   finish(0,0);
  end
 endtask
 task automatic guard;input integer kind;
  begin prepare(0);strict=0;@(negedge clk);req_mode=1;req_count=8;req_epsilon=1;req_src_addr=100;req_gamma_addr=200;req_exp_addr=300;req_dst_addr=400;
   case(kind)0:req_count=0;1:req_count=258;2:req_mode=3;3:req_epsilon=0;4:req_src_addr=1023;5:req_dst_addr=100;6:req_dst_addr=200;7:begin req_mode=0;req_exp_addr=100;end endcase
   // kind4 requires two words to exceed S, not one legal word at1023.
   if(kind==4)req_count=9;
   req_valid=1;while(!req_ready)@(negedge clk);@(posedge clk);#1;@(negedge clk);req_valid=0;finish(1,0);
   if(reads!=r0||writes!=w0||commands!=c0)$fatal(1,"FAIL_W4_N guard touched native or S");
  end
 endtask
 integer i;
 initial begin
  repeat(4)@(negedge clk);reset=0;repeat(2)@(negedge clk);
  for(i=0;i<11;i=i+1)begin run(i,0);mark(case_name(i));end
  run(0,1);mark("W4_N_NATIVE_COMMAND_HOLD");run(5,2);mark("W4_N_NATIVE_RESPONSE_HOLD");run(7,3);mark("W4_N_DESTINATION_ACK_GATE_SOFTMAX257");run(4,4);mark("W4_N_HELPER_REQUEST_RESPONSE_HOLD");
  for(i=0;i<8;i=i+1)begin guard(i);mark(guard_name(i));end
  run(0,0);mark("W4_N_REUSE_AFTER_LOCAL_ADMISSION_ERRORS");
  // A real unsupported native operation: controller must close with poison,
  // never silently restart BEGIN or claim numerical output.
  prepare(0);strict=0;launch();wait(cv&&cop==1);@(negedge clk);corrupt_n=1;@(posedge clk);#1;@(negedge clk);corrupt_n=0;finish(1,1);
  if(writes!=w0||ram(400)!==POISON)$fatal(1,"FAIL_W4_N native error wrote destination");
  hard_reset();run(5,0);mark("W4_N_NATIVE_ERROR_POISON_COORDINATED_RESET_RECOVER");
  prepare(0);strict=0;launch();wait(hrv&&owner);@(negedge clk);inject_mem_error=1;@(posedge clk);#1;@(negedge clk);inject_mem_error=0;finish(1,1);
  if(writes!=w0)$fatal(1,"FAIL_W4_N read error wrote destination");hard_reset();run(0,0);mark("W4_N_MEMORY_READ_ERROR_POISON_RESET_RECOVER");
  // Error on a later actual destination ACK: accepted writes stay visible.
  prepare(4);strict=0;launch();wait(mv&&mw&&ma==401);allow_mem_rsp=0;while(!hrv)@(negedge clk);@(negedge clk);inject_mem_error=1;allow_mem_rsp=1;@(posedge clk);#1;@(negedge clk);inject_mem_error=0;finish(1,1);
  if(writes-w0!=2||ram(400)!==n_output(4,0)||ram(401)!==n_output(4,1)||ram(402)!==POISON)$fatal(1,"FAIL_W4_N partial accepted writes rollback/overrun");
  hard_reset();run(8,0);mark("W4_N_LATE_WRITE_ERROR_PARTIAL_PREFIX_POISON_RESET");
  prepare(7);launch();wait(mv&&mw&&ma==300);allow_s_ack=0;while(!s_valid)@(negedge clk);repeat(4)@(negedge clk);hard_reset();run(0,0);mark("W4_N_RESET_PENDING_EXP_WRITE_ACK_RECOVER");
  prepare(0);allow_n_rsp=0;launch();while(!rv)@(negedge clk);repeat(4)@(negedge clk);hard_reset();run(6,0);mark("W4_N_RESET_HELD_NATIVE_RESPONSE_RECOVER");
  $display("PASS_W4_N cases=%0d cycles=%0d Sread=%0d Swrite=%0d Sack=%0d Ncmd=%0d Nrsp=%0d done=%0d",cases,cycles,reads,writes,acks,commands,responses,completions);$finish;
 end

endmodule
