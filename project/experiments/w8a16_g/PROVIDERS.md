# G service coverage before physical freeze

Refs #250. Main source `c4d7b960599b9d292f27eb4429d5f226a7156c95`: `project/rtl/block_v2/block_v2_g.sv`, `project/experiments/block_v2/test_g.cpp`, `docs/BLOCK_V2.md:58–60`. The old compact G is not SiLU-only.

| Old operation | Old input/output profile | New `g_s32` | Required binding decision |
| --- | --- | --- | --- |
| `in_fn=0` SiLU, optionally gated | Two S16 Q5.10 inputs; Q5.10 result; optional RNE10 gate multiply; S16 saturation and flag | Two S32/Q16 lanes, 257-point [-16,+16] table, optional RNE16 gate multiply; atomic overflow error | Same mathematical operation, different numerical contract, ports and error semantics. New P provider and descriptor profile required |
| `in_fn=1` Sigmoid, optionally gated | Q5.10 input, Q1.14 activation; gate Q5.10; RNE14 gate multiply; S16 saturation | Unsupported | Preserve native G16 provider; S32 callers need an explicit tested conversion/format rule, or a separately implemented S32 service |
| `in_fn=2` GELU_tanh, optionally gated | S16 Q5.10 result and gate multiply RNE10 | Unsupported | Same explicit provider/format requirement; relevant to Gemma3 |
| `in_fn=3` Softplus, optionally gated | S16 Q5.10 result and gate multiply RNE10 | Unsupported | Same explicit provider/format requirement; relevant to Qwen3.5 GDN and Falcon-H1 |

Main P's `pu_p_group.sv` fixes its G call to `in_fn=0,in_gated=1`. Main C/F's `block_cfj_cf.sv:128–130` exposes `meta[2:0]` as `in_fn` and `meta[3]` as gated mode, so all four native G services remain part of that interface. U and J do not gain G operations from this change.

The current physical candidate is explicitly **P's new `G32_SILU` provider**. The chosen first arrangement keeps `G16_MULTI` in C/F and selects `G32_SILU` in P; each Block type has one fixed implementation. These names must remain different catalog types. Existing production `block_v2_g` and its tables are untouched. P's old S16 service is an explicit interface/version change; the new provider does not provide that old S16 bit contract. C/F's legacy G16 functionality is retained, while their S32 Sigmoid/Softplus/GELU services remain unsupported. A five-Block resource manifest must name each macro's actual provider/profile and must not replace one merely because both are called G. This arrangement does not give arbitrary S32 GDN/GELU requests a legal mapping. Unregistered format conversions or unsupported functions must reject compilation, and each registered conversion has its own numeric, latency, area and endpoint evidence. In particular, there is no automatic S32-to-S16 narrowing. This is not complete new-profile coverage of Qwen3.5, Falcon-H1 or Gemma3.

Unifying all four operations into one new S32 G implementation is another hardware task: it needs defined coefficients, range/error bounds, tables, interface opcodes, numerical tests and actual area/ports. The 1,028-byte SiLU table does not represent four functions. No long physical acceptance may silently remove old functionality or declare this missing S32 coverage complete.
