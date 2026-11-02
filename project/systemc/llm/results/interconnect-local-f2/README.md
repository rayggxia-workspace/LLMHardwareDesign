# Local finite-bridge evidence (f2)

Four synthetic two-layer structures, three modes each (off/flow/link).
Every complete hidden/logits binary matches the earlier r35 synthetic baseline.
These are not extra pretrained checkpoints. Local GCC10.3/SystemC3.0.1 build
uses -Werror and UBSan; raw LastTest.log records all 12 CTest passes, including
three-sender contention, exact corruption rejection and dropped-response watchdog.
Flow audit controls reject bad slices, dependencies and missing macro transactions.

index.json binds source archive members, actual local binaries, test/helper,
inputs, outputs, baseline and raw logs. Large/complete binary and event files
remain at the indexed local paths. Only code/CMake LF-normalized equality to the
executed f2 archive is asserted; later documentation/audit/runner additions are
separately recorded. The remote real-model evidence is a distinct collection.
