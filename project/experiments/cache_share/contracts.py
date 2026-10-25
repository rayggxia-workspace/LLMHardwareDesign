"""Strict evidence schemas: missing fields must never count as success."""
KEYS={'actual_M_active_reset','no_stale_completion','SRAM_retained'}
def protocol(p):
 if not isinstance(p,dict)or set(p)!=KEYS or any(v is not True for v in p.values()):raise ValueError('incomplete or non-boolean reset protocol')
def config(m,variant,stall=None):
 if type(m.get('profile'))is not int or m['profile']!=variant:raise ValueError('variant binding')
 if stall is not None and(type(m.get('stall'))is not int or m['stall']!=stall):raise ValueError('stall binding')
