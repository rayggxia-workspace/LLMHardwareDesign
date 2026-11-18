# C-v35 independent gate preparation

Prepared while 120194 runs. No EDA is submitted by preparation. Wait for CU to identify a complete stable candidate and its fresh results; prioritize one promising candidate, not six expensive full checks.

After explicit freeze confirmation, run `freeze.py RUN OUTPUT_DIRECTORY 'CU confirmation'`. It requires the producer's final `candidate.sha256`, status, complete pre/post RCX artifacts and fresh reports; verifies their hashes, actual frozen stage code, source inputs, models and original CTS geometry reference; and performs a second immutable-source check. `accepted` remains false. Do not invoke this merely because some final filenames exist during routing/extraction.

For that frozen source, run separate bounded jobs for:

1. Original focused upper and antenna checks on its actual GDS. Bind both reports and rule hashes to `frozen-source.json` before and after.
2. Complete dynamic pre/post RCX per-net material comparison using `C-final-v1/def-material.py` and freshly exported actual layer/via metadata. Any discrepancy needs candidate-specific normalization, actual readback, re-extraction and physical identity evidence before qualifying SPEF.
3. `geometry-driver.tcl` in two fresh OpenROAD processes: original exact overlay 4_cts ODB and the candidate final ODB, followed by `geometry-driver-check.py`. This checks original die, signal BPins, every hardmacro transform and all-layer pins, and 153 unique BUF_X8 drivers. PG BPin differences are explicitly retained for review.

`verify-binding.py frozen-source.json` is required before and after each check. Use existing `C-final-v1` full independent timing/electrical/async/PG/SDC, functional and model gates only on the exact selected candidate with qualified extraction. The old nine-net repairs and the 222+5 native classification are references, never automatically inherited. Root owns the same-final-GDS complete unchanged deck.
