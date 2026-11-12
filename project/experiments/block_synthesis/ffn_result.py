"""Result stores and serial SRAM verification reads for the #251 FFN."""

from ffn_scatter import s_pressure


READBACK_TAG = 0x10250


def sram_word_phases(client, mode, name):
    """One accepted request, one SRAM pipeline edge, one accepted response."""
    site = f'P{client}.S'
    request = {'kind': f'{name}.request', 'ticks': 1, 'claims': {f'{site}.request': 1}}
    ack = {'kind': f'{name}.ack', 'ticks': 1, 'claims': {f'{site}.response': 1}}
    if mode:
        request['ready_window'] = s_pressure(client, False)
        ack['ready_window'] = s_pressure(client, True)
    return request, {'kind': f'{name}.pipeline', 'ticks': 1, 'claims': {}}, ack


def mid_readback_words(tile_count):
    return tuple((tile % 3, 256 + 16 * (tile // 3) + word)
                 for tile in range(tile_count) for word in range(16))


def down_group_addresses(group, group_count, client):
    words = 32 if group < group_count - 1 else 12 if client == 0 else 10
    return range(32 * group, 32 * group + words)


def down_readback_words(group_count, client_count):
    return tuple((client, address) for client in range(client_count)
                 for group in range(group_count)
                 for address in down_group_addresses(group, group_count, client))


def readback_service(words, mode):
    phases = [phase for index, (client, _) in enumerate(words)
              for phase in sram_word_phases(client, mode, f'word{index}')]
    return {'ticks': len(phases), 'claims': {}, 'phases': phases}
