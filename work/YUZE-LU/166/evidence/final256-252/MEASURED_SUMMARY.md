# R local-state 256: exact standalone native macro

Two state versions, 2048 state bytes total, eight arithmetic lanes.
Ordinary standard-cell storage; not a foundry SRAM macro.
Original 300MHz / I/O SDC, fixed internal M1–M10, 821 internal M10 signal pins.

Final extracted setup: 0.0102522 ns.
Final extracted hold: 0.00191164 ns.
All required physical checks passed; complete original GDS items: 0.
Exact final cell netlist: 189 numeric cases and three protocol tests passed.
Actual final-cell cycle counts are in meta/CASE_CYCLES.csv; time is cycles/300MHz,
not a full-model, power or system performance measurement.

Native files are in native/; actual-source abstract views are in abstract/.
Evidence, source and lineage are preserved with per-member MANIFEST hashes.
No old-ISA substitution, hierarchical timing-model or M11/M12 system qualification.
