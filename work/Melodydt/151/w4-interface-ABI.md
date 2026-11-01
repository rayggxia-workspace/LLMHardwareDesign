# W4 implementation contract — internal service, fixed product callers

Parent research commit0101cc7e1e6d5718455fb45b61c7428439efc09a. Native7078786 remains source lock unless explicit audited upgrade. Leaf/P2/W1/W3 code must remain byte-identical. Shared packageintegrated; agents only draft in assigneddirs.

## N controller

Module `block_w4_n_ctrl` external to nativeN and S helper. Ports:
clk, reset;
req_valid input / req_ready output;
req_mode[1:0] (0Softmax,1RMS,2L2;3invalid), req_count[15:0] target1..257;
req_epsilon[31:0] positive fornorm,ignoredsoftmax;
req_src_addr[9:0], req_gamma_addr[9:0], req_exp_addr[9:0], req_dst_addr[9:0];
rsp_valid output / rsp_ready input; rsp_error/rsp_saturated outputs;
busy output;
native n_cmd_valid/n_cmd_ready, n_cmd_op[3:0],n_cmd_count[3:0],n_cmd_param[31:0],n_cmd_data/aux[127:0]; n_rsp_valid/n_rsp_ready,n_rsp_data[127:0],n_rsp_error,n_rsp_saturated;
mem_req_valid/mem_req_ready,mem_req_write,mem_req_addr[9:0],mem_req_data[127:0];mem_rsp_valid/mem_rsp_ready,mem_rsp_data[127:0],mem_rsp_error.
All signal directions conventionalcontroller→native/helper requests. Match W3 e/g style names except n_ prefix.

Capture request once. Countceil(count/8), native countmin8remaining. Each S response captured/taken before issuing anotherread. Hold all requestpayloads underbackpressure. Own single S helper for entire service through completionrsp consumption. Source/gamma immutable lease forwhole service, caller promises version. N context retained between phases, nointerleavinggroup accepted. reset must coordinateN/helper/controller; no free standalonecancel/rollback. completionrsp/error/sat held. Errorbeforefirstdstwrite nooutput; afterpartialwrites, partial may remain, never claim rollback.

Conservative region checks: required count1..257,validmode,positive normepsilon, all used rangesend<=1023. RMS/L2 src/gamma/dst disjoint; Softmax src/exp/dst disjoint,unusedgammaignored. Input andgamma tails maskedzero, outputtailzero. No in-place/overlap service inthis firstcontroller; reject isimplementationprofile restriction,notpermanentalgorithm illegality.

Sequence BEGIN op0parammode/eps; allraw STATS op1 ACK; FINALIZE op2. RMS/L2: raw+gamma reread→op5→resultwriteACK, eachword. Softmax: allraw reread→op3 EXPreturn (U16exactcodes)→expwriteACK; op4 factor onlyafterallEXPstored; exp rereadexact→op6→resultwriteACK. Completion onlyafterlastactualdestinationACK. Onnative/memerror discard unsubmitted result; stopservicewitherror, grouplease closes onlywithcoordinatedreset before reuse ifnativecontextmayremain. NEWBEGIN can reset nativegroup aftercompletederror? implementationmust explicitlypermitcleansuccessfulnewBEGIN or assertcoordinatedreset rule; documentactualbehavior.

Numeric independentreference must exactlyderive floor division/isqrt andsignedRNE30; RMSfactor=floor(2^38/isqrt(floor(sumsq*2^16/count)+epsilon*2^16)); L2factor analogous no/count; outputclipS16(RNE30(x*factor*gamma)). gammaQ10 gives outputFin10. Softmax scoreS16Fin10, exactEXP U16[0,32768] thenfactor=floor(2^44/sumEXP), probabilityclip[0,16384](RNE30(EXP*factor)) Q14. NoDUT-derived expected. Explicit representablevectors, epsilonrawsquaredunits.

## F8 bounded integration

New `block_w4_f8_top` may clone W3fixedFFN FSM as separate module, do not modifyW3. Samepublic frameports and16×128 ingresslayout, variabletensor/weights; originalx S8Fin7 andweightsS8Fin7. Save originalresidual independently. Add N RMSNorm8 using S16 signextendedrawx,gamma=1024,epsilon1(rawsquaredcodeunit). NoutputS16Fin10; convert RNEright3+clipS8 Fin7 (explicitnew NUM narrowfunction ifusingexistingEopcannotfaithfullyconvert; no claimingE12 doesRNE). Mgate/up usesconvertednormx; E residual stilloriginalX Fin7→Fin10. N has itsown nativeinstance; oneS/helper sharedwithLOCAL/E/G/N owners. FSM/params/addressesfixed, nohostprogramloading. Root must agree precise extraSslots andcounts beforetest. No fullF/A ormodelquality claim; W5 fullpaths tracked separately.
