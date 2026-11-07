"""Functional indexed reads through the explicitly virtual external interface.

This does not assert that PR182 generates tensor-dependent addresses in RTL.
The virtual endpoint interprets the address expression; only its bounded data
transfer is timed. Address generation timing remains unqualified and visible.
"""
import hashlib
import json
import math

from memory import descriptor_ticks
from solver import Unsupported


def index_address(index, rows, row_words, offset_words, words, address_bits):
    """ONNX negative indices, checked before any external request is issued."""
    if isinstance(index, bool) or not isinstance(index, int):
        raise ValueError('Gather index must be an integer')
    if not -rows <= index < rows:
        raise ValueError('Gather index outside table')
    index %= rows
    address = (index * row_words + offset_words) * 16
    if not 0 <= offset_words or words < 1 or offset_words + words > row_words:
        raise ValueError('Gather transfer outside selected row')
    if address + words * 16 > 1 << address_bits:
        raise ValueError('Gather address overflow')
    return address


def register_gather(hardware, attributes, index_words, output_words):
    profile = hardware.get('virtual_memory')
    if not profile:
        raise Unsupported('indexed external Gather requires the declared virtual memory interface')
    alternatives = []
    for site, meta in hardware['sites'].items():
        if index_words + output_words > meta['words']:
            continue
        channel = int(meta['memory_group']) % profile['channels']
        resource = f'virtual-memory.channel.{channel}'
        hardware['resources'][resource] = 1
        demand = site + '.io.indexed-load'
        hardware['nets'].setdefault(demand, {'cost':1, 'fixed':False,
            'unit':'logical interface bundle', 'qualification':'indexed data/ACK demand; physical pins unbound'})
        ticks = (index_words * meta['io_read_ticks'] +
                 descriptor_ticks(profile, output_words, 'load', meta['io_write_ticks']))
        digest = hashlib.sha256(json.dumps(attributes, sort_keys=True).encode()).hexdigest()[:20]
        sid = f'{site}.indexed-gather:{digest}'
        hardware['services'][sid] = {
            'op': 'IndexedGather', 'numeric': 'native-record-v1',
            'attributes': attributes, 'site': site, 'input_words': [index_words],
            'output_words': [output_words], 'ticks': ticks,
            'resources': [resource, meta['io_resource']],
            'nets': sorted(set(meta.get('memory_nets', {}).get('load', [])) | {demand}),
            'qualified': True, 'qualification_scope': 'virtual interface functional indexed read',
            'controller': 'virtual-memory', 'address_generation_timing_qualified': False,
            'native_program': [{'command': 'VirtualIndexedLoad', **attributes,
                'completion': 'destination S write ACK',
                'index_bounds': 'ONNX negative-index normalization, then checked row address',
                'address_generation': 'virtual endpoint; not an RTL qualification'}],
            'external_read_words': output_words,
        }
        alternatives.append(sid)
    if not alternatives:
        raise Unsupported('no S can hold one Gather index record and output record')
    return alternatives


def embedding_spec(node, model, input_format, output_format):
    table, indices = node['inputs']
    dims = model['values'][table]['shape']
    attrs = node.get('attributes', {})
    if set(attrs) - {'axis'} or len(dims) != 2 or attrs.get('axis', 0) not in (0, -2):
        raise Unsupported('embedding Gather requires axis 0 of a two-dimensional table')
    if table not in model.get('weights', []):
        raise Unsupported('runtime Gather table requires an explicit materialization rule')
    if input_format != output_format:
        raise Unsupported('Gather preserves exact table encoding; quantization is a separate step')
    index_type = model['values'][indices].get('dtype')
    if index_type not in ('INT32', 'INT64'):
        raise Unsupported('Gather indices must retain ONNX INT32/INT64 encoding')
    if any(not isinstance(d, int) or d < 1 for d in dims):
        raise Unsupported('embedding table dimensions must be resolved')
    if dims[1] % input_format.lanes:
        raise Unsupported('embedding row needs explicitly aligned offline record packing')
    expected = model['values'][indices]['shape'] + [dims[1]]
    if model['values'][node['outputs'][0]]['shape'] != expected:
        raise Unsupported('Gather output shape differs from index shape plus embedding width')
    return {'table': table, 'rows': dims[0], 'row_words': dims[1] // input_format.lanes,
            'index_bits': int(index_type[3:]), 'index_lanes': 1,
            'table_words': math.prod(dims) // input_format.lanes}
