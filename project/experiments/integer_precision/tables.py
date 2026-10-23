"""Compile independent candidate LUT constants; not an imported llaccel table."""
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import json
from pathlib import Path


def build():
    with localcontext() as c:
        c.prec=80
        def integer(x):
            return int(x.to_integral_value(rounding=ROUND_HALF_EVEN))
        sigmoid=[min(65535,integer(Decimal(65536)/(1+(-(Decimal(i-128)/16)).exp()))) for i in range(257)]
        exponential=[integer((-Decimal(i)/256).exp()*Decimal(1<<24)) for i in range(4097)]
    return {"schema":"c1-independent-lut/1","compiler":"Decimal precision=80 ROUND_HALF_EVEN",
            "sigmoid_u16_f16":sigmoid,"exp_u32_f24":exponential}


def load(path=None):
    return json.loads(Path(path or Path(__file__).with_name("tables.json")).read_text(encoding="utf-8"))


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("output",type=Path); a=p.parse_args()
    a.output.write_text(json.dumps(build(),separators=(",",":"))+"\n",encoding="utf-8",newline="\n")
