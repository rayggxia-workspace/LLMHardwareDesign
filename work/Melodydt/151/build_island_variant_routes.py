# -*- coding: utf-8 -*-
"""Six-variant operand and materialization route proposal; no implementation audit."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
PARENT="051fddb9a3d2cecd4b76c43d07ec8581db9402ce"
LEAF="707878621b2add4ed218b8c43df2e95c9a56e2ba"
COMPUTE={"M","N","E","G","R"}
MACROS=["M","N","E","G","R","S","T"]


def url(path,ref=PARENT,line=None):return "https://github.com/rayggxia-workspace/LLMHardwareDesign/blob/"+ref+"/"+path+("#L"+str(line) if line else "")
def file_info(path,repo_path):
    raw=path.read_bytes()
    return {"path":repo_path,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),"url":url(repo_path)}


def physical_routes():
    rows=[
      ("P_IN","EXT/MEM/PARAM payload ingress","S ordinary write",128,"X/Y, weights, gamma, bias, cos/sin, state/history, coefficients and expert data enter actual S slots; wait write ACK"),
      ("P_SR","S ordinary read response","finite operand gather",128,"capture response into owned holding slot and take it BEFORE requesting another S read"),
      ("P_ML","S built-in loader","M A128 and B512",None,"dedicated existing-shaped loader path; complete descriptor/layout/format/weight identity and done separate from EXEC"),
      ("P_N","gather + local command formatter","N cmd_data128 + cmd_aux128",256,"data and matching original/gamma/EXP role, actual cmd_count1..8 and cmd_param/phase stable until cmd handshake"),
      ("P_E","gather + local command formatter","E A/B/C",384,"up to three independent128-bit operands; unused inputs explicitly constant; op/shift stable; no hold-S-response waiting for the second S read"),
      ("P_G","gather -> pair serializer","G x32 + linear_gate32",64,"capture x/gate source words, select matching token/head/lane pair, issue/retire counts; native G has no valid-element count"),
      ("P_R","gather OR CTRL metadata formatter","R cmd_data128",128,"select payload vs OPEN/EXEC/COMMIT owner/epoch/position metadata using actual op/index; one driver, no blind tensor-as-command"),
      ("P_NUM","gather -> explicit NUM endpoint","coefficient/bias/wide-merge service",128,"128-bit transport chunk reference only; internal wider arithmetic, fields, result scale and endpoint protocols still must be designed"),
      ("P_IDX","gather -> bounded layout/index endpoint","S/MEM address selection or reordered payload",128,"split/transpose/repeat/gather plus real checked addresses; IDs remain IDs, not numeric scores"),
      ("P_CAP","M/N/E/G/R/NUM/IDX result endpoints","selected response capture/pack",128,"real selected-source mux/holding; G32 needs pad/pack, different native responses classified; not push-pull wire-OR"),
      ("P_SW","capture/pack or layout output","S ordinary write",128,"wholeword writes, exclusive tail word or explicit assembly, drain write ACK, publish only after successful classification"),
      ("P_TW","capture/pack or gather","T sequential write",128,"BEGIN first, exact word count/index; only approved completed output chunks, error/saturation checked; final write seals"),
      ("P_TO","T read response","common egress -> EXT/MEM or S ingress",128,"one selected sink takes; hold data/index/last, wait actual destination stored ACK, final TAKE then RELEASE; S destination needs real checked base+index"),
      ("P_MO","S read/gather","common egress -> MEM write",128,"private state/history/intermediate spills can use direct memory egress without claiming T commit; durable ACK and visibility supplied by future MEM contract")
    ]
    return [{"route_id":i,"source":s,"destination":d,"transport_bits":w,"contract":t,
             "implementation_status":"not_assessed_here; separate evidence audit required",
             "is_direct_compute_to_compute_connection":False} for i,s,d,w,t in rows]


def physical_expansion(src,dst):
    # Expansion is transport only. Mandatory algorithm arithmetic remains explicit
    # as a separate edge to E/NUM, not magically inserted by this routing function.
    if src in COMPUTE or src in ("NUM","IDX"):
        prefix=["P_CAP","P_SW"]
    elif src=="T":
        if dst in ("EXT","MEM"):return ["P_TO"]
        prefix=["P_TO","P_IN"]
    elif src in ("EXT","MEM","PARAM"):prefix=["P_IN"]
    elif src=="S":prefix=[]
    else:prefix=[]
    if dst=="M":return prefix+["P_ML"]
    if dst=="MEM":return prefix+["P_SR","P_MO"]
    if dst=="T":return prefix+["P_SR","P_TW"]
    if dst=="S":return prefix
    endpoint={"N":"P_N","E":"P_E","G":"P_G","R":"P_R","NUM":"P_NUM","IDX":"P_IDX"}.get(dst)
    if endpoint:return prefix+["P_SR",endpoint]
    return prefix


def edge(code,src,dst,role,format_rule,sync,extra=None):
    row={"edge_id":code,"producer_macro_or_service":src,"consumer_macro_or_service":dst,
         "data_role":role,"format_and_layout_rule":format_rule,"wait_and_release_rule":sync,
         "candidate_transport_route_ids":physical_expansion(src,dst),
         "route_is_proof_of_direct_physical_macro_pair":False,"implementation_status":"not_assessed_here"}
    if (src=="R" and dst in ("N","G")) or (dst=="R" and src in ("N","G")):
        row["numeric_adapter_is_required_unless_exact_units_and_range_proved"]=True
        row["conditional_adapter_route_expansions"]=[
          physical_expansion(src,adapter)+physical_expansion(adapter,dst) for adapter in ("E","NUM")]
        row["adapter_limit"]="transport/gather does not rescale; E13 only its valid S32->S16 subset, static field selection/extension only with proven units/range, otherwise actual NUM/proven lowering"
    if extra:row.update(extra)
    return row


def common_inputs():
    return [edge("INPUT","EXT","N","hidden X/Y -> source input or pre-tail Norm","declared logical H and accepted S16 units; stage full Norm group and original replay values","input stored ACK before stats; residual original survives until final add"),
            edge("WEIGHTS","MEM","M","all projection weights, including selected expert weights","prepack/transform real weights to B n-major8*n+k; S8 one B512, S16 half0 then half1; tile/base alignment","weight tile stored ACK + descriptor accepted + A/B retired + loader done before EXEC; reuse_b needs exact identity"),
            edge("GAMMA","PARAM","N","gamma and exact epsilon binding","gamma in aux matching original replay lane; RMS0 gamma=1+weight; L2 no learned source gamma and unknown epsilon kept explicit","read/capture matching data+aux before command; epsilon may come from stable prebuilt control table"),
            edge("CONSTANTS","PARAM","E","bias, scales, cos/sin and residual companions as selected by source","E native8S16; RoPE interleave half-vectors to adjacent x1/x2, B_even=cos/B_odd=sin; partial channels bypass","real payload source or stable prebuilt ROM; do not fabricate gamma/cos/scale at metal wiring time"),
            edge("TEMP_SPILL","S","MEM","intermediate/residual/original-replay overflow -> real staging","actual immutable slots/ranges; never pretend S16KiB fits whole gate/up/mid/KV/state","MEM stored ACK before local slot release; implementation/interface deferred"),
            edge("TEMP_RELOAD","MEM","S","stored intermediate/runtime parameter/input -> local staging","restore exact format/layout/version, not arbitrary carrier reinterpretation","wait S write ACK before source is consumed by gather/loader"),
            edge("OUTPUT_DRAIN","T","EXT","sealed chunk -> other island/host or selected MEM sink","T words opaque128, actual valid bytes/count/tensor fragment identity maintained outside T","all destination stored ACK and final TAKE/RELEASE; chunk last does not imply complete sublayer/state commit")]


def softmax_edges(prefix):
    return [edge(prefix+"_SCORE","M","E","QK dot -> source score scale/mask","M read32 containers need accepted units; mask/access rule may need checked selection, cannot assume S16 represents -infinity","full D dot before scale; save exact score array for stats and EXP"),
            edge(prefix+"_MASK","E","E","scaled score -> mask/access transform","preserve source scale and causal/local accessible positions; explicit second E operation if selected","both score and mask/access operands captured; output ownership stable"),
            edge(prefix+"_STATS","E","N","whole logical score row -> stats and EXP passes","N op1 then op2; original score replay to op3; actual count and max-context lineage","complete full row stats before op3; native count65535 limit not silently truncated"),
            edge(prefix+"_EXP","N","N","EXP output -> exact EXP replay","op3 U16 UQ1.15 codes<=32768 stored unchanged; op4 factor then op6 -> probability Q14","all EXP writes ACK, exp_count=count, factor valid and same row/context; original scores are not op6 EXP"),
            edge(prefix+"_PV","N","M","probabilities -> PV A operands","Q14 S16; V scale determines PV units/read shift; B must real n-major value tiles","complete probability write/pack then loader; one N group must finish before BEGIN next")]


def attention(gated):
    rows=common_inputs()+[
      edge("A_NORM_PROJ","N","M","input Norm -> QKV/Q_gate projections","full H replay -> accepted M A S8/S16; aligned A containers","save Norm output, residual X retained; sequential M projections export before overwrite"),
      edge("A_PROJ_BIAS","M","E","source QKV bias / head input layout","Qwen2.5 actual bq/bk/bv before following transforms; numeric conversion not a bitcast","projection and matching bias captured; absent-bias models bypass arithmetic"),
      edge("A_QKNORM","M","N","source Q/K head Norm","Qwen3 ordinary RMS, Gemma/Qwen3.5 RMS0; one complete D/head; NONE for Qwen2.5/Llama/Phi","each norm stats+gamma/original replay complete, then save before next head"),
      edge("A_NORM_ROPE","N","E","normalized Q/K -> RoPE","only source QK-Norm models; full or partial rotary ranges retained","save all head outputs and correct cos/sin frame before E9"),
      edge("A_PLAIN_ROPE","M","E","unnormalized Q/K -> source RoPE","no-QK-Norm/no-bias models; Phi fused5120 split Q3072/K1024/V1024, RoPE96/128","Qwen2.5 uses explicit bias-then-RoPE next role"),
      edge("A_BIAS_ROPE","E","E","Qwen2.5 biased Q/K -> RoPE","bias is applied before source RoPE; no QK head Norm","capture biased values before E9, not add bias after rotation"),
      edge("A_QK","E","M","rotated Q/K -> QK operands","correct head/token transpose; GQA shared-head selection; M A rows/B n-major","KV stored/visible, weight identity replaced by dynamic K tile identity; all operand buffers ready"),
      edge("A_KV_SAVE","M","MEM","current V -> KV lifecycle","V direct projection/layout; K comes from separate E post-RoPE role; shared KV heads, no forced repeat storage","current data must durable/store-visible before QK/PV; external-memory semantics deferred"),
      edge("A_K_SAVE","E","MEM","post-RoPE K -> KV next version","correct position/window/layer, GQA shared heads","KV update/root visibility controlled, not one T commit"),
      edge("A_KV_READ","MEM","M","past/current K/V -> QK/PV B data","head group and causal/local window selection; actual transpose/pack/n-major into S B layout","all selected tile data available and loader done; memory latency/identity not bypassed")]
    rows+=softmax_edges("A")
    if gated:
        rows += [edge("A_GATE_X","M","G","Q_gate split activation -> G.x","per-head Q256/Gate256 split of8192; Gate Q10 to fn1 gated","hold Gate for same token/head/context pair"),
                 edge("A_GATE_LINEAR","M","G","PV context -> G.linear_gate","4096 context narrowed to accepted Q10; G.fn1 gated output Q10 (product>>14)","PV full D and both companions matched; no gate before QK"),
                 edge("A_GATE_WO","G","M","Sigmoid(Gate)*context -> Wo input","pack twoS16 outputs to A layout; tail lanes counted","complete G issue/retire and write ACK before loader/Wo")]
    else:
        rows += [edge("A_PV_WO","M","M","PV context -> Wo input","saved context is actual tensor, not reuse of M merged result without restore","export PV before Wo overwrites M; pack/layout/load stored context")]
    rows += [edge("A_WO_POSTN","M","N","Gemma Wo -> post-attention RMS0","full H2560, gamma=1+weight; only source Gemma","complete down-to-H output before post Norm; residual X retained"),
             edge("A_POSTN_RES","N","E","Gemma post-attention Norm -> residual1","same declared units as saved X","Add after postNorm, never move postNorm across residual"),
             edge("A_WO_RES","M","E","ordinary Wo and Granite gain -> residual1","Granite gain0.22 before Add; legal narrow or explicit NUM conversion if needed","X and branch from same layer/token; do not publish errored/saturated-disallowed value"),
             edge("A_RES_STORE","E","T","Y after first residual -> sealed output chunk","full H tensor fragmented; compact/padded layout must be declared, count+valid tail external","T BEGIN; correct sequential writes; full job done only after all fragments/stored ACK/release")]
    return rows


def ffn():
    return common_inputs()+[
      edge("F_NORM_PROJ","N","M","pre-FFN Norm -> gate/up projections","full H, Phi fused gate_up2I exact split","Norm complete, save Y residual and projection results before next M use"),
      edge("F_GATE","M","G","gate projection -> G.x","SiLU fn0 or Gemma GELU_tanh fn2; accepted Q10, never Up as activation","matching token/I-slice, both inputs captured"),
      edge("F_UP","M","G","Up projection -> G.linear_gate","linear companion, not already-SiLU value; Q10","one M result exported before computing other projection"),
      edge("F_FALCON_GATE_SCALE","M","E","Falcon gate projection -> pre-SiLU MuP","0.353553... before activation; accepted numeric lowering","store scaled gate then feed G; do not apply same scale to Up"),
      edge("F_SCALED_GATE","E","G","Falcon scaled gate -> G.x","fn0 gated with same unscaled Up","accepted/retired pair count and association"),
      edge("F_MID","G","M","activation(gate)*Up -> down projection","pack G2S16, store full required I or proven memory/tile schedule","single M cannot keep down partial while overwriting it for next gate/up; MEM/extra scheme gap retained"),
      edge("F_POSTN","M","N","Gemma down output -> post-FFN RMS0","full H2560, before residual2","Norm statistics+replay complete"),
      edge("F_NORM_RES","N","E","Gemma post-FFN Norm -> residual2","match Y units and gamma semantics","original Y retained until successful add/output storage"),
      edge("F_DOWN_RES","M","E","other down output -> optional output gain/residual2","Falcon0.078125 after down; declared units before E add","all-I accumulation done before output quantization/gain"),
      edge("F_GAIN_RES","E","E","scaled branch -> Add(Y,branch)","separate operations if FMA units/range do not match","capture branch and original Y before add"),
      edge("F_OUTPUT","E","T","O after second residual -> output chunks","full logical H and token count retained","T lifecycle and destination stored ACK, not scalar busy falling")]


def recurrent(profile):
    d=profile=="D"
    rows=common_inputs()+[
      edge("R_NUM_PARAMETERS","PARAM","NUM","coefficient constants, A_log/A_rate, wide bias, D/skip and H dt limits","real parameter payload in accepted wide units; static A_rate may be folded only after format/quality acceptance","S/ROM snapshot and identity stable with same layer/token; NUM cannot invent constants"),
      edge("R_NORM_PROJ","N","M","input Norm -> recurrent/branch projections","D RMS0, H one shared ordinary RMS2560","shared normalized input snapshot persists for all required projections/branches"),
      edge("R_PROJECT_CONV","M" if d else "E","R","D qkv8192 or H MuP-scaled XBC4608 -> conv4 current x","R x is4S32 packets; accepted common F, explicit expand/shift if logicalS16","history/taps/current values loaded before op6 mode2; each layer/channel slice identity"),
      edge("R_HISTORY_IN","MEM","R","old conv history and taps -> R","op9 history4S32, op10 taps8S16; true kernel/old-tail history","no OPEN of next tile while pending; restore correct old version"),
      edge("R_CONV_STORE","R","MEM","new conv history -> privateNext","op12 output saved BEFORE op7; wait COPY ACK then op14 exports new history","all history writes durable ACK; no full-version publication just because one tile committed"),
      edge("R_STATE_IN","MEM","R","old full recurrent state -> native tile","GDN[B,32,128,128] or SSM[B,32,128,256]; active S32 tiles","restore full selected tile and numerical units before EXEC; local8KiB is not full model state"),
      edge("R_STATE_LOOP","R","R","state step output -> later token/tile input","op7 local commit, op11 export to S/MEM next root then reload; oldRoot preserved until publication","local op7 irreversible; full-root publish only after complete state/history ranges ACK",{"loop_kind":"external_state_version_feedback","external_memory_in_path":True}),
      edge("R_OUT_STORE","R","MEM","committed state -> privateNext/root service","actual fourS32 read packets, full range and owner/epoch/position","wait each stored ACK; incomplete next isolated, never blind append retry"),
      edge("R_Z_GATE","M" if d else "E","G","Z projection (H after MuP) -> output G.x SiLU","Z Q10; linear gate companion comes from source-correct R/N stage","keep token/head/channel pairing across recurrent and projection latencies"),
      edge("R_DT_BIAS","M" if d else "E","E","a/dt projection (H after MuP) -> dt_bias","D a32+dt_bias; H dt32 with per-segment MuP already applied","constants actual payload/parameter source, not fabricated"),
      edge("R_DT_SOFTPLUS","E","G","dt-bias sum -> Softplus fn3","Q10 input/output; H source Clip still explicit","G fn3 does not generate decay Exp"),
      edge("R_DT_NUM","G","NUM","dt Softplus -> H source Clip -> coefficient generation","dynamic dt and actual A/B/C/X units; H Clip is retained in NUM stage; generic Exp/inject not supplied by N/G","NUM inputs complete with constants, range/rounding/version accepted"),
      edge("R_COEFF","NUM","R","decay/beta/inject/skip payloads -> R","GDN op5 scalar UQ1.31 decay/beta; SSM op15 per-element UQ1.31 decay plus op4 inject/op5 skip; honor all native guards","SSM decay shadow loaded before EXEC; coefficients belong to same token/tile/state version"),
      edge("R_OUTPUT_PROJECT","G" if d else "N","M","normalized/gated recurrent output -> Wout","D RMS->SiLU(Z) gate output4096; H SiLU(Z) gate->global RMS4096","complete required head/global group and materialization before Wout"),
      edge("R_OUTPUT_RES","M","E","Wout -> source scale/residual","H branch gain before mix; D direct first residual","preserve X until all same-token branches arrived")]
    if d:
        rows += [edge("D_CONV_SILU","R","G","conv result -> G.x SiLU","R output4S32 unitF -> legal Q10 narrow; E13 only if exact S32 case, otherwise NUM","op12 saved and formatted before R commit clears output-valid"),
          edge("D_QK_REPEAT_L2","G","N","conv-SiLU Q/K -> repeat16to32 then L2","head(value)=floor(value/2), full128, actual graph Repeat before L2; no learned gamma, epsilon unknown","layout/pack and complete group barriers; reduced16-L2 execution not assumed"),
          edge("D_Q_SCALE","N","E","L2 query -> 1/sqrt128 scale","only Q additionally scaled; accept raw gamma/output Q14 contract explicitly","same head/128 group and accepted scale"),
          edge("D_QUERY","E","R","scaled Q -> R.query","native S16 Q14, not blind N/G unit bitcast","load full query groups before GDN EXEC"),
          edge("D_KEY","N","R","L2 K -> R.key","native S16 Q14; K has no Q-only extra scale","load full key groups before EXEC"),
          edge("D_VALUE","G","R","conv-SiLU V -> R.x value","V4096 mapped to32 value heads, R S32 state-unit input; accepted expand/rescale","8-lane slices matched with query/key/beta/decay"),
          edge("D_BETA","M","G","beta projection -> ungated Sigmoid fn1","G ungated Sigmoid Q14, unlike gated Q10","beta data/count preserved by value head"),
          edge("D_BETA_FORMAT","G","NUM","Sigmoid beta -> UQ1.31 formatting/check","accepted nonnegative Q14 to Q31 may use proved shift17/field expansion; do not declare G output already Q31","same head, [0,1] and packing proof; no arbitrary reinterpretation"),
          edge("D_RMS","R","N","recurrent readout -> per-value-head RMS128","S32 unitF -> valid N S16 units with explicit conversion;32 groups, ordinary RMS gamma=weight","collect all128, stats and original/gamma replay; save before next R tile overwrites"),
          edge("D_NORM_GATE","N","G","RMS128 output -> G.linear_gate","G.x is SiLU(Z) activation input; normalized R is linear gate input","RMS BEFORE Z gate; same token/head/lane companions"),
          edge("D_FINAL","E","T","D residual1 Y -> output chunk","full H2560 preserved","full output/state/history close conditions distinct")]
    else:
        rows += [edge("H_MUP","M","E","SSM Win8736 -> per-segment MuP","five Z/X/B/C/dt segments have distinct scales; split4096/4608/32","do not collapse to one gain or alter branch source Norm"),
          edge("H_CONV_BIAS","R","NUM","XBC conv output -> actual bias add","R conv has no bias operand; common S32/unitF bias before SiLU","save complete valid output; legal wide add/rounding/range required"),
          edge("H_CONV_SILU","NUM","G","biased conv output -> G.x SiLU","legal Q10 narrowing before activation; not E16 as arbitrary wide bias","matching bias/channel and conv history version"),
          edge("H_BC","G","R","conv-SiLU B/C -> key/query coefficients","B256/C256 from one group broadcast to32 heads, accepted R Q14 units","correct state rows and same dt/head; actual group broadcast/layout hardware"),
          edge("H_X_NUM","G","NUM","conv-SiLU X -> dt*X injection and D*X skip","NUM converts coefficient and state units, source source does not supply these automatically","dt/X/D and any B/C scaling matched"),
          edge("H_R_GATE","R","G","SSM readout+skip -> G.linear_gate","R S32 unitF -> legal G Q10; G.x is Z for fn0 gated","gate BEFORE Norm, not D-style R->N->G"),
          edge("H_GATE_RMS","G","N","SiLU(Z)*readout -> one global RMS4096","entire4096 across heads, not32 separate128 norms","all4096 accepted gate outputs saved, stats+original/gamma replay complete"),
          edge("H_SHARED_ATTN","N","M","same shared normalized input -> attention projections","do not duplicate input RMS; immutable N snapshot used by SSM too","both consumers have durable data before snapshot release"),
          edge("H_K_SCALE_ROPE","M","E","Q/K projection -> full RoPE128, K only pre-multiplier","K0.044194... distinct from QK score scale; Q has no such pre-multiplier; proper paired layout","all source constants/position same as attention branch"),
          edge("H_QK","E","M","rotated Q/K and shared KV -> QK","GQA5 and n-major K/V tile layout; memory KV lifecycle also required","KV writes/read visibility and loader done before relevant matrix"),
          edge("H_KV","MEM","M","attention old/current KV -> QK/PV","causal shared heads, layer/token identity, correct transpose/pack","real memory request/data/ACK; no free source"),
          edge("H_KV_NEXT","E","MEM","prepared attention K -> KV next","K post-RoPE; V retains separate M projection/layout identity; no forced repeated storage","durable visibility gate separate from recurrent root publication"),
          edge("H_V_NEXT","M","MEM","attention V projection -> KV next","V has no RoPE; shared KV head layout/position retained","actual write ACK before PV reads current V"),
          edge("H_PV_WO","M","M","attention PV -> Wo","store actual context1280 before overwriting M","single M sequential phases, no result restore"),
          edge("H_JOIN","E","E","scaled attention and scaled SSM -> mix, then residual1","Add(attn_scaled,ssm_scaled) then Add(X,mix); matching token/version","two branch-arrival bits/storage; one shared local owner, no two controllers drive M/S"),
          edge("H_FINAL","E","T","hybrid residual1 Y -> output chunk","H2560, full tensor not merely one T batch","output stored ACK and state publication explicitly separate")]
        rows += softmax_edges("H_ATTN")
    return rows


def moe():
    return common_inputs()+[
      edge("X_NUM_PARAMETERS","PARAM","NUM","gain0.22 and accepted merge scale/range parameters","constant/parameter payload is distinct from dynamic probabilities; actual numeric formats pending","capture stable accepted parameter version before rank accumulation/final gain"),
      edge("X_NORM","N","M","one pre-MoE RMS -> router/expert tokens","H1536 normalized once; expert internal path adds no new Norm","preserve Y residual and normalized token for selected8 ranks"),
      edge("X_ROUTER","M","N","router40 logits -> TopK records","accepted S16 score and U16 expertID0..39 fields; save original logits","finish all40 records before TOP_SELECT; no per-expert fabricated static IDs"),
      edge("X_IDS","N","IDX","TopK IDs -> checked gather and expert-weight address selection","IDs only, not logits or routing probability; keep rank","source ID-domain/range and original-logit/expert-layout proof; do not feed ID as numeric score"),
      edge("X_SELECTED_LOGITS","M","N","stored original selected logits -> Softmax8","IDX selects actual saved M logits by N IDs; N op0 mode0/op1/2/3/4/6 on selected8","TOP_SELECT output does not contain scores; all selected scores must exist before stats"),
      edge("X_ROUTE_EXP","N","N","routing EXP -> probability replay","exact UQ1.15 EXP then factor/op6 Q14, same selected8/rank order","EXP storage ACK and same factor/ID ordering"),
      edge("X_WEIGHTS","MEM","M","ID-selected actual expert gate_up/down weights","all40 experts in scope, per expertI512, fusedGU1024 then down1536; B n-major","weight request identity and stored/loader done before expert EXEC"),
      edge("X_GATE","M","G","expert gate -> G.x SiLU","fn0 gated, correct split512 and Q10","same token/rank/expert/I slice as Up"),
      edge("X_UP","M","G","expert Up -> G.linear_gate","linear Up Q10, not activation output","export each M result before next expert/projection overwrites"),
      edge("X_MID","G","M","expert gate*Up -> down input","full I512 or proved stored schedule","compact/padded A layout and loader complete"),
      edge("X_RETURN","M","NUM","expert return1536 -> weighted wide merge values","declared common Fin across ranks; S32/S64 selected source not arbitrary S16 FMA","save/export before next expert overwrites M merged context"),
      edge("X_PROB","N","NUM","routing probabilities -> merge weights","same selected rank/ID, Q14 or independently accepted format","probability from exact selected8 Softmax, retained until corresponding rank consumed"),
      edge("X_ACC","NUM","NUM","wide accumulator across all8 rank returns","real accumulator/context and rank-mask, precision/range/rounding proof","all ranks complete before publish; no loss when M reused",{"loop_kind":"NUM_retained_accumulator_context_not_native_seven_macro_connection"}),
      edge("X_GAIN","NUM","E","weighted sum and source gain0.22 -> residual2","NUM handles required wide gain/narrowing or approved decomposition; E add only accepted narrow units","single final gain/rounding order accepted, original Y retained"),
      edge("X_OUTPUT","E","T","MoE residual2 O -> output chunk","H1536 with complete token/rank result","all8 ranks arrived, checked errors, then T chunk lifecycle")]


def build(root):
    aux=root/"work/Melodydt/151"
    sized=json.loads((aux/"block-variant-models.json").read_text(encoding="utf8"))
    lock=json.loads((aux/"phase2-source-lock.json").read_text(encoding="utf8"))
    if lock["selected_PR144_ref"]!=LEAF:raise AssertionError("leaf ref drift")
    sources=[]
    for item in lock["core_files"]:
        raw=(root/item["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item["sha256"]:raise AssertionError("source byte drift")
        sources.append({"path":item["path"],"sha256":item["sha256"],"url":url(item["path"],LEAF)})
    definitions={"A_plain":attention(False),"A_gate":attention(True),"F":ffn(),"D":recurrent("D"),"H":recurrent("H"),"X":moe()}
    routes=physical_routes();rows=[]
    for v in sized["variant_rows"]:
        name=v["variant_id"];edges=definitions[name]
        pairs=sorted({(e["producer_macro_or_service"],e["consumer_macro_or_service"]) for e in edges if e["producer_macro_or_service"] in COMPUTE and e["consumer_macro_or_service"] in COMPUTE})
        active=[m for m in COMPUTE if v["counts"][m]]
        rows.append({"variant_id":name,"macro_counts":v["counts"],"data_role_edges":edges,
                     "required_service_ids":["CTRL_NATIVE","PARAM_SOURCE","S_ARB_ACK","GATHER","CAPTURE_PACK","LAYOUT_IDX","GROUP_REPLAY","FORK_JOIN","T_EGRESS","MEM_ENDPOINT"]+(["NUM"] if name in ("D","H","X") else [])+(["R_VERSION"] if name in ("D","H") else []),
                     "conditional_services":(["NUM/proven conversion for source units or widths not handled by chosen native read/format"] if name in ("A_plain","A_gate","F") else [])+(["long-row Softmax algorithm/resources if admitted count exceeds65535"] if name in ("A_plain","A_gate") else []),
                     "logical_compute_pair_union":[{"source":a,"destination":b,"means_direct_physical_wire":False} for a,b in pairs],
                     "true_payload_feedback_rows":[e["edge_id"] for e in edges if e["producer_macro_or_service"]==e["consumer_macro_or_service"]],
                     "time_multiplexing_is_not_a_payload_edge":["M multiple matrices/segments","N multiple norm/Softmax groups","G different activation functions/phases" if v["counts"]["G"] else "no G","R conv/state/layers" if v["counts"]["R"] else "no R"],
                     "physical_route_ids":sorted({i for e in edges for path in [e["candidate_transport_route_ids"]]+e.get("conditional_adapter_route_expansions",[]) for i in path}),
                     "capture_enabled_compute_sources":sorted(active),"physical_input_M_route":"P_ML",
                     "stage_order_source":v["source_stage_order"],"stage_order_is_compiled_program":False,
                     "implementation_status":"separate evidence audit; not inferred from role/pair/port compatibility"})
    union=sorted({(p["source"],p["destination"]) for row in rows for p in row["logical_compute_pair_union"]})
    return {"schema_version":1,"issue":151,"owner":"Melodydt","research_parent":PARENT,"leaf_source":LEAF,
       "scope":{"six_variants":list(definitions),"repository_samples":8,"decoder_layer_types":10,"all49_pair_crossbar_required":False,
                "RTL_simulation_server_or_remote_write_this_round":False,"implementation_status_audited_here":False,"system_has_external_memory":True,"MEM_protocol_design":"deferred"},
       "interpretation":{"logical_edge":"producer/consumer algorithm data role; may need explicit format/layout materialization",
          "source_option_union":"each variant is the union of its source model/layer options, not an unconditional compiled execution of every listed role",
          "physical_route":"named endpoint hops in shared S-centered candidate network; only P_ML dedicated Sloader->M compute input",
          "no_double_count_rule":"M->N functional dependency expanded via capture/S/gather does not create or prove a direct M->N wire; count this transport once",
          "arithmetic_not_free_transport":"NUM/E algorithm work is an explicit edge/node; S or formatter does not supply arbitrary arithmetic",
          "required_service_not_minimal_instance_count":"catalog describes functions and ownership, not fixed buffer counts/area or complete hardware"},
       "shared_physical_route_catalog":routes,"variant_rows":rows,
       "logical_compute_pair_union_all_variants":[{"source":a,"destination":b,"is_physical_direct_connection":False} for a,b in union],
       "shared_sync_services":[
         {"id":"CTRL_NATIVE","role":"one local owner drives native command/phase/ready and waits each correct ACK/error; actual native protocols remain different"},
         {"id":"PARAM_SOURCE","role":"weights/gamma/bias/cos/sin/taps/state values from real MEM/S or prebuilt stable ROM; op/shift/count/epsilon may be static table fields; dynamic factors require approved controlled capture"},
         {"id":"S_ARB_ACK","role":"one ordinary S owner per request; consume/classify write ACK; loader wide priority handled by fixed schedule or real arbitration; no holding S response while needing next S operation"},
         {"id":"GATHER","role":"up to three128-bit operand slots as shared reference; E A/B/C3, N data/aux2, G x/gate slice2; sufficient metadata/count/valid ownership required"},
         {"id":"CAPTURE_PACK","role":"selected result capture, source-op classifier, G2lane pack/retire, E13 low64 handling, wholeword tail ownership; no free wire-OR or blanket S64 cast"},
         {"id":"LAYOUT_IDX","role":"split/fused/per-head reorder, RoPE half interleave, transpose, GQA/head repeat, M n-major; real checked dynamic ID/address gather"},
         {"id":"GROUP_REPLAY","role":"N full-group stats/factor/replay lineage; original/gamma data distinct from EXP/probability; N count4 can consume E13 half without mandatory merge8"},
         {"id":"NUM","role":"explicit coefficient Exp/inject, Falcon wide bias, accepted wide conversion and MoE weighted accumulation/gain; interfaces/counts/numeric acceptance pending"},
         {"id":"FORK_JOIN","role":"stable residual/branch snapshots, same token/head/rank/version pairing and arrival bits; branch value not reusable before last consumer stored/finished"},
         {"id":"R_VERSION","role":"save output before local commit; wait COPY then export active/history; restore old full roots and publish next only after real durable ACK of all required ranges"},
         {"id":"T_EGRESS","role":"BEGIN/sequential writes/SEALED/COMMIT/read/last/release per chunk, independent egress progress and stored ACK; job and state completion separate"},
         {"id":"MEM_ENDPOINT","role":"weights/KV/history/state/expert/runtime parameters/input/output/intermediates have real source/destination; no assumed zero latency/unbounded bandwidth or existing controller"}],
       "native_response_classification":{"M":{"tensor_ops":[3,5],"other":"EXEC faultmask/scale/clear/load lifecycle ACK not tensor"},
           "N":{"vector_ops":{"3":"EXP UQ1.15","5":"Norm S16","6":"probability Q14"},"structured_ops":{"7":"mixed statistics","10":"U16 TopK IDs only","11":"factor32"},"other":"BEGIN/STATS/FINALIZE/etc ACK or errors"},
           "E_G":"typed output only for corresponding accepted op/fn/gated; errors/saturation and tail policy checked",
           "R":{"payload_ops":{"11":"active4S32","12":"output4S32","14":"history4S32"},"metadata_op":13,"other":"ACK/error or controlled metadata, not automatic tensor"},
           "S":"write response echoes din but is an ACK; read response source owner retained","T":"opaque128 word; index/last is batch-relative, not tensor shape/element count"},
       "endpoint_shape_rules":{"E":"3x128 inputs, op4bits/shift5bits; most selected ops need<=2 payloads, unused C explicit constant",
          "N":"data128+aux128, op4/count4/param32; actual vector count1..8; gamma/original matched",
          "G":"x32+linearGate32,fn3/gated1; pair serializer and issued/retired count; fn1 ungatedQ14 vs gatedQ10",
          "M":"A128/B512+bank/row/tile/fmt/half via Sloader; cmd4/index6/data64 separate; B n-major8*n+k",
          "R":"cmd4/index10/data128; output4S32 per128; key/query8S16Q14; x/state/conv S32 unitF and coefficients UQ1.31; format proof required",
          "S_T_MEM":"S wholeword128 no byte mask, T384 opaque words; future MEM width/address/ACK not fixed by128 internal carrier"},
       "model_binding_reference":{"source":"work/Melodydt/151/block-variant-models.json","logical_invocations":sized["global_logical_variant_invocations"],"counts_are_not_instances_or_route_bandwidth":True},
       "provenance":{"inputs":[file_info(aux/n,"work/Melodydt/151/"+n) for n in ["block-variant-models.json","family-spec.json","phase2-source-lock.json"]],"native_core_SHA_checked":sources}}


def validate(data):
    checks=[];routes={r["route_id"] for r in data["shared_physical_route_catalog"]}
    def ck(name,value):
        if not value:raise AssertionError(name)
        checks.append(name)
    ck("six exact variants",[r["variant_id"] for r in data["variant_rows"]]==["A_plain","A_gate","F","D","H","X"])
    for row in data["variant_rows"]:
        name=row["variant_id"];edges=row["data_role_edges"]
        ck(name+" unique local edge IDs",len({e["edge_id"] for e in edges})==len(edges))
        for e in edges:
            ck(name+"/"+e["edge_id"]+" physical refs exist",all(r in routes for r in e["candidate_transport_route_ids"]))
            ck(name+"/"+e["edge_id"]+" no absent compute macro",all(node not in COMPUTE or row["macro_counts"][node]>0 for node in [e["producer_macro_or_service"],e["consumer_macro_or_service"]]))
            ck(name+"/"+e["edge_id"]+" no direct-wire claim",not e["route_is_proof_of_direct_physical_macro_pair"])
        ck(name+" actual parameter/weight path",any(e["producer_macro_or_service"]=="MEM" and e["consumer_macro_or_service"]=="M" for e in edges) and any(e["producer_macro_or_service"]=="PARAM" for e in edges))
        ck(name+" T output path",any(e["consumer_macro_or_service"]=="T" for e in edges))
    by={r["variant_id"]:r for r in data["variant_rows"]}
    ck("A_plain no G physical endpoint",not any(e["producer_macro_or_service"]=="G" or e["consumer_macro_or_service"]=="G" for e in by["A_plain"]["data_role_edges"]))
    ck("A_gate both G roles",{e["edge_id"] for e in by["A_gate"]["data_role_edges"]}>={"A_GATE_X","A_GATE_LINEAR"})
    ck("D Norm then gate roles",{e["edge_id"] for e in by["D"]["data_role_edges"]}>={"D_RMS","D_NORM_GATE"})
    ck("H gate then global Norm roles",{e["edge_id"] for e in by["H"]["data_role_edges"]}>={"H_R_GATE","H_GATE_RMS"})
    ck("MoE ID path not score reinterpret",any(e["edge_id"]=="X_IDS" and e["consumer_macro_or_service"]=="IDX" for e in by["X"]["data_role_edges"]))
    ck("MoE saved actual score and wide merge paths",{e["edge_id"] for e in by["X"]["data_role_edges"]}>={"X_SELECTED_LOGITS","X_RETURN","X_PROB","X_ACC"})
    ck("implementation not audited by static roles",not data["scope"]["implementation_status_audited_here"])
    return {"status":"PASS_ROUTE_ROLE_CONSISTENCY_ONLY","checks_count":len(checks),"checks":checks,
            "variant_role_counts":{r["variant_id"]:len(r["data_role_edges"]) for r in data["variant_rows"]},
            "physical_route_catalog_count":len(routes),"RTL_or_direct_connection_acceptance":False}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--root",type=Path,default=Path("."));p.add_argument("--output-dir",type=Path,default=HERE);p.add_argument("--check",action="store_true")
    a=p.parse_args();data=build(a.root);result=validate(data)
    raw=(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n").encode("utf8")
    target=a.output_dir/"island-variant-routes.json"
    if a.check:
        if target.read_bytes()!=raw:raise AssertionError("byte recomputation mismatch")
    else:
        a.output_dir.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);result["artifact_sha256"]=hashlib.sha256(raw).hexdigest()
        (a.output_dir/"island-route-checks.json").write_bytes((json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf8"))
    print("PASS: {} route-role checks; {}".format(result["checks_count"],"byte-identical" if a.check else target))


if __name__=="__main__":main()
