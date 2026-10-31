"""Enumerate native role slots and static recipe guards; never simulates hardware."""
from pathlib import Path
import argparse
import collections
import hashlib
import itertools
import json

MACROS = ['M', 'N', 'E', 'G', 'R', 'S', 'T']
CLASSES = {
    'M.result64':'numeric', 'M.read32':'numeric', 'M.partial_diag':'diagnostic',
    'N.norm':'numeric', 'N.exp':'exp', 'N.probability':'probability',
    'N.topk_ids':'id', 'N.stats':'record', 'N.factor':'factor',
    'E.vector':'numeric', 'E.pack8':'numeric', 'E.cast32_to16':'numeric',
    'G.activation':'numeric', 'G.gated':'numeric',
    'R.output':'numeric', 'R.active_state':'numeric', 'R.active_history':'numeric',
    'R.meta':'record', 'S.stored_word':'typed_carrier', 'S.write_echo':'typed_carrier',
    'S.loader_A':'loader', 'S.loader_B':'loader', 'T.committed_word':'typed_carrier',
}
SRC_DETAILS = {
    'M.result64':('2xS64/128','product_F','M op3; valid row; capture before overwriting merged'),
    'M.read32':('4xS32/128','product_F_after_read_shift','M op5 logical8/16/32 remain S32 carriers; sat retained'),
    'M.partial_diag':('2xS40 sign-extended S64/128','pre_scale_partial_F','M op12 valid/owner; diagnostic algorithm binding required'),
    'N.norm':('count1..8 S16/128','declared_Norm_F','N op5; gamma/epsilon/factor context'),
    'N.exp':('count1..8 U16/128','15','N op3, max32768; preserve group/max/code lineage'),
    'N.probability':('count1..8 nonnegative S16/128','14','N op6, max16384; probability is not unnormalized EXP'),
    'N.topk_ids':('k1..8 U16/128','0_if_explicit_ID_AS_INT','N op10; ID not score or source-record position'),
    'N.stats':('mixed128','field_schema','N op7; select field before numeric casting'),
    'N.factor':('U32 low32/128','context_formula','N op11; formula and Norm/Softmax context required'),
    'E.vector':('8xS16/128','operation_declared_F','E op0..11; op-dependent role/scale'),
    'E.pack8':('8xS8 low64/128','declared_F','E op12; not four S16'),
    'E.cast32_to16':('4xS16 low64/128','declared_Fout','E op13; upper64 padding, tail external'),
    'G.activation':('2xS16/32','fn1_Q14_else_Q10','ungated function tag retained'),
    'G.gated':('2xS16/32','Q10_if_gate_Q10','gated fn and gate units retained'),
    'R.output':('4xS32/128, two packets','product_F','R op12 before commit/next EXEC clears output'),
    'R.active_state':('4xS32/128','product_F','R op11 active_valid; pending reads OLD active'),
    'R.active_history':('4xS32/128','product_F','R op14 history_valid; pending reads OLD history'),
    'R.meta':('mixed128','field_schema','R op13; does not expose all internal validity/failed flags'),
    'S.stored_word':('opaque128','inherited_schema','read response must match known initialization/writer schema'),
    'S.write_echo':('opaque128','inherited_write_schema','explicit ACK-forward only; capture echo and ACK before same-S reentry'),
    'S.loader_A':('8xS8 low64 or8xS16/128','descriptor_schema','bank/row/tile/wide; complete both A/B obligations'),
    'S.loader_B':('64xS8 or32xS16/512','descriptor_schema','n-major/half; split512; complete both A/B obligations'),
    'T.committed_word':('opaque128','inherited_lease_schema','committed sequential index/last; tail separate; release after drain'),
}
FIELDS = {
    'N.stats':{'count':{'bits':[15,0],'type':'U16','F':'0'},
               'max':{'bits':[31,16],'type':'S16','F':'input_F'},
               'min':{'bits':[47,32],'type':'S16','F':'input_F'},
               'sum':{'bits':[79,48],'type':'S32','F':'input_F'},
               'sumsq':{'bits':[127,80],'type':'U48','F':'2*input_F'}},
    'R.meta':{'length':{'bits':[8,0],'type':'U9','F':'0'},
              'pending_state':{'bits':[9,9],'type':'U1','F':'0'},
              'pending_history':{'bits':[10,10],'type':'U1','F':'0'},
              'output_valid':{'bits':[11,11],'type':'U1','F':'0'},
              'owner':{'bits':[63,32],'type':'U32','F':'0'},
              'epoch':{'bits':[95,64],'type':'U32','F':'0'},
              'position':{'bits':[127,96],'type':'U32','F':'0'}},
}
COND = {
 'C_FAMILY':'FamilySpec explicitly authorizes mathematical role/operation and this profile version.',
 'C_UNITS':'Source raw formula/Fin and destination Fout/range/overflow policy declared; no arbitrary relabel.',
 'C_SHAPE':'Valid elements, range, layout, strides, tail and companions match; padding is not data.',
 'C_SCHEMA':'Typed carrier inherits trustworthy initialization/write/lease schema and lineage; dispatch recursively.',
 'C_FIELD':'Record schema and selected field(s), signedness/extension/F are explicit; whole record is not numeric vector.',
 'C_ID':'Explicit ID_AS_INT(F=0), ID domain use, or ID_RESOLVE lookup; IDs never become logits by relabel.',
 'C_DIAG':'Product declares partial arithmetic meaning, pre-scale units and exact valid/owner lifetime.',
 'C_FACTOR':'Factor raw formula and source context establish meaningful coefficient units.',
 'C_EXP_NUM':'EXP used as unnormalized exponential value, or input to a new declared arithmetic task; not probability.',
 'C_PROB':'Probability provenance/scale retained; not relabeled as EXP or arbitrary coefficients.',
 'C_EXP_LINE':'Destination replay receives exact EXP codes whose group/max/aggregate factor it owns, or proven lossless equivalent lineage.',
 'C_SCORE_LINE':'EXP_X replays the score handle used in this group STATS; same max/version/order/valid count.',
 'C_RECORD':'TOP_RECORDS has score S16 plus ID U16; current edge provides named field(s), companions explicitly JOINed.',
 'C_COEFF':'R decay/beta/element_decay values represent the declared coefficient, UQ1.31 in 0..0x80000000; CAST alone does not compute it.',
 'C_INJECT':'R inject is an already computed algorithm quantity with units F; packing cannot create the missing arithmetic.',
 'C_E_C':'E C units/meaning match selected op: product-scale FMA or SELECT predicate, etc.',
 'C_M_FMT':'M A/B format S8/S16 selected, bank/rows/tile identities and n-major layout correct.',
 'C_N_GAMMA':'Norm gamma mathematical parameter and Q10 encoding/desired output scale explicitly bound.',
 'C_PARAM':'Unique control owner validates exact field, authorized dynamic/permanent update, identity, bounds and reserved bits.',
 'C_INTEGRAL':'Addresses/opcodes/counts/IDs are exact integers; reject invalid fields rather than modulo/unchecked clamp.',
 'C_ACK':'ACK-forward binds original write schema/version, captures payload and consumes write ACK before resource reentry.',
 'C_DEST_OP':'Selected destination opcode/mode actually consumes this named role; G.gate requires gated=1, E B/C require an operation using them.',
 'C_COMPANION':'All required independent inputs/compound fields are named and supplied by companion handles or declared ROM constants before execution.',
}
STATE = {
 'S_VALID':'Source valid/error/sat handling and lifetime checked; no stale or already released source.',
 'S_READY':'Destination native phase/ready/window legal; otherwise WAIT/RESUME/REENTER, not declaring whole pair illegal.',
 'S_OWNER':'Only one native owner; task/epoch/version cannot be mixed or prematurely reused.',
 'S_LOADER':'Consume all A/B outputs via predefined selected sinks/discards; no abort or waiting for same-S write while done is blocked.',
 'S_N_CONTEXT':'Lock N group and phase counters; preserve context during RESUME; finish old group before unrelated BEGIN.',
 'S_R_CONTEXT':'Respect native pending matrix. state/history/taps/element_decay need no pending; key/query/x/coeff/skip permit history-only pending.',
 'S_T_LIFE':'BEGIN/FILL/SEALED/COMMIT/READ/RELEASE; metadata alone grants no requester access; no rewind.',
 'S_REENTER':'Capture old result before overwrite; ordinary same-resource reentry is distinct from same-context RESUME.',
}
MAP = {
 'K_ONCHIP':'No external memory. Existing S payload16384B and T payload6144B plus explicitly budgeted new on-chip support storage only.',
 'K_SLOTS':'Reserve full required S words, output/event slots and companions; S insufficient => mapping gap, not semantic illegal.',
 'K_LOADER':'Serial S baseline uses separate prefabricated1024B maximum transaction spool (A512+B16512), metadata extra. Not a hidden extra S port.',
 'K_T_SELF':'Same T reentry reserves complete source batch in S before drain/release/new generation; at most6144B input spool, extra compute workspace separate.',
 'K_S_COPY':'Overlapping S copy uses proven memmove direction or scratch; shared subword writes need RMW/lock or own whole tail word.',
 'K_M_LAYOUT':'M A base and B base4-word aligned; A alloc4/8words per tile; B alloc4/8words per tile; fits actual S banks.',
 'K_ROUTE':'Physical endpoints/selection/MUX/return paths must exist and satisfy frozen-base budgets; no multi-driver time-slot fiction.',
}
GAPS = {
 'G_BIND':'Family/shape/profile/value and exact semantic bindings not yet instantiated.',
 'G_SCHEMA':'Input carrier schema, record field or companion selection must be resolved.',
 'G_LINEAGE':'EXP/score exact lineage or lossless-equivalence proof is missing until bound.',
 'G_WIDE':'Full S64/U64/record-wide numeric conversion path not implemented; M op5 is only a native-result subset.',
 'G_NUMERIC':'Generic numeric/pack/layout support not implemented; native E/M subsets do not close all profiles.',
 'G_SYS':'Generic export/import/storage/topology/control layer has zero new RTL/verification/physical qualification.',
 'G_LOADER':'Loader output selector, exact descriptor spool and dual-output completion support not implemented.',
 'G_T_SELF':'Complete on-chip spool/release/reopen controller not implemented.',
 'G_ARITH':'If the family requires a new coefficient/inject/score computation, it is an explicit producer arithmetic task, not transparent CAST.',
 'G_DIAG':'Diagnostic mathematical use has not been accepted by a family/profile proof.',
 'G_PARAM':'Parameterized native-command builder and data-to-parameter validator not implemented.',
}
NEG = {
 'X_BITCAST':'Reject S64 as fourS32, fourS32 as eightS16, wrong low64 interpretation or record-as-vector.',
 'X_EXP_PROB':'Reject EXP relabeled probability, probability relabeled EXP, changed codes using old factor or group lineage.',
 'X_ID_SCORE':'Reject ID-as-logit without semantic redefinition or required score gather.',
 'X_RECORD':'Reject unspecified field/schema/companion; reserved bits or signedness cannot be guessed.',
 'X_PARAM':'Reject unvalidated cmd-data forwarding, unauthorized structural change, bad field bounds or reserved bits.',
 'X_STALE':'Reject stale version/error payload as a valid new tensor; do not conflate an unready stage with an illegal macro pair.',
 'X_RESOURCE':'Never rewrite absent on-chip capacity/RTL/route as semantic_illegal.',
 'X_REENTER':'Reject direct same-T simultaneous read/FILL, implicit T rewind, M result restore fiction or premature context overwrite.',
}
PARAM = {
 'M.scale':('factor S16,left0..31','op4 index0; zero upper43; compound fields from named sources/ROM'),
 'M.exec_descriptor':('A/B fmt0..1,clear0..1,lastK1..8,N1..8,tiles1..4,rows1..8','op10 bank<<5; reserved bits zero; loaded bank/format/append context'),
 'N.epsilon':('positive U32 raw square units','BEGIN mode1/2 only; no active-group hijack'),
 'N.mode':('enum0..2','BEGIN; finite family branch only'),
 'N.count':('integer1..8','per stage and remaining group count'),
 'N.topk_k':('integer1..8','k<=records_loaded<=40'),
 'E.op':('enum0..13','family-approved operation; 14/15 unsupported'),
 'E.shift':('integer0..31','selected operation units/rounding'),
 'G.fn':('enum0..3','finite approved function; tag changes output units'),
 'G.gated':('boolean','gated requires companion gate'),
 'R.owner':('U32','authorized owner/context, no owner substitution'),
 'R.epoch':('U32','matching context; commit cannot advance0xffffffff; no stale reuse'),
 'R.position':('U32','family token/subversion rule and expected position'),
 'R.length':('integer1..256','OPEN no pending; state storage capacity'),
 'R.mode':('enum0..2','EXEC matching owner/epoch/position and mode prerequisites'),
 'S.address':('integer0..1023 word units','native request; no wide integer truncation/modulo'),
 'S.load_descriptor':('rows1..8,tiles1..4,aligned bases and bank/format/reuse','bounds and resident weight identity; no loader restart while busy'),
 'T.owner':('integer0..3','BEGIN EMPTY; external authorization'),
 'T.generation':('U32','BEGIN EMPTY; generation/epoch reuse prevention'),
 'T.word_count':('integer1..384','BEGIN EMPTY; tail separate; whole batch capacity'),
}

def source_extra(src):
    cls=CLASSES[src]
    return {'record':['C_FIELD'],'typed_carrier':['C_SCHEMA'],'id':['C_ID'],
            'diagnostic':['C_DIAG'],'factor':['C_FACTOR'],'exp':['C_EXP_NUM'],
            'probability':['C_PROB']}.get(cls,[])

def target_mode(dst):
    if dst in ('S.payload','T.payload'): return 'TRANSPORT'
    if dst=='N.soft_replay': return 'EXP_REPLAY'
    if dst=='N.exp_score': return 'SCORE_REPLAY'
    if dst=='N.topk_records': return 'RECORD_JOIN'
    return 'NUMERIC'

def evaluate(semantic,state,mapping,implemented=False):
    """Only a transparent static guard evaluator; no model/RTL/route proof."""
    if any(v is False for v in semantic.values()): return 'REJECT_PROFILE_VARIANT'
    if any(v is None for v in semantic.values()): return 'UNRESOLVED_SEMANTICS'
    if any(v is not True for v in state.values()): return 'WAIT_OR_PROTOCOL_GUARD'
    if any(v is not True for v in mapping.values()): return 'GAP_ONCHIP_MAPPING'
    return 'STATIC_CONTRACT_SATISFIED_NOT_VERIFIED' if implemented else 'LEGAL_CONDITIONS_WITH_IMPLEMENTATION_GAP'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--base',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parent)
    args=parser.parse_args();base=args.base.resolve();out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    path=base/'work/Melodydt/151/all-legal-connection-contract.json'
    old=json.loads(path.read_text(encoding='utf-8'))
    srcs=[f'{m}.{r}' for m in MACROS for r in old['source_roles'][m]]
    dsts=[f'{m}.{r}' for m in MACROS for r in old['destination_roles'][m]]
    params=[f'{m}.{r}' for m in MACROS for r in old['controlled_parameter_roles'][m]]
    assert len(srcs)==23 and len(dsts)==27 and len(params)==20
    assert set(srcs)==set(CLASSES)==set(SRC_DETAILS) and set(params)==set(PARAM)
    source_schema={s:{'class':CLASSES[s],'carrier':SRC_DETAILS[s][0],'F':SRC_DETAILS[s][1],
                      'native_rule':SRC_DETAILS[s][2]} for s in srcs}
    recipes={};data=[];controlled=[]
    def add_recipe(cls,mode,dmacro):
        rid=f'{cls}_{mode}_{dmacro}'
        if rid in recipes:return rid
        profiles=['P01','P14','P15'];sem=['C_FAMILY','C_SHAPE'];steps=['EXPORT_CAPTURE']
        if mode=='TRANSPORT':
            steps+=['PRESERVE_TYPED_SCHEMA','BITPACK_128']
            if cls=='typed_carrier':sem+=['C_SCHEMA']
        else:
            sem+=['C_UNITS','C_DEST_OP','C_COMPANION'];profiles+=['P02','P03','P04']
            if cls=='typed_carrier': sem+=['C_SCHEMA'];profiles+=['P13'];steps+=['RESOLVE_INHERITED_SCHEMA_AND_DISPATCH']
            elif cls=='record':sem+=['C_FIELD'];profiles+=['P05'];steps+=['EXPLICIT_FIELD_SELECT']
            elif cls=='id':sem+=['C_ID'];profiles+=['P06','P13'];steps+=['DECLARE_ID_USE_OR_RESOLVE_ID']
            elif cls=='diagnostic':sem+=['C_DIAG'];steps+=['VERIFY_PARTIAL_MATH_AND_OWNER']
            elif cls=='factor':sem+=['C_FACTOR'];steps+=['BIND_FACTOR_FORMULA']
            elif cls=='exp' and mode!='EXP_REPLAY':sem+=['C_EXP_NUM'];profiles+=['P13']
            elif cls=='probability':sem+=['C_PROB']
            steps+=['EXACT_NUMERIC_RECIPE_IF_REQUIRED','COMPOSE_LAYOUT_ONCE','BITPACK']
        if mode=='EXP_REPLAY':sem+=['C_EXP_LINE'];steps+=['VERIFY_EXACT_EXP_LINEAGE_NOT_SRC_OPCODE'];profiles+=['P13']
        if mode=='SCORE_REPLAY':sem+=['C_SCORE_LINE']
        if mode=='RECORD_JOIN':sem+=['C_RECORD'];profiles+=['P05','P10'];steps+=['JOIN_SCORE_AND_ID_FIELDS']
        if mode=='PARAM':sem+=['C_PARAM','C_INTEGRAL'];profiles+=['P12'];steps+=['SELECT_NAMED_PARAMETER_FIELDS','EXACT_REJECTING_COMMAND_BUILDER']
        state=['S_VALID','S_READY','S_OWNER'];mapping=['K_ONCHIP','K_SLOTS','K_ROUTE']
        if dmacro=='M' and mode!='PARAM':mapping+=['K_M_LAYOUT']
        if dmacro=='N':state+=['S_N_CONTEXT']
        if dmacro=='R':state+=['S_R_CONTEXT']
        if dmacro=='T':state+=['S_T_LIFE'];profiles+=['P08']
        steps+=['REUSE_S_HANDLE_OR_MATERIALIZE_ONCHIP','WAIT_WRITE_ACK','IMPORT_THROUGH_UNIQUE_OWNER']
        if mode=='PARAM':steps+=['VALIDATE_PARAMETER_UPDATE_WINDOW']
        recipes[rid]={'profiles':sorted(set(profiles)),'semantic_guards':sorted(set(sem)),
                      'state_guards':state,'mapping_guards':mapping,'normal_form':steps,
                      'conditional_profiles':{'P10':'Only when this operation/record needs independently supplied companion inputs; unary imports do not require a JOIN.'},
                      'implementation':'NEW_SYSTEM_NOT_IMPLEMENTED','verification':'NOT_EXECUTED'}
        return rid
    for number,(src,dst) in enumerate(itertools.product(srcs,dsts),1):
        cls=CLASSES[src];mode=target_mode(dst);dm=dst.split('.')[0];rid=add_recipe(cls,mode,dm)
        cond=[];gaps=[];extra=[]
        if cls in ('record','typed_carrier'):gaps+=['G_SCHEMA']
        if cls=='diagnostic' and mode!='TRANSPORT':gaps+=['G_DIAG']
        if mode in ('EXP_REPLAY','SCORE_REPLAY'):gaps+=['G_LINEAGE']
        if mode not in ('TRANSPORT',):gaps+=['G_NUMERIC']
        if src in ('M.result64','M.partial_diag','N.stats','R.meta') and mode!='TRANSPORT':gaps+=['G_WIDE']
        if dst in ('R.decay','R.beta','R.element_decay'):cond+=['C_COEFF'];gaps+=['G_ARITH']
        if dst=='R.inject':cond+=['C_INJECT'];gaps+=['G_ARITH']
        if dst=='E.C_vec':cond+=['C_E_C']
        if dst in ('M.A','M.B_nmajor'):cond+=['C_M_FMT']
        if dst=='N.norm_gamma':cond+=['C_N_GAMMA']
        if src=='S.write_echo':cond+=['C_ACK']
        if src in ('S.loader_A','S.loader_B'):extra+=['K_LOADER','S_LOADER'];gaps+=['G_LOADER']
        if src.split('.')[0]==dm:
            extra+=['S_REENTER']
            if dm=='S':extra+=['K_S_COPY']
            if dm=='T':extra+=['K_T_SELF'];gaps+=['G_T_SELF']
        # Conditional slots are never accepted edges without value/profile bindings.
        status='schema_or_semantic_binding_unresolved' if cls in ('record','typed_carrier','id','diagnostic','factor') else 'conditional_uninstantiated'
        data.append({'id':f'D{number:04d}','src':src,'dst':dst,'status':status,'recipe_id':rid,
                     'condition_ids':cond,'extra_guard_ids':extra,'gap_ids':sorted(set(gaps))})
    for number,(src,dst) in enumerate(itertools.product(srcs,params),1):
        cls=CLASSES[src];dm=dst.split('.')[0];rid=add_recipe(cls,'PARAM',dm)
        controlled.append({'id':f'P{number:04d}','src':src,'dst':dst,'status':'controlled_binding_unresolved',
                           'recipe_id':rid,'condition_ids':['C_PARAM','C_INTEGRAL'],
                           'extra_guard_ids':(['K_LOADER','S_LOADER'] if cls=='loader' else []),
                           'gap_ids':['G_PARAM']+(['G_SCHEMA'] if cls in ('record','typed_carrier') else [])+
                           (['G_LOADER'] if cls=='loader' else [])+
                           (['G_WIDE'] if src in ('M.result64','M.partial_diag','N.stats','R.meta') else [])})
    evidence=[]
    for relative in ['work/Melodydt/151/all-legal-connection-contract.json','docs/LEGAL_CONNECTION_PROFILES.md',
                     'docs/ALL_LEGAL_CONNECTION_SPEC.md','docs/rtl-contracts/MST_NATIVE.md',
                     'docs/rtl-contracts/NEG_NATIVE.md','docs/rtl-contracts/R_NATIVE.md']:
        b=(base/relative).read_bytes();evidence.append({'path':relative,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)})
    tests=[]
    def case(cid,description,semantic,state,mapping,expected,slots):
        slot=next(x for x in data+controlled if x['id']==slots[0])
        recipe=recipes[slot['recipe_id']]
        guards=recipe['semantic_guards']+slot['condition_ids']
        states=recipe['state_guards']+[x for x in slot['extra_guard_ids'] if x in STATE]
        maps=recipe['mapping_guards']+[x for x in slot['extra_guard_ids'] if x in MAP]
        # Each witness binds ALL actual recipe guards before overriding a counterexample.
        sem_values=dict.fromkeys(guards,True);state_values=dict.fromkeys(states,True);map_values=dict.fromkeys(maps,True)
        aliases={'schema_and_role':'C_FAMILY','carrier_interpretation':'C_UNITS','score_companion':'C_RECORD',
                 'exact_equivalence':'C_EXP_LINE','authorized_update':'C_PARAM',
                 'capture':'S_VALID','source_valid':'S_VALID','N_phase':'S_N_CONTEXT',
                 'ack_captured':'S_VALID','released_before_begin':'S_REENTER','owner':'S_OWNER',
                 'capacity':'K_SLOTS','onchip_capacity':'K_SLOTS'}
        for changes,values in [(semantic,sem_values),(state,state_values),(mapping,map_values)]:
            for key,value in changes.items():
                key=aliases.get(key,key);assert key in values,(cid,key,slot)
                values[key]=value
        got=evaluate(sem_values,state_values,map_values)
        assert got==expected,(cid,got,expected)
        tests.append({'id':cid,'description':description,'slot_ids':slots,'semantic':sem_values,'state':state_values,
                      'mapping':map_values,'expected':expected,'actual':got,'kind':'STATIC_RECIPE_GUARDS_ONLY'})
    def sid(src,dst):return next(x['id'] for x in data if x['src']==src and x['dst']==dst)
    good='LEGAL_CONDITIONS_WITH_IMPLEMENTATION_GAP';bad='REJECT_PROFILE_VARIANT'
    # Full Cartesian index is tested; selected adversarial cases check rule distinctions.
    for s in srcs:
        case('STORE_'+s,'Typed original payload can be preserved in S under guards; RTL absent.',{'schema_and_role':True},{'capture':True},{'onchip_capacity':True},good,[sid(s,'S.payload')])
    examples=[
      ('M64_CAST','M2^40 F40 toS16 Q10 requires exact right30; not E13 reinterpret.',{'C_UNITS':True},{'source_valid':True},{'capacity':True},good,'M.result64','G.x'),
      ('M64_BITCAST','TwoS64 cannot be fourS32.',{'carrier_interpretation':False},{},{},bad,'M.result64','E.A_cast13'),
      ('ID_INT','Explicit ID_AS_INT arithmetic feature.',{'C_ID':True,'C_FAMILY':True},{},{},good,'N.topk_ids','M.A'),
      ('ID_SCORE_RAW','IDs cannot be relabeled logits.',{'C_ID':False},{},{},bad,'N.topk_ids','N.stats_data'),
      ('TOPK_ID_JOIN','ID contribution requires separate score companion.',{'C_RECORD':True,'score_companion':True},{},{},good,'N.topk_ids','N.topk_records'),
      ('TOPK_ID_NO_SCORE','ID alone does not complete score/ID record.',{'C_RECORD':False},{},{},bad,'N.topk_ids','N.topk_records'),
      ('EXP_NUM','EXP can be a declared unnormalized numeric weight.',{'C_EXP_NUM':True,'C_UNITS':True},{},{},good,'N.exp','M.A'),
      ('EXP_PROB_RENAME','EXP is not already probability.',{'C_EXP_NUM':False},{},{},bad,'N.exp','M.A'),
      ('EXP_COPY_REPLAY','Lossless S copy retains exact N EXP group/code lineage.',{'C_SCHEMA':True,'C_EXP_LINE':True},{'N_phase':True},{},good,'S.stored_word','N.soft_replay'),
      ('EXP_OTHER_SRC','A proven lossless copy through another source retains lineage; producer opcode alone is no blacklist.',{'C_EXP_LINE':True,'exact_equivalence':True},{'N_phase':True},{},good,'E.vector','N.soft_replay'),
      ('EXP_CHANGED','Changing EXP values cannot reuse old factor.',{'C_EXP_LINE':False},{},{},bad,'S.stored_word','N.soft_replay'),
      ('SCORE_WRONG','EXP_X must replay original STATS scores.',{'C_SCORE_LINE':False},{},{},bad,'M.read32','N.exp_score'),
      ('STATS_FIELD','Explicit sumsq U48 extraction and units2Fin.',{'C_FIELD':True,'C_UNITS':True},{},{},good,'N.stats','E.A_cast13'),
      ('STATS_VECTOR','Mixed stats record is not eightS16.',{'C_FIELD':False},{},{},bad,'N.stats','E.A_vec'),
      ('ACK_FORWARD','Capture known write echo, take ACK, then reuse S.',{'C_ACK':True,'C_SCHEMA':True},{'ack_captured':True},{},good,'S.write_echo','S.payload'),
      ('ACK_UNKNOWN','Unknown ACK cannot create tensor schema.',{'C_SCHEMA':False},{},{},bad,'S.write_echo','G.x'),
      ('LOADER_SPOOL','Both loader outputs drained into reserved1024B on-chip spool.',{'C_SHAPE':True},{'S_LOADER':True},{'K_LOADER':True},good,'S.loader_B','S.payload'),
      ('LOADER_NOSPOOL','No spool with serial S is mapping gap, not semantic illegal.',{'C_SHAPE':True},{'S_LOADER':True},{'K_LOADER':False},'GAP_ONCHIP_MAPPING','S.loader_B','S.payload'),
      ('T_SELF','Whole input batch ACKed in S then release/newBEGIN.',{'C_SCHEMA':True},{'released_before_begin':True},{'K_T_SELF':True},good,'T.committed_word','T.payload'),
      ('T_SELF_FIFO','Two slots cannot hold arbitrary source batch.',{'C_SCHEMA':True},{},{'K_T_SELF':False},'GAP_ONCHIP_MAPPING','T.committed_word','T.payload'),
      ('R_PENDING','Legal state transfer must wait for proper pending window.',{'C_UNITS':True},{'S_R_CONTEXT':False},{},'WAIT_OR_PROTOCOL_GUARD','R.output','R.state'),
      ('S_FULL','No external memory; capacity failure is mapping gap.',{'C_UNITS':True},{},{'onchip_capacity':False},'GAP_ONCHIP_MAPPING','M.read32','N.stats_data'),
      ('UNKNOWN_SCHEMA','Unresolved S schema is not inferred from128bits.',{'C_SCHEMA':None},{},{},'UNRESOLVED_SEMANTICS','S.stored_word','M.A'),
      ('G_UNUSED_GATE','Ungated G does not consume a mathematical gate edge.',{'C_DEST_OP':False},{},{},bad,'E.vector','G.gate'),
      ('R_COEFF_JOIN','A decay contribution needs beta companion/constant for native op5 index0.',{'C_COMPANION':False},{},{},bad,'N.factor','R.decay'),
      ('E_UNARY_C','Unused C field of a unary E op is not a consumed mathematical input.',{'C_DEST_OP':False},{},{},bad,'M.read32','E.C_vec'),
    ]
    for x in examples:case(*x[:6],[sid(x[6],x[7])])
    case('PARAM_VALID','Named scalar bound through unique validated owner.',{'C_PARAM':True,'C_INTEGRAL':True},{'owner':True},{},good,['P0001'])
    case('PARAM_BAD','Raw command forwarding or out-of-range opcode rejected.',{'C_PARAM':False},{},{},bad,['P0001'])
    case('PARAM_CONST','Data may not change a product-locked structural parameter.',{'authorized_update':False},{},{},bad,['P0001'])
    assert len(data)==621 and len(controlled)==460 and len({(x['src'],x['dst']) for x in data})==621
    pair_counts=collections.Counter(x['src'].split('.')[0]+'->'+x['dst'].split('.')[0] for x in data)
    assert len(pair_counts)==49
    counts=collections.Counter(x['status'] for x in data)
    result={
      'schema_version':1,'baseline_revision':'39bd7bf','source_RTL':'643c6012 frozen imported bytes',
      'artifact_kind':'ROLE_SLOT_AND_RECIPE_DRAFT_NOT_HARDWARE_COVERAGE',
      'scope':{'sample_models':8,'family_catalog_frozen':False,'external_memory_allowed':False,
               'onchip_only':True,'unknown_shapes_are_conservative_mapping_questions_not_semantic_blacklists':True},
      'enumeration':{'data_sources':23,'data_destinations':27,'data_cartesian_slots':621,
                     'controlled_destinations':20,'controlled_cartesian_slots':460,'macro_pairs':49,
                     'all_cartesian_slots_are_legal':False,'profile_parameter_space_exhaustively_instantiated':False,
                     'proven_legal_edges':0,'new_system_RTL_implemented':0,'new_system_verified':0,'physical_qualified':0},
      'defaults':{'semantic_decision':'requires concrete family/profile/value/lineage binding',
                  'all_slots_have_gap_ids':['G_BIND','G_SYS'],'implementation':'NOT_IMPLEMENTED',
                  'verified':False,'physical_qualified':False,'external_route_fallback':False},
      'source_schema':source_schema,'record_field_schema':FIELDS,
      'special_source_export_recipes':{
         'S.write_echo':['CAPTURE_ECHO_WITH_WRITE_SCHEMA','TAKE_ACK','RELEASE_S_RESPONSE_SLOT','FORWARD_SNAPSHOT'],
         'S.loader_A':['RESERVE_SEPARATE_ONCHIP_SPOOL_MAX1024B','CONFIGURE_EXPLICIT_OUTPUT_SINKS','DRAIN_ALL_A_AND_B','TAKE_DONE','ISSUE_NORMAL_S_WRITES'],
         'S.loader_B':['RESERVE_SEPARATE_ONCHIP_SPOOL_MAX1024B','SPLIT_B512_WITH_HALF_AND_NMAJOR_METADATA','DRAIN_ALL_A_AND_B','TAKE_DONE','ISSUE_NORMAL_S_WRITES'],
         'T.committed_word':['RESERVE_S_SOURCE_BATCH_SPOOL_MAX6144B_WHEN_REQUIRED','READ_INDEX_ORDER','WAIT_ALL_S_WRITE_ACKS','LAST_TAKE_THEN_RELEASE','KEEP_TYPED_SNAPSHOT_FOR_TARGET'],
         'M.result64':['READ3_FULL_S64_WITH_ROW_CONTEXT','DO_NOT_TRUNCATE_TO_S32','USE_NUM_CONVERT_OR_PROVEN_NATIVE_READ5_SUBSET'],
      },
      'destination_schema':{f'{m}.{r}':{'expected':t,'subformats':(['S8','S16'] if m=='M' else []),
                                      'native_import_owner':m+'_CTRL'} for m in MACROS for r,t in old['destination_roles'][m].items()},
      'controlled_schema':{p:{'domain':PARAM[p][0],'native_rule':PARAM[p][1],
                              'parameter_fields_from_source_or_ROM_must_be_named':True} for p in params},
      'compound_destination_assembly':{
         'N.norm_replay':'op5 data=x plus same-group aux=gamma; independent companion/constant required.',
         'N.norm_gamma':'op5 aux=gamma plus same-group data=x; independent companion required.',
         'N.topk_records':'op9 each32bits is(score S16,ID U16); this edge may contribute one named field, not the complete record.',
         'R.decay':'op5 index0 low32 decay plus bits63:32 beta; upper64zero. Beta companion/constant required.',
         'R.beta':'op5 index0 bits63:32 beta plus low32 decay; upper64zero. Decay companion/constant required.',
         'E.A_vec':'Opcode declares A/B/C operand schema. Extra inputs only for operations consuming them.',
         'E.B_vec':'A and op-dependent C companion; opcode must actually use B.',
         'E.C_vec':'A/B or predicate-source companions as declared by opcode; do not invent C usage for unary op.',
         'G.gate':'gated=1 plus activation x. gated=0 has no mathematical gate edge.',
         'G.x':'gate companion/constant when gated=1; ungated function is unary.',
         'M.A':'A contribution can load before B but EXEC waits complete descriptor, B/tile validity and matching scale.',
         'M.B_nmajor':'B contribution can load before A but EXEC waits complete descriptor and A rows/tiles.'},
      'semantic_conditions':COND,'state_guards':STATE,'mapping_guards':MAP,'gaps':GAPS,'rejected_variants':NEG,
      'applicability':{
         'G_WIDE':'Only if resolved fields/values actually require full wide conversion; a selected small field may use a proved native subset.',
         'G_ARITH':'Conditional producer dependency only. If the source already has the correct coefficient/inject meaning, no new arithmetic is implied.',
         'S_REENTER':'Only same physical instance with a new independent context; legal same-context RESUME does not require closing that context.',
         'K_T_SELF':'Only when source and destination are the same physical T. Distinct T instances have separate lease rules.',
         'K_S_COPY':'Only for actual S copy/overwrite; immutable same-range alias can use reference ownership without copying.',
         'record_field_selection':'Slot recipes select finite declared fields; they do not enumerate every field/scale/shape instance yet.',
         'native_identity_or_subset':'CAST/BITPACK operations may reduce to identity or a proved E/M subset; gaps refer to the generic system path, not denial of native primitives.'},
      'recipes':recipes,'data_slots':data,'controlled_parameter_slots':controlled,
      'topology_requirements':{
        'FORK':'Materialize once, per-consumer references/pending masks; no shared take OR.',
        'JOIN':'Independent finite input slots and same task/epoch/range/type; companion fields required.',
        'RESUME':'N EXP->SOFT replay and R history-only pending may preserve same context; no forced new BEGIN/OPEN.',
        'REENTER':'Next independent context only after saved outputs and legal context close/commit/revoke.',
        'T_SPOOL':'Same T input batch fully spooled in S; last write ACK then release, newgeneration BEGIN; no native rewind.',
        'S_COPY':'Memmove direction/scratch and ACK capture before same-port reentry.',
        'LOADER_SPOOL':'Separate on-chip1024B descriptor spool; both A/B obligations completed before ordinary-S write phase.',
        'bounded_feedback':'Explicit initial token/version/delay; semantic adjacency self-loop is not combinational ready loop.'},
      'static_cases':tests,'summary':{'data_status_counts':dict(counts),'macro_pair_slot_counts':dict(pair_counts),
                                    'recipe_definitions':len(recipes),'static_guard_cases':len(tests),'static_guard_cases_passed':len(tests)},
      'provenance':evidence,
      'limits':['621+460 is a slot Cartesian index, not1081 accepted connections.',
                'Field choices, M subformats, scales/shapes, op-specific roles, lineage proofs and companions are not yet fully instantiated.',
                'Eight FP32 sample graphs do not establish complete integer family/shape/quality coverage.',
                'No external memory; new on-chip buffers are costed requirements, not current RTL facts.',
                'Static guard cases test classification rules only; no RTL, liveness, numeric-model or physical verification.']}
    # Keep full slots readable one per line and avoid repeating long recipe text1081 times.
    text=json.dumps(result,ensure_ascii=False,indent=2)
    for key in ('data_slots','controlled_parameter_slots'):
        block='[\n'+',\n'.join('    '+json.dumps(v,ensure_ascii=False,separators=(',',':')) for v in result[key])+'\n  ]'
        text=text.replace(json.dumps(result[key],ensure_ascii=False,indent=2).replace('\n','\n  '),block)
    # A controlled writer guarantees valid JSON even if pretty-block replacement did not match.
    assert json.loads(text)==result
    (out/'edge-ledger.json').write_bytes((text+'\n').encode('utf-8'))
    report=f'''# 角色枚举槽与规范配方覆盖草案（步骤2）

基线39bd7bf；七宏继承643c6012固定RTL。用户范围：现有八样本作研究输入、未知规模保守估计、暂不考虑外存。此稿只建立角色账本和静态规则，不修改RTL/任务/远端。

实际枚举 **23源×27数据目的=621数据槽**，以及 **23源×20受控参数目的=460参数槽**；49个宏类别有向对均有下钻。M的A/B各保留S8/S16子格式，N Norm原值/gamma分开，R decay/beta分开。完整列名继承all-legal-connection-contract.json；输入6份文件的实际字节SHA在JSON provenance。

这1081槽不是1081条已证明合法边。当前已证明合法实例0、新系统RTL0、组合验证0、物理资格0。数据槽状态为：{dict(counts)}。需要具体FamilySpec、角色意义、字段、Fin/Fout、shape/布局、lineage、状态和容量后才能接受实例；缺RTL始终保留implementation gap。

## 1. 如何读账本

`data_slots`每行只索引source/destination、共享recipe_id、额外condition/guard/gap；长规则集中在recipes和各规则表。默认每槽还有G_BIND/G_SYS。`applicability`明确条件适用范围：G_WIDE只针对真正需要宽转换的已选字段；G_ARITH只在源尚未提供正确算法数量时成立；同实例REENTER/Tspool不强加给不同实例或同context RESUME。参数槽独立走PARAM_BIND，不允许把payload裸接成完整命令。profile与字段尚未绑定的槽为未决，不自动全绿。

语义guard失败表示拒绝**该profile实例/裸接方式**，不是永久禁止宏对。未就绪/pending违反状态guard时是等待或原生协议错误；容量/线路/缓冲不足是mapping gap；实现缺失是implementation gap。无外存不改变语义判定，也不偷偷回退DRAM。

## 2. 必要分支

| 源/目的特例 | 规范配方及限制 |
|---|---|
| 普通numeric→numeric | 导出→精确NUM_CAST→合成布局→BITPACK→有界片上中转→目标owner导入；零变换允许identity，不能为凑配方无限cast |
| M.RESULT64/partial、U48字段 | 保留完整宽度；通用S64/U64转换为gap。M.op5只覆盖本M结果的受限出口，不能给其他宽源当通用算术器 |
| N.EXP/PROB | EXP可明确作为未归一化数值参与算术，但不自动变概率；SOFT_REPLAY必须是该factor所绑定的确切EXP codes |
| EXP经S/T或其他无损路径 | 继承schema/context和精确码等价证明即可回放；不以生产者opcode是否N.EXP作永久黑名单。数值改变则不得沿用旧lineage/factor |
| ID→数值/score | ID_AS_INT F0是显式新语义；MoE score须ID_RESOLVE/gather。TopK record需score/ID JOIN，单个ID输入不能完成整记录 |
| STATS/META | 字段schema按位提取；count/owner/epoch等F0，max/min/sum沿input_F，sumsq用2Fin；保留位不是数据 |
| S/T opaque | 必须继承已知写入/初始化/租约schema再递归分派，不能从128bit宽度猜类型 |
| S ACK-forward | 保存同版本write echo、take ACK后才重入同S端口；不是任意ACK都产生新张量 |
| S loader额外输出 | 串行S基线采用独立预制1024B最大描述符spool，完成全部A/B义务再普通S写；不是暗增S端口 |
| 同T→T | 全批最多6144B先暂存S并等ACK→末读→release→新generation BEGIN回装；计算workspace另计，两个弹性槽不能替代 |
| 参数输入 | 字段提取/必要数值转换→值域/保留位/授权窗口检查→唯一owner构造命令；无验证opcode、地址、ID截断/取模非法 |

R inject/decay等若尚需算法计算，recipe显式依赖单独算术生产任务；CAST不生成缺失的系数/注入。N.gamma与E.C也检查目标操作的数学单位。

## 3. 容量和拓扑

运输只允许现有S16KiB/T6KiB与显式预算的新片上支持存储；不包含外存。S不足、loader1024B新增spool不存在、Tspool与其他live张量冲突都报mapping gap。S中的T输入spool、其他中间量和新增寄存spool必须分别计价，不可重复使用同一个活跃区域。

fork保存每消费者引用/接收状态；join独立保持各输入。N/R需要RESUME的同context阶段不强迫先关组/提交再开始；下一独立context才REENTER。T/R提交不形成跨宏原子；反馈需要明确初值、版本和存储延迟，不能把所有图环一律当非法，也不能由静态DAG宣称无死锁。

## 4. 已做与未做

生成器实际校验621/460唯一键、49宏对、23/27/20目录匹配和{len(tests)}项正/负/条件静态guard案例；案例涵盖宽bitcast、ID语义、EXP lineage、字段提取、ACK-forward、loader spool、T重入、R pending及片上不足。规则正例仍返回implementation gap，而不是硬件通过。

复现：`python -X utf8 <本报告同目录>/generate_edge_ledger.py --base <steps123-39bd7bf/integrated> --output-dir <独立输出目录>`；实际脚本位置在本报告同目录。默认仅在脚本同目录输出两个文件。

未决：完整八模型边实例的映射（由根整合）、有限家族/shape/尺度域、字段与companion全部实例、操作/布局参数域穷举、片上预算、宽数值oracle与误差接受、RTL/活性/物理验证。没有把有限参数空间都实例化；报告不使用“1081条均合法/全通”表述。
'''
    (out/'edge-report.md').write_bytes(report.encode('utf-8'))
    print(json.dumps({'data_slots':len(data),'parameter_slots':len(controlled),'recipes':len(recipes),
                      'cases':len(tests),'ledger_bytes':(out/'edge-ledger.json').stat().st_size},ensure_ascii=False))

if __name__=='__main__':main()
