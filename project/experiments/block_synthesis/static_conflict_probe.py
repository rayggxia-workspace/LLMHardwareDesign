"""Inspectable regression for serial users of mutually exclusive metal nets."""
from copy import deepcopy
import json

from loop_dp import optimize
from verify_loop_dp import verify


def main():
    hardware = {'resources': {'r': 1}, 'sites': {'S': {'words': 8}},
                'nets': {n: {'cost': 1} for n in ('a', 'b', 'c')},
                'incompatible_nets': [['a', 'b']]}

    def binding(name, net, ticks):
        return {'id': name, 'site': 'S', 'resources': ['r'], 'ticks': ticks,
                'nets': [net], 'scratch_words': 1,
                'external_read_words': 1, 'external_write_words': 0}

    tasks = [{'id': 'first', 'bindings': [binding('use_a', 'a', 1)]},
             {'id': 'second', 'after': ['first'], 'bindings': [
                 binding('conflicting_b', 'b', 1), binding('legal_c', 'c', 2)]}]
    legal = optimize(tasks, hardware, width=8)
    assert legal['nets'] == ['a', 'c'] and legal['makespan'] == 3
    checked = verify(tasks, hardware, legal)
    unchecked = deepcopy(hardware)
    unchecked.pop('incompatible_nets')
    forged = optimize(tasks, unchecked, width=8)
    assert forged['nets'] == ['a', 'b']
    try:
        verify(tasks, hardware, forged)
    except ValueError as error:
        independent_rejection = str(error)
        assert 'incompatible static' in independent_rejection
    else:
        raise AssertionError('independent verifier accepted illegal serial topology')
    tasks[1]['bindings'] = tasks[1]['bindings'][:1]
    no_alternative = optimize(tasks, hardware, width=8)
    assert no_alternative['status'] == 'no_plan_in_bounded_search'
    print(json.dumps({'status': 'passed', 'legal_alternative': legal,
                      'legal_check': checked, 'forged_plan_rejection': independent_rejection,
                      'no_legal_alternative': no_alternative}, indent=2))


if __name__ == '__main__':
    main()
