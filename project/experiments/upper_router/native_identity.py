"""Exact hierarchical native identity implies unchanged recursive geometry.

Compare every native cell's polygons and every instance's identity/transform.
Avoid flattening repeated SRAM/standard-cell geometry into enormous global
unions. This is a stronger structural check, not a relaxed sampling check.
"""
import pya


def references(cell):
    return sorted((i.cell.name,str(i.cplx_trans),i.na,i.nb,str(i.a),str(i.b)) for i in cell.each_inst())


def verify(reference,joined,upper_cell):
    assert reference.dbu==joined.dbu,'native grid changed'
    original_top=reference.top_cell().name;counts={'cells':0,'layers':0,'instances':0}
    for cell in reference.each_cell():
        actual=joined.cell(cell.name);assert actual is not None,('native cell missing',cell.name)
        before=references(cell);after=references(actual)
        if cell.name==original_top:
            addition=(upper_cell,str(pya.ICplxTrans()),0,0,str(pya.Vector()),str(pya.Vector()))
            # KLayout reports scalar instance arrays as 0x0 arrays.
            assert after.count(addition)==1,('missing/duplicated upper reference',after[-3:],addition)
            after.remove(addition)
        assert before==after,('native instance identity/transform changed',cell.name)
        counts['instances']+=len(before)
        for info in reference.layer_infos():
            source_index=reference.find_layer(info);target_index=joined.find_layer(info)
            assert target_index is not None,('native layer missing',str(info))
            a=pya.Region(cell.shapes(source_index));b=pya.Region(actual.shapes(target_index))
            assert (a^b).is_empty(),('native cell geometry changed',cell.name,str(info))
            ta=sorted(s.text.to_s() for s in cell.shapes(source_index).each() if s.is_text())
            tb=sorted(s.text.to_s() for s in actual.shapes(target_index).each() if s.is_text())
            assert ta==tb,('native label changed',cell.name,str(info));counts['layers']+=1
        counts['cells']+=1
    return {'passed':True,**counts,'proof':'all native cell-layer XORs zero and all hierarchy identities/transforms equal'}
