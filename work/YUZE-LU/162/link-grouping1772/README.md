# Preserve accepted Link8 grouping for the new S-arbiter interface

Refs #162 / PR #163. The new3200um `control_s_arbiter_r7` completed all native and fixed-PG gates at `r256-arbiter-perimeter-1738/17380` and `r256-arbiter-fixed-pg-1741/17380`; setup/hold +1.194584/+0.022119ns. This is individual block qualification only.

Fresh1757 selection passed. Automatic grouping from the changed pin geometry hit the existing reset-bank316-Link8 assertion before generating a topology receipt. Preserve the failed output and task result; its dependent function/STA/placement tasks have not run. No new reset block or weakened assertion is introduced.

The optional `--link-grouping-reference` uses the actual previous1470um physical manifest solely to reproduce the accepted logical lane grouping. It requires the3200um selected arbiter, the same1402 port names and identical other22 physical rows. New selected dimensions, pins and six-file identities stay authoritative for every physical checker; only the grouping recipe uses the reference coordinates. Existing contraction,316-link/25-bank checks and all validation remain intact. Default invocation is unchanged. Full fresh topology, function, placement, native and upper RC/geometry/PG/300MHz still have to run; no previous composition qualification transfers.

Rule1.0.0; registration PR5 pending; board unverified/sync pending; reviewer unassigned; Draft PR, no merge.
