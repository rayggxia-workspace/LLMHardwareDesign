# Actual seven-job R repair queue

Refs #121; PR #122.

94503 actual RUNNING on node13;387 immutable source Git/archive/remote files and exact run/queue/argv verified. Seven real finite jobs, six16CPU slots. Actual sample: six OpenROAD processes, disjoint16CPU affinities covering96CPUs,7029 CPU ticks across the1second sample and61870940KiB total RSS. Seventh item pending available slot, no filler or final acceptance. Source remains current5-marker b622d31e, full final gates pending.
