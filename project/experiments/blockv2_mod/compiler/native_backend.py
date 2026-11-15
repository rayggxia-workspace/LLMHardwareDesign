"""Encode allocated native operations and validate them against target RTL routes.

No archived descriptors, machine pages or stage manifests are accepted here.
A provider encodes the selected operation from its live operands and parameters.
"""
from dataclasses import dataclass
from hashlib import sha256
import struct
import zlib

from resident_rms_contract import lower_record
from resident_gather_contract import pack_u0_records, LINK_ABI

@dataclass(frozen=True)
class EncodedCall:
    target: int
    group: str
    completion: str
    signature: tuple
    descriptor: bytes | None
    compact_record: tuple | None
    semantic_descriptor_sha256: str

class NativeBackend:
    def __init__(self, profile):
        self.topology=profile['topology_id']
        self.targets={t['group']:t for t in profile['targets']}
        if len(self.targets)!=len(profile['targets']):
            raise ValueError('duplicate target group')
        if len({t['id'] for t in self.targets.values()})!=len(self.targets):
            raise ValueError('duplicate native target ID')

    def encode(self, group, provider, command):
        target=self.targets[group]
        terminal, encoder=provider
        if command['required_completion']!=terminal:
            raise ValueError('selected command completion differs from encoder')
        raw=encoder(command)
        if not isinstance(raw,bytes) or len(raw)!=128:
            raise ValueError('native encoder must return one complete descriptor')
        schema,size,opcode,abi,topology=struct.unpack_from('<IHHII',raw)
        if size!=128 or topology!=self.topology or zlib.crc32(raw[:124])!=int.from_bytes(raw[124:],'little'):
            raise ValueError('native encoder produced an invalid descriptor')
        signature=(schema,abi,opcode)
        routes={(r['schema'],r['abi'],r['opcode']):r for r in target['routes']}
        route=routes.get(signature)
        compact=None
        descriptor=raw
        if route is None:
            # The translation is selected by the target's declared compact ABI,
            # not by a hardcoded U0 instance number.
            if not any(key[:2]==(1,LINK_ABI) for key in routes):
                raise ValueError('target lacks native descriptor route')
            compact=lower_record({'target':target['id'],'service_signature':signature,
                                  'required_completion':terminal},raw,self.topology,
                                 target_id=target['id'])
            if compact is None:raise ValueError('no compact encoder for native operation')
            signature=(1,LINK_ABI,compact[0])
            route=routes.get(signature)
            descriptor=None
        if route is None or terminal not in route['completions']:
            raise ValueError('target lacks encoded operation completion')
        return EncodedCall(target['id'],group,terminal,signature,descriptor,compact,sha256(raw).hexdigest())

    def encode_deployment_call(self, group, provider, command):
        """The whole-graph path must use descriptor-fetching native calls."""
        call=self.encode(group,provider,command)
        if call.descriptor is None or call.compact_record is not None:
            raise ValueError('whole-graph deployment cannot install a per-operation local page')
        return call

    def compact_page(self, calls, *, image_id, pack_image):
        calls=tuple(calls)
        if not calls or len({c.group for c in calls})!=1 or any(c.compact_record is None for c in calls):
            raise ValueError('compact page requires one target and only compact calls')
        return pack_u0_records([c.compact_record for c in calls],
                               topology=self.topology,image_id=image_id,pack_image=pack_image)
