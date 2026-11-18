# C-v20 rsp_data14 same-net M10 bridge

Evidence root: `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-m10-notch14-v2`. This independent candidate starts from the frozen rsp_data52-patched ODB, never overwrites that prior evidence, and adds only two standard0.8um-width M10 segments on `dma_s_rsp_data[14]`.

The S pin is `(1367.095,579.070)-(1369.095,581.070)`um. The nearby same-net vertical route right edge is x1366.895um and its lower edge is y581.000um. A narrow0.2um gap and0.07um vertical overlap create the spacing notch. A thin copper sliver would risk minimum-width failure, so the candidate uses an ordinary-width short L bridge: center x1366.495 from y580.670 to581.400, and center y580.670 from x1366.495 to1367.495um.

`C-m10-notch14-structural-receipt.json` proves all original target routes are preserved, all other nets and all non-NETS DEF sections unchanged, and exported Verilog byte-identical. Candidate ODB SHA256 is8fe478bae4f1410e921359f2dd1094a45556c33de1bd44e60dfe606de5ff7e9f. Its hook reconstructs this exact source net and is not safe to blindly reuse after a separate reroute.

The actual S leaf GDS contains an M10 segment extending above the abstract pin. The delivered leaf DEF binds this to the same `rsp_data[14]` net and `PIN rsp_data[14]`: `(448190,1016140,extension0)` to `(448190,1020940)` in2000DBU/um. The macro R0 origin `(1144,72)`um maps that exact segment to the observed actual geometry. The first strict check intentionally failed because this leaf geometry had not yet been included. The revised check independently reconstructs top-net routes, pin and this leaf route, then requires exact equality with the entire actual connected M10 component before and after, not merely intersection with a named pin. It separately checks new copper does not touch other components and preserves800nm spacing, plus local width/notch/space rules and unchanged other layers.

Standalone native checker120006 versus the52-only baseline:234→232, only the two rsp_data14 M10 spacing markers disappear, no added markers. Fresh VDD/VSS connectivity passes. Full native clearance remains false; all232 pre-existing markers remain explicit. Actual regenerated GDS strict component/rule check is recorded separately. This is a local patch qualification, not complete C backend signoff.

## Final local qualification

Job120011 completed with all strict actual-GDS assertions passing. Net14 adds exactly0.744um² M10, removes zero, and has one connected component whose full actual geometry equals the independent top-net+pin+leaf-net reconstruction before and after. No foreign component overlap;800nm foreign separation passes. Target space markers2→0, notch1→0, width violations0. All other local layers are unchanged. `C-m10-notch14-gds-receipt.json` and `C-m10-notch14-pin-placement-binding.json` bind the actual artifacts and macro location.

CU received the full frozen ODB hash and may start the integrated electrical/antenna ECO from this double-patched baseline. Both source and previous52-only evidence remain untouched. Full native clearance remains false with232 inherited markers; the integrated final candidate still requires fresh parasitics, timing/electrical checks, actual full GDS checks and function/state/control equivalence.
