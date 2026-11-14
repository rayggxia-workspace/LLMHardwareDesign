"""Encode a selected resident ADD2 as Block V2 C-group local control images."""

from hashlib import sha256
from struct import unpack_from
from zlib import crc32

S32_ADD_META = 0xF0
NATIVE_ABI = 0x01930001
CAPACITY_PROFILE = 0x17630001
LOCAL_PM_BYTES = 4096
S_WORDS = 1024


def operands(descriptor):
    if (len(descriptor) != 128
            or unpack_from('<IHHI', descriptor) != (3, 128, 2, 7)
            or crc32(descriptor[:124]) != unpack_from('<I', descriptor, 124)[0]
            or any(descriptor[24:124])):
        raise ValueError('invalid PR260 ADD2 descriptor')
    left, right, dst, words = unpack_from('<4H', descriptor, 16)
    if (not words or max(left, right, dst) + words > S_WORDS
            or any(0 < abs(source - dst) < words for source in (left, right))):
        raise ValueError('ADD2 exceeds private SRAM or overwrites an unread word')
    return left, right, dst, words


def link(descriptor, command, source, target, pack_image):
    left, right, dst, words = operands(descriptor)
    if (command['op'] != 'EXEC' or command['required_completion'] != 'service_done'
            or len(command['read']) != 2 or len(command['write']) != 1):
        raise ValueError('selected event is not a completed resident binary EXEC')
    objects = command['read'] + command['write']
    if ([(x['address'], x['bytes']) for x in objects]
            != [(word * 16, words * 16) for word in (left, right, dst)]
            and [(x['address'], x['bytes']) for x in objects]
            != [(word * 16, words * 16) for word in (right, left, dst)]):
        raise ValueError('ADD2 descriptor and selected operands disagree')
    if any(x['site'] != target['group'] + '.S' for x in objects):
        raise ValueError('selected operands are outside the target private SRAM')

    topology = target['topology_id']
    if type(topology) is not int or not 0 < topology < 1 << 32:
        raise ValueError('invalid C-group local topology')
    width = target['execution_records_per_image']
    first_image_id = target['first_image_id']
    if (type(width) is not int or not 1 <= width <= 16
            or type(first_image_id) is not int or first_image_id <= 0
            or first_image_id + (words - 1) // width >= 1 << 32):
        raise ValueError('invalid C-group program image reservation')

    report = []
    for offset in range(0, words, width):
        image_id = first_image_id + len(report)
        rows = []
        code = []
        for i in range(offset, min(words, offset + width)):
            rows.append(dict(resource=0, service=0, native_op=0x100, native_abi_id=NATIVE_ABI,
                             native0=(1 << 15) | ((dst + i) << 5) | 0x18,
                             native1=(left + i) | ((right + i) << 10), native2=S32_ADD_META))
            code.extend((dict(op='L_EXEC', a=0, b=0, c=len(rows) - 1), dict(op='L_WAIT', x=1)))
        code.append(dict(op='L_END'))
        identity = dict(program_image_id=image_id, topology_id=topology,
                        native_abi_id=NATIVE_ABI)
        header = dict(**identity, entry_pc=0, max_steps=len(code), resource_mask=1,
                      capacity_profile_id=CAPACITY_PROFILE)
        task = dict(**identity, block_type=2, entry_pc=0, max_steps=len(code), required_resources=1)
        image = pack_image('local', code, dict(task=[task], execution=rows), header,
                           instruction_version=2)
        if len(image) > LOCAL_PM_BYTES or len(image) % 16:
            raise ValueError('C-group local image does not fit target PM')
        report.append(dict(image_id=image_id, first_word=offset, words=len(rows),
                           sha256=sha256(image).hexdigest(), image=image))
    return dict(source=source, task=command['task_id'], target=target['group'],
                descriptor_sha256=sha256(descriptor).hexdigest(),
                requires=dict(operands_resident=True, completion='all_local_waits_and_task_done'),
                images=report)
