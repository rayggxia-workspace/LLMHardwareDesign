# R6 control program generation

Issue179 and PR180 track this work. The first target is the verified R4 RAW16/P
transfer path. The target registry pins the native ABI, topology, image capacity
profile, S size and finite credits. The runnable graph uses the two existing
routes `host → LC0` and `LC0 → LC1`, with one 16-byte S object on each block.

The JSON task IR declares image IDs, buffers and their addresses, routes and
credits, the receiver READY event, and completion groups. The compiler will
schedule the consumer before the producer, consume the ingress store ACK before
forwarding, and wait for both task completions. Ordered completion groups
select a joint wait or separate waits. Buffer and transfer declaration order
has no scheduling meaning.

```bash
python3 -B project/control_r6_v0_1/task_ir.py project/control_r6_v0_1/examples/split_wait.json
```

The currently admitted target has one resident task per local controller and
one in-flight service per block. The R5 candidate profiles remain separate
software research targets. See the maintained two-level control plan for
stage results and evidence.
