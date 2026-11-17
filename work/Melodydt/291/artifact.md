# Seven-model Word tables — artifact contract

## Purpose and content

Deliver one editable DOCX with two publication tables, without changing the manuscript or rerunning simulations. Table II contains short-prefill, estimated 512-token-prefill, and decode throughput (token/s) across seven models. Table III contains covered on-chip and on-chip-plus-DDR energy, each divided into decode and short-prefill (J/token). Preserve calibration ranges; do not create a midpoint or claim whole-chip coverage.

## Template evidence and invariants

- Read-only reference: `D:/Download/v2-IEEE-integrated.docx`; SHA-256 `93859d49268877883a61d5fbddaf07692406588d76dc0ec5b5c11a8d4b2b409f`.
- Reference rendered using Microsoft Word 16.0; page 3 supplies the table specimen.
- Letter page, 0.75-inch top and 1-inch bottom margins. Final manuscript section has 907-twip left/right margins, giving a full-width table of 10,426 twips (18.3903 cm).
- Preserve source style/theme/numbering definitions. Table text is Times New Roman, 8 pt. Captions use source `table head` style, centered small capitals, above tables. Black top/bottom rules are 1 pt; header and group separator rules are 0.5 pt. No shading or vertical borders.
- Intentional adaptation: the insert uses one full-width column, two native editable tables, 7.5-pt notes, and explicit table numbers II/III. The original manuscript body, illustrations, bibliography/custom XML, and metadata are not part of the insert. The original file remains untouched.
- Seven model columns align between the tables. Energy scope labels span their two phase rows. Repeating headers and non-splitting rows; no fixed row heights.

## Data and notation

- Input: `work/Melodydt/291/combined-results.json`, already frozen for the combined speed/energy report.
- Speed: three decimals. 512-token values use `estimated_input_tok_s_to_logits`, including one final output head. Short prefill excludes the final head; the distinction must appear in the note.
- Energy: four-decimal low–high J/token ranges. Prefill is the 2-token short window. Ranges are calibration endpoints, not confidence intervals or complete error bounds.
- Clearly identify system-level TLM evaluation, estimated P512 without independent full-sequence validation, covered energy subtotal, and excluded components.

## Acceptance and QA

Exactly two editable tables and seven model columns; 21 speed values and 28 energy ranges match the frozen source after formatting. Source manuscript hash unchanged. Render the final DOCX and inspect every output page for clipping, wrapping, cell alignment, and readable notes. The bundled render_docx.py route was attempted but cannot run without LibreOffice; use approved, independent hidden Word read-only export and Poppler PNG rendering, recording this fallback. Publish only the DOCX as the requested artifact; QA PDF/PNGs remain task-local.
