# Issue166 — R local-state implementation

Independent branch task/166-r-local-state, based on frozen PR160 delivery 9b3e7248.
Existing accepted R256, PR160, control/S worktrees and remote jobs are unchanged.

Scope: 16-row lane-local DFF state tiles; two versions; 1R1W; registered read
selection/data/merge; shared host read path; original integer arithmetic.
R256 and R1024 require separate complete physical acceptance at original 300MHz.
No physical qualification is currently claimed.

First component contract: read E0 acceptance → E1 local selection → E2 local data
→ E3 output. Write E0 acceptance → E1 local write selection/data → E2 storage.
Simultaneous E2 access is read-before-write. Reset invalidates control, not state.

References:
- https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_ram_1p_adv.sv
- https://github.com/lowRISC/opentitan/blob/master/hw/ip/prim/rtl/prim_ram_1r1w_adv.sv
- https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/ram/README.md
- https://yosyshq.readthedocs.io/projects/yosys/en/0.41/cmd/memory_map.html

Registration: management-hub PR5 pending. No board.json: board unverified,
synchronization pending; administrator/reviewer unassigned.
