"""Use measured native/pin lower bounds in placement search, never acceptance."""
import hashlib,json,math
from pathlib import Path


def budgets(path,drivers):
    path=Path(path);parent=path.parent/'receipt.json'
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    receipt=json.loads(parent.read_text())
    assert receipt['passed']and receipt['stage']=='minimum-native-pin-capacitance-failure-only'
    assert receipt['outputs'][path.name]==sha(path)
    data=json.loads(path.read_text())
    assert data['passed']and data['diagnostic_executed']and not data['whole_system_qualified']
    assert data['placements']
    measured=None
    for placement in data['placements']:
        rows={r['net']:r for r in placement['rows']}
        assert len(rows)==len(placement['rows'])and set(rows)==set(drivers)
        current={}
        for name,row in rows.items():
            driver=drivers[name]
            assert row['driver']==driver['driver']
            limit=driver['physical_driver']['max_capacitance_ff']
            assert row['max_capacitance_ff']==limit
            values=(limit,row['native_ground_cap_ff'],row['minimum_input_pin_cap_ff'])
            assert all(math.isfinite(v)and v>=0 for v in values)
            remaining=limit-values[1]-values[2]
            assert remaining>0,('Native/pin necessary bound already impossible',name)
            current[name]=remaining
        if measured is None:measured=current
        else:assert measured==current,'Placement-independent native/input budgets disagree'
    return measured,{str(path):sha(path),str(parent):sha(parent),str(Path(__file__)):sha(__file__)}
