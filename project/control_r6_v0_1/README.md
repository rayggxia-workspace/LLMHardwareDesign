# R6 control program generation

Issue179 and PR180 track this work. The first target is the verified R4 RAW16/P
transfer path. The target registry pins the native ABI, topology, image capacity
profile, S size and finite credits. The runnable graph uses the two existing
routes `host → LC0` and `LC0 → LC1`, with one 16-byte S object on each block.

The JSON task IR declares image IDs, buffers and their addresses, routes and
credits, the receiver READY event, and completion groups. The compiler
schedule the consumer before the producer, consume the ingress store ACK before
forwarding, and wait for both task completions. Ordered completion groups
select a joint wait or separate waits. Buffer and transfer declaration order
has no scheduling meaning.

```bash
python3 -B project/control_r6_v0_1/task_ir.py project/control_r6_v0_1/examples/split_wait.json
python3 -B project/control_r6_v0_1/compile_ir.py project/control_r6_v0_1/examples/split_wait.json --output split_wait.bundle.json
```

Pass `--instruction-version 2` to emit 64-bit instructions. The reference
verifier accepts either image version and checks the same graph and identities.
The output contains the reference loader manifest and the three exact
little-endian binary images under `images_hex`. It records SHA-256 for the IR,
target registry, manifest and each image. The generated examples include a
joint wait and two successive waits with distinct credit masks.

The currently admitted target has one resident task per local controller and
one in-flight service per block. The R5 candidate profiles remain separate
software research targets. See the maintained two-level control plan for
stage results and evidence.
