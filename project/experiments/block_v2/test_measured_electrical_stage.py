"""Real native GRT fixture and negative controls for an intermediate-only ECO gate."""
from pathlib import Path
from measured_electrical_stage import validate,violations

def main():
    root=Path(__file__).resolve().parents[3]
    text=(root/'work/YUZE-LU/143/r-input-hold/failed-090/5_global_route.rpt').read_text()
    assert {k:len(v) for k,v in violations(text).items()}==dict(capacitance=96,slew=7)
    result=validate(text,text,[96,7,0,0],[96,7,0,0])
    assert result['passed'] and result['native_leaf_accepted'] is False
    def reject(after,counts):
        try:validate(text,after,[96,7,0,0],counts)
        except AssertionError:return
        raise AssertionError('Negative control incorrectly passed')
    reject(text.replace('wire699687/Z','new_invalid_driver/Z'),[96,7,0,0])
    reject(text.replace('-256.24 (VIOLATED)','-257.24 (VIOLATED)'),[96,7,0,0])
    reject(text,[96,7,1,0]);reject(text,[96,7,0,1]);reject(text,[95,7,0,0])
    print('PASS: real96cap/7slew GRT fixture; new pin/worse worst/setup/hold/count negative controls rejected. Final qualification remains false.')

if __name__=='__main__':main()
