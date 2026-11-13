"""Lower a typed operator graph using board-qualified, instance-specific recipes."""
from copy import deepcopy
import hashlib
import json
import math

from solver import Unsupported


DTYPE_BYTES = {
    'INT8': 1, 'UINT8': 1, 'INT16': 2, 'UINT16': 2, 'INT32': 4, 'UINT32': 4,
    'INT64': 8, 'UINT64': 8, 'FLOAT16': 2, 'BFLOAT16': 2, 'FLOAT': 4, 'DOUBLE': 8,
}


def signature(value):
    result = {'shape': value.get('shape'), 'dtype': value.get('dtype')}
    if 'format' in value:
        result['format'] = value['format']
    for field in ('numeric_format','storage_bytes'):
        if field in value:
            result[field] = value[field]
    return result


def value_size(value):
    shape = value.get('shape')
    dtype = value.get('dtype')
    if dtype not in DTYPE_BYTES or shape is None or any(type(dim) is not int or dim < 1 for dim in shape):
        raise Unsupported('event lowering requires a supported type and a concrete positive shape')
    size = value.get('storage_bytes', math.prod(shape) * DTYPE_BYTES[dtype])
    if type(size) is not int or size < 1:
        raise Unsupported('invalid event value storage size')
    return size


def indexed_bindings(node, model, hardware):
    """Bind an embedding lookup to a declared indexed DDR endpoint."""
    from indexed_memory import embedding_spec
    from numeric import Format

    spec = hardware['event_model']
    profiles = spec.get('indexed_gather', ())
    if not profiles:
        return []
    if len(node['inputs']) != 2 or len(node['outputs']) != 1:
        raise Unsupported('indexed Gather needs two inputs and one output')
    table, index = node['inputs']
    output = node['outputs'][0]
    values = model['values']
    formats = [values[name].get('format') for name in (table,output)]
    if not all(formats) or any(values[name]['dtype'] not in ('INT8','INT16','INT32') for name in (table,output)):
        raise Unsupported('indexed Gather needs explicitly quantized, identically encoded table and output')
    incoming, outgoing = (Format.read(fmt) for fmt in formats)
    definition = embedding_spec(node,model,incoming,outgoing)
    row_bytes = definition['row_words'] * 16
    if (incoming.bits != DTYPE_BYTES[values[table]['dtype']] * 8
            or outgoing.bits != DTYPE_BYTES[values[output]['dtype']] * 8
            or incoming.unsigned or outgoing.unsigned):
        raise Unsupported('indexed Gather type differs from its packed encoding')
    if incoming.bits * incoming.lanes != 128:
        raise Unsupported('event indexed Gather currently needs a fully packed 128-bit record')
    if value_size(values[table]) != definition['rows'] * row_bytes:
        raise Unsupported('indexed Gather storage size differs from the packed table')
    elements = math.prod(values[index]['shape'])
    length = elements * row_bytes
    if length != value_size(values[output]) or value_size(values[index]) != elements * definition['index_bits'] // 8:
        raise Unsupported('indexed Gather record storage differs from the typed input/output')
    if table not in spec.get('initial_backing', ()):
        raise Unsupported('indexed Gather table requires immutable DDR backing')
    parameters = {**definition, 'indices':elements}
    result = []
    for profile in profiles:
        source = spec['windows'][profile['index_window']]
        destination = spec['windows'][profile['output_window']]
        site = profile['site']
        if source['site'] != site or destination['site'] != site:
            raise Unsupported('indexed Gather window/control site differs')
        if source['bytes'] < value_size(values[index]) or destination['bytes'] < length:
            continue
        address_bits = profile['address_bits']
        bandwidth = profile['bytes_per_tick']
        setup = profile['setup_per_index']
        if (type(address_bits) is not int or not 1 <= address_bits <= 64 or
                type(bandwidth) is not int or bandwidth < 1 or type(setup) is not int or setup < 1):
            raise Unsupported('invalid indexed Gather address/timing profile')
        config = {**parameters, 'address_bits':address_bits}
        name = 'indexed-load:' + profile['id'] + ':' + hashlib.sha256(
            json.dumps(config,sort_keys=True).encode()).hexdigest()[:16]
        ticks = elements * (setup + (row_bytes + bandwidth - 1) // bandwidth)
        service = {'ticks':ticks,'claims':profile['claims'], 'nets':profile.get('nets', ()),
                   'control_site':site,'read_bytes':length,'indexed_read':config}
        for field in ('native_providers', 'memory_nets', 'memory_owner', 'memory_local_owner',
                      'memory_abi', 'memory_width_bits'):
            if field in profile:
                service[field] = deepcopy(profile[field])
        spec['services'][name] = service
        result.append({'id':profile['id'],'site':site,'ticks':ticks,'scratch_words':0,
                       'resources':[],'nets':[], 'event_stages':[
                           {'service':name,'inputs':{profile['index_window']:index},
                            'outputs':{profile['output_window']:output}}]})
    if not result:
        raise Unsupported('indexed Gather index and output do not fit any declared S destination')
    return result


def lower(model, hardware):
    """Produce candidates, without assigning any node to a particular Block.

    Recipes are executable hardware contracts keyed by a typed operator
    signature. Each recipe can supply a stage DAG and finitely sized scratch.
    No cost-only or floating-to-integer substitution is performed here.
    """
    h = deepcopy(hardware)
    spec = h['event_model']
    values = model['values']
    nodes = model['tasks']
    backing = set(spec.get('initial_backing', ()))
    if spec.get('weights_in_ddr'):
        backing.update(model.get('weights', ()))
    if spec.get('inputs_in_ddr'):
        backing.update(model['inputs'])
    spec['initial_backing'] = sorted(backing)
    initial = backing | set(spec.get('initial_copies', {}).values())
    external_outputs = model.get('external_outputs', ())
    if (not isinstance(external_outputs, (list, tuple)) or any(not isinstance(v, str) for v in external_outputs)
            or len(external_outputs) != len(set(external_outputs))
            or not set(external_outputs) <= set(model['outputs'])):
        raise Unsupported('external_outputs must name distinct graph outputs')
    external_outputs = set(external_outputs)
    producers = {}
    node_ids = set()
    for node in nodes:
        name = node['id']
        if name in node_ids:
            raise Unsupported('duplicate graph node ' + name)
        node_ids.add(name)
        for value in node['outputs']:
            if value in producers or value in initial or value not in values:
                raise Unsupported('ambiguous graph producer for ' + value)
            producers[value] = name

    by_operator = {}
    for recipe in spec.get('recipes', ()):
        by_operator.setdefault((recipe.get('domain', ''), recipe['op']), []).append(recipe)

    live = set(model['outputs']) | initial
    tasks = []
    for node in nodes:
        name = node['id']
        inputs, outputs = node['inputs'], node['outputs']
        live.update((*inputs, *outputs))
        missing = set(inputs) - initial - producers.keys()
        if missing:
            raise Unsupported(f'{name}: no placed producer or input backing for {sorted(missing)}')
        profile_in = [signature(values[value]) for value in inputs]
        profile_out = [signature(values[value]) for value in outputs]
        bindings = []
        for recipe in by_operator.get((node.get('domain', ''), node['op']), ()):
            if (recipe['inputs'] != profile_in or recipe['outputs'] != profile_out
                    or recipe.get('attributes', {}) != node.get('attributes', {})):
                continue
            binding = deepcopy(recipe['binding'])
            stages = binding['event_stages']
            if any('id' in stage or 'after' in stage for stage in stages):
                previous = []
                for stage in stages:
                    if not stage.get('id') or list(stage.get('after', ())) != previous:
                        raise Unsupported(f'{name}: recipe {binding["id"]} requires an internal stage DAG')
                    previous = [stage.pop('id')]
                    stage.pop('after', None)
            references = {f'in:{i}': value for i, value in enumerate(inputs)}
            references.update({f'out:{i}': value for i, value in enumerate(outputs)})
            for temporary, size in binding.pop('temporaries', {}).items():
                value = f'{name}::temporary::{temporary}'
                references[f'tmp:{temporary}'] = value
                sizes = spec.setdefault('value_bytes', {})
                if value in values or sizes.setdefault(value, size) != size:
                    raise Unsupported(f'{name}: conflicting temporary {temporary}')
            consumed, produced = set(), set()
            for stage in binding['event_stages']:
                for direction in ('inputs', 'outputs'):
                    stage[direction] = {window: references[ref] for window, ref in stage.get(direction, {}).items()}
                consumed.update(stage['inputs'].values())
                produced.update(stage['outputs'].values())
            if not set(inputs) <= consumed:
                raise Unsupported(f'{name}: recipe {binding["id"]} omits a graph input')
            if not set(outputs) <= produced:
                raise Unsupported(f'{name}: recipe {binding["id"]} omits a graph output')
            binding.setdefault('ticks', 1)
            binding.setdefault('scratch_words', 0)
            binding.setdefault('resources', [])
            binding.setdefault('nets', [])
            bindings.append(binding)
        if not bindings and node['op'] == 'Gather' and node.get('domain', '') == '':
            try:
                bindings = indexed_bindings(node,model,h)
            except Unsupported as exc:
                raise Unsupported(f'{name}: {exc}') from exc
        if not bindings:
            raise Unsupported(f'{name}: no qualified event recipe for {node.get("domain", "")}/{node["op"]} '
                              f'with inputs {profile_in} and outputs {profile_out}')
        for binding in bindings:
            for stage in binding['event_stages']:
                written = [w for w, value in stage.get('outputs', {}).items() if value in external_outputs]
                if written:
                    stage['backed_outputs'] = list(dict.fromkeys((*stage.get('backed_outputs', ()), *written)))
        tasks.append({'id': name, 'after': sorted({producers[v] for v in inputs if v in producers}),
                      'bindings': bindings})

    missing = set(model['outputs']) - initial - producers.keys()
    if missing:
        raise Unsupported('no graph producer or backing for outputs ' + str(sorted(missing)))
    if external_outputs - backing - producers.keys():
        raise Unsupported('external outputs need a DDR image or a graph producer')
    sizes = spec.setdefault('value_bytes', {})
    for value in sorted(live):
        size = value_size(values[value])
        if sizes.setdefault(value, size) != size:
            raise Unsupported('event storage size differs for ' + value)
    spec['live_out'] = model['outputs']
    if external_outputs:
        spec['external_outputs'] = sorted(external_outputs)
    return {'tasks': tasks}, h
