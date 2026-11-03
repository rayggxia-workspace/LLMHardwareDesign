# R local-state 1024: exact standalone native macro

Two state versions, 8192 state bytes total, eight arithmetic lanes.
Ordinary standard-cell storage; not a foundry SRAM macro.
Optional finalization pipeline: False; op4/op5 extra cycles: 0.
Original 300MHz / I/O SDC, fixed internal M1鈥揗10, 821 internal M10 signal pins.

Final extracted setup: 0.0674889 ns.
Final extracted hold: 0.000210554 ns.
All required physical checks passed; complete original GDS items: 0.
Exact final cell netlist: 189 numeric cases and three protocol tests passed.
Actual final-cell cycle counts are in meta/CASE_CYCLES.csv; time is cycles/300MHz,
not a full-model, power or system performance measurement.

Native files are in native/; actual-source abstract views are in abstract/.
Evidence, source and lineage are preserved with per-member MANIFEST hashes.
No old-ISA substitution, hierarchical timing-model or M11/M12 system qualification.
