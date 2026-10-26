"""Extend a SHA-pinned tech LEF without modifying any native bytes.

This generates geometry and early RC estimates, not a 12-layer RCX rule file.
Final extraction/DRC/calibration remain explicit downstream gates.
"""
import argparse
import hashlib
import json
from pathlib import Path

MARKER_START = "# BEGIN BLOCK_V1_RESEARCH_EXTENSION\n"
MARKER_END = "# END BLOCK_V1_RESEARCH_EXTENSION\n"
PROPERTIES = ('# BEGIN BLOCK_V1_LEF58_PROPERTIES\nPROPERTYDEFINITIONS\n'
              '  LAYER LEF58_SPACING STRING ;\nEND PROPERTYDEFINITIONS\n'
              '# END BLOCK_V1_LEF58_PROPERTIES\n')


def generate(native, spec, out):
    raw = native.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == spec["native_tech_sha256"], "unqualified native platform"
    text = raw.decode("utf-8")
    assert "LAYER metal11" not in text and "LAYER via10\n" not in text
    assert text.count("END metal10") == 1
    g, e = spec["geometry_um"], spec["electrical"]
    assert g["cut_width"] + 2*g["enclosure"] <= g["width"] + 1e-12
    assert g["width"] + g["spacing"] <= g["pitch"] + 1e-12
    assert abs(g["metal11_bottom"] - 12.09 - g["dielectric_gap"]) < 1e-9
    assert abs(g["metal12_bottom"] - g["metal11_bottom"] - g["thickness"] - g["dielectric_gap"]) < 1e-9
    lines = [MARKER_START]
    for level, direction in [(11,"HORIZONTAL"),(12,"VERTICAL")]:
        cut = level - 1
        lines.append("""LAYER via{cut}
  TYPE CUT ;
  WIDTH {cw} ;
  SPACING {cs} ;
  RESISTANCE {vr} ;
END via{cut}
LAYER metal{level}
  TYPE ROUTING ;
  DIRECTION {direction} ;
  WIDTH {w} ;
  PITCH {p} ;
  OFFSET {o} ;
  SPACINGTABLE
    PARALLELRUNLENGTH 0.0 2.7 4.0
    WIDTH 0.0 {s} {s} {s}
    WIDTH 1.5 {s} {s} {s} ;
  PROPERTY LEF58_SPACING "SPACING {s} ENDOFLINE {ew} WITHIN {ei} ;" ;
  RESISTANCE RPERSQ {r} ;
  THICKNESS {t} ;
  HEIGHT {h} ;
END metal{level}
""".format(cut=cut,cw=g["cut_width"],cs=g["cut_spacing"],vr=e["via_resistance_ohm"],
           level=level,direction=direction,w=g["width"],p=g["pitch"],o=g["track_offset"],
           s=g["spacing"],ew=g["eol_width"],ei=g["eol_within"],r=e["sheet_resistance_ohm"],
           t=g["thickness"],h=g["metal%d_bottom"%level]))
    for cut in [10,11]:
        a=g["width"]/2
        b=g["cut_width"]/2
        lines.append("""VIA BV1_via{cut} DEFAULT
  RESISTANCE {r} ;
  LAYER metal{cut} ; RECT -{a} -{a} {a} {a} ;
  LAYER via{cut} ; RECT -{b} -{b} {b} {b} ;
  LAYER metal{upper} ; RECT -{a} -{a} {a} {a} ;
END BV1_via{cut}
VIARULE BV1_via{cut}_array GENERATE
  LAYER metal{cut} ; ENCLOSURE {enc} {enc} ;
  LAYER metal{upper} ; ENCLOSURE {enc} {enc} ;
  LAYER via{cut} ; RECT -{b} -{b} {b} {b} ; SPACING {pitch} BY {pitch} ;
END BV1_via{cut}_array
""".format(cut=cut,upper=cut+1,r=e["via_resistance_ohm"],a=a,b=b,enc=g["enclosure"],pitch=g["cut_width"]+g["cut_spacing"]))
    lines.append(MARKER_END)
    extension = "".join(lines)
    # Insert new layer order before subsequent VIA declarations. Native bytes,
    # including their whitespace and units, remain exactly recoverable.
    point = text.index("END metal10") + len("END metal10")
    emitted = text[:point] + "\n" + extension + text[point:]
    assert emitted.count('VERSION 5.6 ;') == 1
    emitted = emitted.replace('VERSION 5.6 ;','VERSION 5.8 ;\n'+PROPERTIES,1)
    restored=emitted.replace('VERSION 5.8 ;\n'+PROPERTIES,'VERSION 5.6 ;',1)
    assert restored.replace("\n"+extension, "", 1).encode() == raw
    out.mkdir(parents=True, exist_ok=False)
    (out / "native.tech.lef").write_bytes(raw)
    (out / "research12.tech.lef").write_bytes(emitted.encode())
    tracks = "".join("make_tracks metal%d -x_offset %g -x_pitch %g -y_offset %g -y_pitch %g\n" %
                     (level,g["track_offset"],g["pitch"],g["track_offset"],g["pitch"]) for level in [11,12])
    (out / "new_tracks.tcl").write_text(tracks)
    r_per_um = e["sheet_resistance_ohm"]/g["width"]
    c_ff_per_um = 0.0088541878128*e["relative_permittivity"]*(g["width"]/g["dielectric_gap"]+2*g["thickness"]/g["spacing"])
    estimates = {"qualification":"EARLY_PARAMETER_ESTIMATE_ONLY", "resistance_unit":"ohm/um",
                 "capacitance_unit":"fF/um", "via_resistance_unit":"ohm", "variants":{}}
    for name, factor in e["estimate_variants"].items():
        estimates["variants"][name] = dict(resistance=r_per_um*factor,capacitance=c_ff_per_um*factor,
                                          via_resistance=e["via_resistance_ohm"]*factor)
    (out / "early-rc-estimates.json").write_text(json.dumps(estimates,indent=2)+"\n")
    (out / "gds-map.json").write_text(json.dumps(spec["gds"],indent=2)+"\n")
    audit = dict(native_sha256=hashlib.sha256(raw).hexdigest(),
                 overlay_sha256=hashlib.sha256(emitted.encode()).hexdigest(), native_bytes_preserved=True,
                 version_header_override={'native':'5.6','compiled_overlay':'5.8'},
                 geometry_only=True, full_12_layer_rcx_qualified=False, full_drc_qualified=False)
    (out / "generation.json").write_text(json.dumps(audit,indent=2)+"\n")
    return audit


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("native",type=Path)
    parser.add_argument("spec",type=Path)
    parser.add_argument("out",type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(args.native,json.loads(args.spec.read_text()),args.out),indent=2))
