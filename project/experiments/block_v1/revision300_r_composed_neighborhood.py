"""Read actual successful R880 composition, never substitute original geometry."""
import json

def inspect(root,out,cpus,run):
    from io_slots import file_sha
    from revision300_r_neighborhood_export import export
    assert cpus==16
    base=out.parents[2];source=base/'block-v1-20261101-880/tasks/revision300-r-composed-vias'
    receipt=json.loads((source/'receipt.json').read_text());assert receipt['passed']and receipt['mode']==source.name
    names=('revision300-r-composed-vias.json','composed-candidate.odb','composed-candidate.def','composed-native-drc.rpt','compose.tcl')
    for n in names:assert file_sha(source/n)==receipt['outputs'][n]
    prior=json.loads((source/names[0]).read_text())
    assert prior['passed']and prior['combined']and prior['original_inputs_unchanged']and prior['exact_normal_net_header_path_rect_and_nonnet_delta']
    assert prior['ancestral_source_receipt_sha256']=='759cae257ff6731b8424eac6270a7bf255b6f0dc980ba0ff3a7bb508037b916b'
    assert prior['original_native_count']==265 and prior['added_markers']==0 and 0<prior['candidate_native_count']<265
    inputs={n:receipt['outputs'][n]for n in ('composed-candidate.odb','composed-candidate.def')}
    export(root,out,cpus,run,source,source,source/'composed-candidate.odb',source/'composed-candidate.def',source/'composed-native-drc.rpt',inputs,prior['candidate_native_count'],dict(script_sha256=receipt['outputs']['compose.tcl'],before_after_def_sha256=None))
