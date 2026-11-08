"""Instantiate a disjoint-channel partition from the current frontier.

Fixed stripe recipes have affine cost in output-column count. Binary-search
the earliest common completion for integer columns, given actual resource
availability and cache hits. The resulting widths are scheduling decisions,
not a change to native arithmetic or the common greedy/DP action pool.
"""
from copy import deepcopy


def coefficients(child):
    b=child['binding'];width=child['columns'][1]-child['columns'][0]
    c=b.get('read_cache')
    fixed=(c['rows']*c['components'][0]*c['stripe']+1)*c['load_ticks'] if c else 0
    if (b['ticks']-fixed)%width:raise ValueError('nonaffine column service')
    return (b['ticks']-fixed)//width,fixed


def warm_bound(children,columns):
    slopes=[coefficients(c)[0] for c in children]
    intercepts=[(c['binding']['read_cache']['load_ticks'] if c['binding'].get('read_cache') else 0)
                for c in children]
    return (columns*min(slopes)+len(children)-1)//len(children)+min(intercepts)


def resized(child,lo,hi):
    b=deepcopy(child['binding']);old_width=child['columns'][1]-child['columns'][0];width=hi-lo
    c=b.get('read_cache');old_saved=0
    if c:old_saved=c['baseline_partial_external_reads']-c['cold_partial_external_reads']
    raw_ticks=b['ticks']+(old_saved*c['load_ticks'] if c else 0)
    raw_reads=b['external_read_words']+old_saved
    if any(value%old_width for value in (raw_ticks,raw_reads,b['external_write_words'])):
        raise ValueError('nonuniform raw column work')
    b['ticks']=raw_ticks//old_width*width;b['external_read_words']=raw_reads//old_width*width
    b['external_write_words']=b['external_write_words']//old_width*width
    if c:
        r=c['rows'];ca,cb=c['components'];k=c['K'];t=c['stripe'];n=r*width
        baseline=3*n*ca*cb*k;cold=r*ca*t+n*ca*cb*(k-t)+n*cb*k+1
        saved=baseline-cold;b['ticks']-=saved*c['load_ticks'];b['external_read_words']-=saved
        b['warm_ticks']=b['ticks']-r*ca*t*c['load_ticks'];b['warm_read_words']=b['external_read_words']-r*ca*t
        c.update(columns=width,baseline_partial_external_reads=baseline,
                 cold_partial_external_reads=cold,warm_partial_external_reads=cold-r*ca*t)
    b['id']+=';frontier-width='+str(width)
    return {'columns':[lo,hi],'binding':b}


def resolve(binding,state,data_ready):
    children=binding['parallel_shards']['children'];columns=binding['parallel_shards']['columns']
    parameters=[];seen=set()
    for child in children:
        b=child['binding'];claimed=set(b['resources'])
        if seen&claimed:raise ValueError('waterfill requires disjoint child resources')
        seen.update(claimed);slope,fixed=coefficients(child);c=b.get('read_cache')
        if c:
            old=state.cache.get(c['site'])
            reused=min(old[1],c['stripe']) if old and old[0]==c['tag'] else 0
            fixed-=reused*c['rows']*c['components'][0]*c['load_ticks']
        free=max([data_ready]+[state.resources[r][0] for r in b['resources']])
        if slope<=0 or fixed<0:raise ValueError('invalid affine column cost')
        parameters.append((free,slope,fixed))
    lower=max(free+slope+fixed for free,slope,fixed in parameters)
    upper=max(free+slope*columns+fixed for free,slope,fixed in parameters)
    def capacities(at):return [max(0,min(columns,(at-free-fixed)//slope)) for free,slope,fixed in parameters]
    while lower<upper:
        middle=(lower+upper)//2;caps=capacities(middle)
        if min(caps)>=1 and sum(caps)>=columns:upper=middle
        else:lower=middle+1
    remaining=columns;lo=0;result=[]
    for i,(child,cap) in enumerate(zip(children,capacities(lower))):
        width=min(cap,remaining-(len(children)-i-1))
        result.append(resized(child,lo,lo+width));remaining-=width;lo+=width
    if remaining:raise ValueError('incomplete frontier partition')
    return result
