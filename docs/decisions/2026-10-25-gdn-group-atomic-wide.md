# GDN grouped publication and exact wide lowering

Issue104 extends the R circuit evidence to Qwen3.5 delta-rule math. Falcon99 cannot represent prediction/residual/correction and coupled twohead retry. Fix the numerical boundary at complete K128 reductions, I64 intermediates, asymmetric S32 storage and a complete twohead transaction.

A single signed32 multiplier performs radix2^31 exact wide products, checking each term and addition before one final RNE. Keep group-private trial/proposal/shadow externally with finite capacity; stage64B immutable metadata and atomically publish one128bit root only after consumer acceptance and all prior ACKs. Position/version are independent. Two banks require DONEACK release and no external concurrent readers whilebusy.

Reason: actual native32/portable12 need33bit correction, full-domain synthetic34bit checks and real range retry; narrow32 forwarding or independent head publication changes the accepted recurrence. Single16KiB scratch cannot hold full32K-cell state/proposal; Vpair2 pays physical packing, repeated reads and external materialization. 32 coefficient slots cap the1MiB window; original256 is not silently admitted.

Evidence: [Issue104 report](../experiments/issue-104-gdn-state.md), independent complete numerical/actual gate receipts. Outcome fixes semantics and demonstrates a bounded circuit, not optimal throughput, shared106 inventory or a physical macro boundary. Integrate service mux/lease/generation later under one explicit resource bank and requalify actual netlist.
