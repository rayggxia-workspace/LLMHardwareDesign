"""Opt-in weighting of the PR #259 Manhattan term for the bounded study."""

import inspect

import search
from geometry import RoutingGrid


def enable(weight, jumps=False):
    if weight == 1 and not jumps:
        return
    original = inspect.getsource(search.connect)
    old = "new+heuristic(nxt), -new, nxt"
    new = f"new+{weight!r}*heuristic(nxt), -new, nxt"
    if original.count(old) != 1:
        raise ValueError("Unexpected router source for weighted A*")
    original = original.replace(old, new)
    if jumps:
        original = original.replace("grid.moves(node)", "jump_moves(grid, node, goals)")
        search.jump_moves = jump_moves
    exec(compile(original, "<weighted PR259 connect>", "exec"), vars(search))


def jump_moves(grid, node, goals):
    """Offer coarse-track shortcuts in addition to the original adjacent moves."""
    yield from RoutingGrid.moves(grid, node)
    if not grid.aligned(node[:2], grid.pitch):
        return
    axis = int(node[2] == 12)
    position = node[axis]
    pitch = grid.pitch
    targets = {position + offset*pitch for offset in (-64, -16, -4, 4, 16, 64)}
    for goal in goals:
        origin = grid.origin[axis]
        goal_track = (goal[axis] - origin) // pitch
        targets.update(origin + (goal_track+adjacent)*pitch for adjacent in (0, 1))
    for target in sorted(targets):
        if abs(target-position) <= pitch:
            continue
        if axis == 0:
            yield target, node[1], node[2]
        else:
            yield node[0], target, node[2]
