"""Independent finite-region, affine-access and beat proofs for Issue76.

No producer or old-closure imports.  Lifetimes are half-open macro intervals;
all-task reservations are conservatively resident at every macro.
"""
from collections import defaultdict
import math

from audit_io76 import need, wire_packets


CAPACITIES = {"M": 32768, "V": 16384, "R": 32768, "EXT": 134217728,
              "ROM": 4260100, **{"S%d" % i: 32768 for i in range(8)}}


def lifetime(value, events):
    need(type(events) is int and events > 0, "finite macro lifetime bound")
    if value == ["task_start", "task_end"]:
        return 0, events
    need(isinstance(value, list) and len(value) == 2 and all(type(v) is int for v in value)
         and 0 <= value[0] < value[1] <= events, "half-open finite lifetime")
    return tuple(value)


def check_regions(capacities, allocations, events):
    need(capacities == CAPACITIES, "fixed finite bank inventory")
    objects, banks, high = {}, defaultdict(list), {}
    for value in allocations:
        name, bank = value["object"], value["bank"]
        off, count = value["offset"], value["bytes"]
        need(isinstance(name, str) and name and name not in objects and bank in capacities,
             "unique existing-bank object")
        need(type(off) is type(count) is int and off >= 0 and count > 0
             and off+count <= capacities[bank], "finite capacity "+name)
        begin, end = lifetime(value["lifetime"], events)
        for left, right, birth, death, other in banks[bank]:
            intersects_bytes = off < right and left < off+count
            intersects_time = begin < death and birth < end
            need(not (intersects_bytes and intersects_time), "live alias "+name+"/"+other)
        banks[bank].append((off, off+count, begin, end, name))
        high[bank] = max(high.get(bank, 0), off+count)
        objects[name] = value
    need(bool(objects), "nonempty concrete memory deployment")
    return objects, high


def affine_bounds(access, loops):
    base, size = access["offset"], access["bytes"]
    repeat, stride = access["repeat"], access["stride"]
    axes = access["index_strides"]
    need(all(type(v) is int for v in (base, size, repeat, stride))
         and base >= 0 and size > 0 and repeat > 0 and stride >= 0,
         "actual finite access")
    need(isinstance(axes, list) and len(axes) <= len(loops) and all(type(v) is int for v in axes)
         and all(type(v) is int and v > 0 for v in loops), "affine loop dimensions")
    axes = [0]*(len(loops)-len(axes))+axes
    low = high = base
    for step, count in zip(axes, loops):
        delta = step*(count-1)
        low += min(0, delta)
        high += max(0, delta)
    return low, high+(repeat-1)*stride+size


def check_access(access, objects, loops, macro, events):
    need(access["object"] in objects and access["mode"] in ("read", "write"), "actual access object/mode")
    obj = objects[access["object"]]
    low, high = affine_bounds(access, loops)
    begin, end = lifetime(obj["lifetime"], events)
    need(0 <= low < high <= obj["bytes"], "affine access exceeds object "+access["object"])
    need(begin <= macro < end, "use outside live interval "+access["object"])
    return obj


def beat_residues(offset, strides, loops):
    need(len(strides) <= len(loops), "beat loop depth")
    axes = [0]*(len(loops)-len(strides))+list(strides)
    result = {offset % 16}
    for step, count in zip(axes, loops):
        period = 16//math.gcd(step, 16)
        result = {(r+i*step) % 16 for r in result for i in range(min(count, period))}
    return result


def local_beats(object_offset, access, loops):
    residues = beat_residues(object_offset+access["offset"], access["index_strides"], loops)
    totals = {sum((r+i*access["stride"]+access["bytes"]+15)//16
                  - (r+i*access["stride"])//16 for i in range(access["repeat"])) for r in residues}
    need(len(totals) == 1, "noninvariant loop bank beats need explicit residue scheduling")
    return totals.pop()


def packet_segments(source_offset, destination_offset, length, segments=1, source_stride=0, destination_stride=0):
    need(all(type(v) is int for v in (source_offset, destination_offset, length, segments, source_stride, destination_stride))
         and source_offset >= 0 and destination_offset >= 0 and length > 0 and segments > 0
         and source_stride >= 0 and destination_stride >= 0, "finite segmented packet layout")
    total = {key: 0 for key in ("payload_bytes", "wire_bytes", "packets", "src_beats", "dst_beats", "bus_beats")}
    peak = 0
    for segment in range(segments):
        p = wire_packets(source_offset+segment*source_stride, destination_offset+segment*destination_stride, length)
        for key in total:
            total[key] += p[key]
        peak = max(peak, p["max_fifo_bytes"])
    total["max_fifo_bytes"] = peak
    return total
