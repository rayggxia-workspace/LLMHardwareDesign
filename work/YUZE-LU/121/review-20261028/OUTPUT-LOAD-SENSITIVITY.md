# M/T output-load sensitivity

This experiment uses the accepted revised native M/T final ODB, approved SDC and SPEF unchanged. Six independent16CPU tasks share one96CPU allocation with immediate refill: M/T each approved50fF, actual P2 base wire C plus2fF receiver, and high wire C plus2fF receiver. No new RTL or layout variant is introduced.

Every actual output has the same exit length within its macro; the implementation refuses unequal loads rather than averaging. It replaces50fF only in a fresh read-only STA process, verifies complete output-load/input-driver/I/O-delay/clock readback, preserves full native endpoint/electrical/annotation checks and proves original final-file hashes unchanged. Approved-load baseline must pass independently. A completed sensitivity experiment can contain negative loaded slack; experiment passed and loaded STA passed are distinct fields.

This is only lumped output-C sensitivity using uncalibrated early RC. Series resistance, inputs, clock escape, coupling, remote drivers and combined interface timing remain unqualified. No relaxation or qualification transfer from this experiment is allowed.

Source and job identities will be recorded in stage265-manifest.json/node-queue-265.json; actual output evidence remains pending until receipt capture. Issue121 stays in_progress and PR122 stays draft.
