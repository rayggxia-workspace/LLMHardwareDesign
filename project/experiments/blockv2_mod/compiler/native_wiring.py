"""Accumulate static endpoint bindings from selected native candidates.

Different operators cannot silently rewire the same sink. A selectable mux
must be modeled explicitly before such alternatives may coexist in one plan.
"""
def merge(selected, candidate):
    result={sink:dict(binding) for sink,binding in selected.items()}
    for connection in candidate.get('connections',[]):
        for signal in connection['signals']:
            sink=signal['sink'];binding={'driver':signal['driver'],'width_bits':signal['width_bits']}
            if type(binding['width_bits']) is not int or binding['width_bits']<=0:raise ValueError('invalid endpoint width')
            if sink in result and result[sink]!=binding:
                raise ValueError('static wiring conflict at '+sink)
            result[sink]=binding
        for tie in connection.get('constant_inputs',[]):
            sink=tie['sink'];binding={'constant':tie['value']}
            if sink in result and result[sink]!=binding:
                raise ValueError('constant and routed driver conflict at '+sink)
            result[sink]=binding
    return result

def selected_plan(candidates):
    state={}
    for candidate in candidates:state=merge(state,candidate)
    return {'schema':'native-selected-static-wiring/1','bindings':state,
            'scope':'logical endpoints of this selected plan; physical routing and timing not claimed'}
