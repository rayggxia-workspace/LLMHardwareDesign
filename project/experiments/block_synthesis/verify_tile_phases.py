"""Independent reconstruction of the existing tile command/descriptor order.

Does not import tile_phases, tile_recipe, transition or candidate generation.
The declared qualified P/feeder/E boundaries and memory abstraction are inputs.
"""
from memory import descriptor_ticks


def program(leaf,hardware):
    s=leaf['dot_tile'];q=hardware['tile_service_profiles'];m=hardware['virtual_memory']
    rows,cols,k=s['rows'],s['columns'],s['K'];rt,ct=s['tile']
    p=hardware['leaf_inventory'][leaf['macro_binding']['M']]
    e=hardware['leaf_inventory'][leaf['macro_binding']['E']] if 'E' in leaf['macro_binding'] else None
    def phase(meta,direction):
        access=meta['io_write_ticks'] if direction=='load' else meta['io_read_ticks']
        return {'channel':meta['memory_group']%m['channels'],'ticks':descriptor_ticks(m,1,direction,access),
                'kind':'external-load-until-S-commit' if direction=='load' else 'external-store-until-ACK'}
    def native(ticks,kind):return {'channel':-1,'ticks':ticks,'kind':kind}
    def loop(n,body):return {'repeat':n,'body':{'sequence':body}}
    pl,ps=phase(p,'load'),phase(p,'store');steps=[loop(16,[pl])]
    row_sizes=[(rt,rows//rt)]+([(rows%rt,1)] if rows%rt else [])
    col_sizes=[(ct,cols//ct)]+([(cols%ct,1)] if cols%ct else [])
    for r,nr in row_sizes:
        if not nr:continue
        pm=q['P'][str(r)];feeder=q['feeder'][str(r)]
        for n,nn in col_sizes:
            if not nn:continue
            reduction=[loop(n,[pl])]
            for component in range(3):
                reduction.extend([loop(r,[pl]),native(feeder['cold'] if component==0 else feeder['reuse_b'],'tile-feeder'),
                    native(pm['scale'],'tile-scale'),native(pm['execute'],'tile-execute')])
            grid=[loop(k,reduction)]
            if n==1:grid.append(loop(r,[native(pm['final_store'],'tile-final-store'),ps]))
            else:
                if e is None:raise ValueError('independent tile phase missing E')
                packets=r*((n+3)//4);single=q['P']['1']
                grid.append(loop(packets,[native(pm['final_store'],'tile-final-store'),ps]))
                grid.append(loop(packets,[phase(e,'load'),native(q['e_shift_store'],'tile-E-service'),phase(e,'store')]))
                scatter=[loop(3,[pl,pl,native(q['feeder']['1']['cold'],'tile-feeder'),
                    native(single['scale'],'tile-scale'),native(single['execute'],'tile-execute')]),
                    native(single['final_store'],'tile-final-store'),ps]
                grid.append(loop(r*n,scatter))
            steps.append(loop(nr*nn,grid))
    return {'sequence':steps}
