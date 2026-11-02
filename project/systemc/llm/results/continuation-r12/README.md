# Complete text-model execution receipts (r12)

Real original checkpoint parameters, complete decoder layers and full vocabulary.
Reference arithmetic is separate from the SystemC simulator. Each validation compares
the actual SystemC prefix; Top1 matches do not imply general accuracy acceptance.
All divergences, including Phi first-step failure, remain in the raw validation files.

`remote-audit.json` binds weights, references, outputs, executable and source archive.
`index.json` checks collected raw receipts against that allocated-node audit and
records source archive member hashes. Logs stay on the server; directly collected hashes are indexed. Original large checkpoint and binary
activation files stay on the authorized task server, at the paths in the audit.
This is untimed functional evidence, not hardware throughput or RTL equivalence.
