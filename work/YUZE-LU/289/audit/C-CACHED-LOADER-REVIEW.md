# Cached loader independent cycle-equivalence argument

Reviewed RTL candidate SHA256: a0f71497ee0c873649c41d64122e2a906775caaed90dc615a686be053625d0f9.
Reference onehot v2 SHA256: 020538508ff7db6461afab28f73726867e5900fde2255a4a311789b105040567.

This is a two-state, reset-initialized compositional proof. It is not a whole-module SAT result or backend acceptance.

## Exact source binding

`review_cached_loader.py` independently enumerates the five substitutions, reverses them, and asserts complete source equality to the already reviewed onehot v2. The only new state is eight 64-bit cached addresses. The original functions, outputs, original state assignments, conditions, and assignment ordering are unchanged. Cache writes occur only at reset and at the original allocation event.

## Inductive validity invariant

Let C be the 252-bit tuple `(f,cols,aa,bb,ast,bst,cst,a_words)`. These are all captured state variables read by addr, including its transitive calls to flat/row_of/col_of. Thus addr is a pure total finite-bit function F(C,word,lane). Let K[p] be a proof-only key recording `(C,allocated_words)` on allocation of slot p.

The invariant is:

1. `pv[p] -> active`.
2. `pv[p] -> K[p] == (C,pi[p])`.
3. For a slot made valid by allocation, `cached_addr[4*p+l] = F(K[p],l)`.

The first two properties have a direct SAT induction proof in `cache-key-induction.sv`, job119717: both reset base and arbitrary one-step preservation pass. Allocation request, acknowledgement clearing, and termination request are over-approximated by arbitrary inputs, while actual active gating, free-slot selection, ready/start rule, and assignment order are retained. This includes allocation and acknowledgement on the same edge.

The third property follows from the exact write expressions: on allocation, pi receives allocated_words, K receives the old configuration plus allocated_words, and all four cached addresses receive addr(allocated_words,l) on that same edge. Otherwise K and cache hold. Reset clears pv, so no initial cache equality is required while a slot is invalid.

Configuration changes only at reset or `start && ready`; reset clears pv, while ready requires old active=0, hence old pv=0 by invariant1. Allocation requires old active=1, so allocation and accepted start cannot coincide. On a valid retained slot, pi and C remain unchanged. Cancel does not change pi or C. Acknowledgement may clear validity; termination clears both active and pv. Report affects ready but does not mutate an active slot's key. These facts establish `pv[p] -> cached_addr[4*p+l] == addr(pi[p],l)` for every lane and every cycle after reset.

## Why every original cycle is preserved

The onehot evaluator computes some lane intermediates even for invalid slots, but only examined lanes can become winners or fallback lanes; examination requires pv. The previously proven 77-bit selector equivalence includes all-zero examination and last-examined fallback. Thus replacing invalid lane addresses cannot affect any selected output. For valid lanes the cached address equals the old address exactly.

Both response-deposit substitutions are guarded by `pv[p]`; their comparison, selected response word, and state updates therefore remain equal. Every original sequential assignment sees identical guards and data in both designs, and every external output is unchanged. Inductively, all original state and all external outputs remain equal on each cycle; the 512 new bits are auxiliary storage and introduce no visible latency.

The use of an auxiliary key is a mathematical abstraction, not added RTL or a timing assumption. No constraint on first, strides, columns, addresses, cancellation, responses, or acknowledgements was introduced to make the proof pass. Four-state X propagation before reset is outside this proof.

Independent peer review: endpoint_audit inspected the actual candidate, inverse binding script, full address dependency tuple, all three use sites, and the induction model. It found the reset-initialized two-state cycle-preservation argument sound. This peer review does not include RTL-to-mapped or backend qualification.
