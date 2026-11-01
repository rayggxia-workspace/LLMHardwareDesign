"""Prepare a fresh C8 pipeline using qualified physical constant drivers."""
import copy
import json
from pathlib import Path
import shutil


def prepare(root,out):
    from io_slots import file_sha
    base=out.parents[2]
    original=base/'block-v1-20261027-077/tasks/native-prepare'
    sealed=json.loads((original/'receipt.json').read_text());assert sealed['passed']is True
    control=base/'block-v1-20261027-118/tasks/native-constant-control'
    bound=json.loads((control/'receipt.json').read_text());assert bound['passed']is True
    path=control/'native-constant-control.json';assert file_sha(path)==bound['outputs'][path.name]
    proof=json.loads(path.read_text());assert proof['passed']is True
    assert proof['tie_mapping_proof']['passed']is True and proof['tie_mapping_proof']['wrong_constant_negative_rejected']is True
    assert proof['original_target_literals']==dict(adebug='0',mdebug='0')
    from native_driver_report import inspect
    inventories={name:inspect('\n'.join(rows)+'\n')for name,rows in proof['undriven_reports'].items()}
    assert set(inventories)=={'c8-before','c8-after','t6k-after','tied-import'}
    assert inventories['tied-import']['passed']and inventories['t6k-after']['passed']
    assert all(not inventories[name]['passed']and inventories[name]['undriven_used_signal_nets']==14
               for name in ['c8-before','c8-after'])
    mapped=control/'tied.v';assert file_sha(mapped)==bound['outputs'][mapped.name]==proof['tied_verilog_sha256']
    old=original/'inputs/shared109/shared109.v'
    assert file_sha(old)==sealed['outputs'][str(old.relative_to(original))]
    source=next(p for p in proof['input_sha256']if p.endswith('/1_2_yosys.v'))
    assert file_sha(old)==proof['input_sha256'][source],'Tie map must derive from the exact original prepared input'
    index=original/'native-preparation.json';assert file_sha(index)==sealed['outputs'][index.name]
    data=copy.deepcopy(json.loads(index.read_text()));data['candidates']=[c for c in data['candidates']if c['top']=='shared109']
    assert len(data['candidates'])==2
    inputs=out/'inputs/shared109';inputs.mkdir(parents=True)
    for suffix in ['.v','.sdc','-ports.json']:
        name='shared109'+suffix;src=original/'inputs/shared109'/name
        assert file_sha(src)==sealed['outputs'][str(src.relative_to(original))]
        shutil.copyfile(mapped if suffix=='.v'else src,inputs/name)
    for candidate in data['candidates']:
        folder=out/('shared109-'+candidate['policy']);folder.mkdir()
        old_folder=original/folder.name
        for name in ['pins.json','pins.tcl','config.mk']:
            src=old_folder/name;assert file_sha(src)==sealed['outputs'][str(src.relative_to(original))]
            if name=='config.mk':(folder/name).write_text(src.read_text().replace(str(original),str(out)))
            else:shutil.copyfile(src,folder/name)
        candidate.update(folder=str(folder),config_sha256=file_sha(folder/'config.mk'),
                         netlist_sha256=file_sha(inputs/'shared109.v'),
                         original_literal_netlist_sha256=file_sha(old),constant_import_control_sha256=file_sha(path),
                         physical_implementation_started=False)
    data.update(original_preparation_receipt_sha256=file_sha(original/'receipt.json'),
                constant_control_receipt_sha256=file_sha(control/'receipt.json'),constant_import_control_sha256=file_sha(path),
                used_signal_driver_controls=inventories,
                qualification='Qualified literal-to-Liberty tie mapping and identical IO/SDC/pin/budget inputs only; fresh import, boundary audit, P&R and full acceptance still required')
    (out/'native-preparation.json').write_text(json.dumps(data,indent=2)+'\n')
