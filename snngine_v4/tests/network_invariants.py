"""
Invariants of a correctly built network, checked on exported arrays (numpy only, no engine import).

Every check compares the built network with its configuration or with an independent recomputation, never with
the engine's own intermediate results alone. Each returns a list of violations (empty: the invariant holds), each
violation a short dict that says what differs and where.

Exported arrays (see engine_export.py), N neurons, S synapses per neuron, D delays, G location groups:
  post (N, S) int     target neuron of synapse s of neuron n (N_rep transposed)
  bnd (N, D + 1) int  delay buckets (N_delays transposed): synapses [bnd[n, d], bnd[n, d + 1]) have delay d
  w (N, S) float      initial weights as built
  types (N,) int      1 inhibitory, 2 excitatory (NeuronType)
  groups (N,) int     location group
  pos (N, 3) float    neuron positions
  conns               list of dicts {src_type, snk_type, n_synapses, w0}: the configured type connections
"""

from __future__ import annotations

import numpy as np

INH, EXC = 1, 2


def _v(check, msg, **detail):
    return {"check": check, "message": msg, **{k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in detail.items()}}


def synapse_delays(bnd: np.ndarray, S: int) -> np.ndarray:
    """(N, S) delay of every synapse from the delay buckets."""
    delay = np.zeros((bnd.shape[0], S), dtype=np.int16)
    cols = np.arange(S)[None, :]
    for r in range(1, bnd.shape[1]):
        delay += (cols >= bnd[:, r:r + 1])
    return delay


def check_targets_valid(post, types):
    out = []
    N = len(types)
    if (post < 0).any():
        out.append(_v("targets_valid", "deleted or unset synapses (-1)", count=int((post < 0).sum())))
    if (post >= N).any():
        out.append(_v("targets_valid", "target index >= N", count=int((post >= N).sum())))
    auto = post == np.arange(len(post))[:, None]
    if auto.any():
        out.append(_v("targets_valid", "autapses", count=int(auto.sum()),
                      neurons=np.unique(np.nonzero(auto)[0])[:10]))
    return out


def check_type_counts(post, types, conns):
    """Every neuron has exactly the configured number of synapses onto each target type (and none onto a type
    without a configured connection)."""
    out = []
    pc = np.clip(post, 0, len(types) - 1)
    for src in np.unique(types):
        rows = np.nonzero(types == src)[0]
        tgt = types[pc[rows]]
        for snk in np.unique(types):
            expected = sum(int(c["n_synapses"]) for c in conns if c["src_type"] == src and c["snk_type"] == snk)
            got = (tgt == snk).sum(axis=1)
            bad = got != expected
            if bad.any():
                out.append(_v("type_counts", f"type {src} -> type {snk}: expected {expected} per neuron",
                              neurons_wrong=int(bad.sum()), of=len(rows), got_min=int(got.min()),
                              got_max=int(got.max()), got_mean=float(got.mean()), first=rows[bad][:10]))
    return out


def check_delay_buckets(bnd, S):
    out = []
    if (bnd[:, 0] != 0).any():
        out.append(_v("delay_buckets", "first bucket boundary not 0", count=int((bnd[:, 0] != 0).sum())))
    if (bnd[:, -1] != S).any():
        out.append(_v("delay_buckets", "last bucket boundary not S", count=int((bnd[:, -1] != S).sum())))
    if (np.diff(bnd, axis=1) < 0).any():
        out.append(_v("delay_buckets", "bucket boundaries decrease", count=int((np.diff(bnd, axis=1) < 0).sum())))
    return out


def cell_of_position(pos, shape, seg):
    """Grid cell (x, y, z) of each position: floor(pos / shape * seg), clipped to the grid."""
    seg = np.asarray(seg)
    return np.clip(np.floor(np.asarray(pos) / np.asarray(shape) * seg).astype(np.int64), 0, seg - 1)


def check_groups(pos, groups, shape, seg):
    """All neurons of a group lie in one grid cell, and different groups in different cells."""
    out = []
    cells = cell_of_position(pos, shape, seg)
    G = int(groups.max()) + 1
    key = (cells[:, 0] * seg[1] + cells[:, 1]) * seg[2] + cells[:, 2]
    per_group = [np.unique(key[groups == g]) for g in range(G)]
    multi = [g for g, k in enumerate(per_group) if len(k) > 1]
    if multi:
        out.append(_v("groups", "groups spanning several cells", count=len(multi), groups=multi[:10]))
    owners = {}
    for g, k in enumerate(per_group):
        for c in k:
            owners.setdefault(int(c), []).append(g)
    shared = {c: gs for c, gs in owners.items() if len(gs) > 1}
    if shared:
        out.append(_v("groups", "cells holding several groups", count=len(shared)))
    return out


def group_cells(pos, groups, shape, seg, G=None):
    """(G, 3) grid cell of each group from its neurons' positions; -1 for a group without neurons."""
    cells = cell_of_position(pos, shape, seg)
    G = int(groups.max()) + 1 if G is None else int(G)
    gc = np.full((G, 3), -1, dtype=np.int64)
    for g in np.unique(groups):
        gc[g] = cells[groups == g][0]
    return gc


def delay_rule(group_cell, D, d_max=None):
    """Independent recomputation of the group-to-group delay: round((D - 1) * d / d_max), d = cell distance,
    d_max = the grid's diagonal (default: the largest distance between the given cells)."""
    c = group_cell.astype(np.float64)
    dist = np.linalg.norm(c[:, None, :] - c[None, :, :], axis=2)
    d_max = dist.max() if d_max is None else float(d_max)
    return np.rint((D - 1) * dist / d_max).astype(np.int64), dist


def check_delays(post, bnd, groups, group_cell, D, engine_g2g_delay=None, d_max=None):
    """Every synapse's delay bucket equals the delay of its source and target groups; the engine's own
    group-to-group delay table (if given) equals the independent recomputation round((D - 1) d / d_max) (groups
    with neurons only), where an exact tie (x.5) may round either way: the engine computes in float32 from
    positions (measured at 9 x 9 x 9: 374 pairs at exactly 7.5 rounded to 7), this check in float64 from cells.
    The synapses are then checked against the engine's table, which is what the simulation uses."""
    out = []
    S = post.shape[1]
    rule, dist = delay_rule(group_cell, D, d_max)
    occ = (group_cell >= 0).all(axis=1)
    expected_table = rule
    if engine_g2g_delay is not None:
        eng_full = np.asarray(engine_g2g_delay)
        x = (D - 1) * dist / (dist.max() if d_max is None else float(d_max))
        tie = np.abs(x - np.floor(x) - 0.5) < 1e-6
        ok = (eng_full == rule) | (tie & (np.abs(eng_full - rule) == 1))
        bad_pairs = ~ok[np.ix_(occ, occ)]
        if bad_pairs.any():
            out.append(_v("delays", "engine group-to-group delay table differs from round((D-1) d / d_max)",
                          pairs_wrong=int(bad_pairs.sum())))
        else:
            expected_table = eng_full
    pc = np.clip(post, 0, len(groups) - 1)
    got = synapse_delays(bnd, S)
    expected = expected_table[groups[:, None], groups[pc]]
    bad = got != expected
    if bad.any():
        out.append(_v("delays", "synapse delay bucket differs from the delay of its group pair",
                      synapses_wrong=int(bad.sum()), fraction=float(bad.mean()),
                      neurons=np.unique(np.nonzero(bad)[0])[:10]))
    return out


def check_weights_by_type(post, w, types, conns, tol=1e-6):
    """Every synapse's initial weight is the configured w0 of its (source type, target type) connection."""
    out = []
    pc = np.clip(post, 0, len(types) - 1)
    pre = np.broadcast_to(types[:, None], post.shape)
    tgt = types[pc]
    for c in conns:
        m = (pre == c["src_type"]) & (tgt == c["snk_type"])
        if m.any():
            bad = np.abs(w[m] - float(c["w0"])) > tol
            if bad.any():
                vals, cnt = np.unique(np.round(w[m][bad], 6), return_counts=True)
                out.append(_v("weights", f"type {c['src_type']} -> {c['snk_type']}: weight not w0 = {c['w0']}",
                              synapses_wrong=int(bad.sum()), of=int(m.sum()),
                              wrong_values={str(float(a)): int(b) for a, b in zip(vals[:5], cnt[:5])}))
    return out


def check_count_tables(tables, L, D, conns):
    """
    The construction's cumulative synapse counts per source group and delay (one table per type connection, rows
    0 .. D, row 0 = 0) are non-decreasing, end at the connection's synapse count, and no delay bucket asks for more
    synapses than there are target neurons of the connection's target type at that delay (minus the neuron itself
    at delay 0 when source and target type are the same). `tables`: {(src_type, snk_type): (D + 1, G) array}.
    `L`: L_Group_neuronCounts (2 + 2 D, G): rows 0, 1 = inhibitory, excitatory neurons of the group; rows 2 + d
    and 2 + D + d = inhibitory and excitatory neurons within delay d. Only groups with neurons of the source type
    are checked (a group without them builds no synapses from that table).
    """
    out = []
    L = np.asarray(L)
    for c in conns:
        key = (c["src_type"], c["snk_type"])
        if key not in tables:
            continue
        has = L[0 if c["src_type"] == INH else 1] > 0
        T = np.asarray(tables[key])[:, has]
        b = np.diff(T, axis=0)                                   # (D, G') bucket sizes
        if (T[0] != 0).any():
            out.append(_v("count_tables", f"{key}: first row not 0", groups=int((T[0] != 0).sum())))
        if (T[-1] != int(c["n_synapses"])).any():
            out.append(_v("count_tables", f"{key}: last row not {c['n_synapses']}", groups=int((T[-1] != int(c['n_synapses'])).sum())))
        if (b < 0).any():
            d, g = np.nonzero(b < 0)
            out.append(_v("count_tables", f"{key}: negative delay bucket", buckets=int((b < 0).sum()),
                          delays=np.unique(d)[:10], min_bucket=int(b.min())))
        targets = L[2 + (0 if c["snk_type"] == INH else D): 2 + (0 if c["snk_type"] == INH else D) + D][:, has].copy()
        if c["src_type"] == c["snk_type"]:
            targets[0] -= 1
        over = b > targets
        if over.any():
            out.append(_v("count_tables", f"{key}: bucket larger than available target neurons",
                          buckets=int(over.sum()), max_excess=int((b - targets)[over].max())))
    return out


def ee_profile(post, types, groups, group_cell):
    """Median excitatory -> excitatory synapses per ordered pair of groups with neurons, by cell distance."""
    G = len(group_cell)
    _, dist = delay_rule(group_cell, 2)
    occ = (group_cell >= 0).all(axis=1)
    pc = np.clip(post, 0, len(types) - 1)
    m = (types[:, None] == EXC) & (types[pc] == EXC)
    pre_g = np.broadcast_to(groups[:, None], post.shape)[m]
    cnt = np.bincount(pre_g * G + groups[pc][m], minlength=G * G).reshape(G, G).astype(float)
    pair = occ[:, None] & occ[None, :]
    d_round = np.round(dist, 6)
    return {float(d): float(np.median(cnt[pair & (d_round == d)])) for d in np.unique(d_round[pair]) if d > 0}


def check_profile_decreases(post, types, groups, group_cell, min_ratio=3.0):
    """Connection probability falls with delay (sigmoidal_connection_probability): the median number of E -> E
    synapses per group pair at the nearest distance is at least `min_ratio` times the one at the largest
    distances. Measured (5 x 5 x 5 groups): correct construction 10 to 13; the old transpose error 1.3 to 1.8, so
    "larger" alone would not detect it."""
    prof = ee_profile(post, types, groups, group_cell)
    ds = sorted(prof)
    near, far = prof[ds[0]], np.median([prof[d] for d in ds[-max(1, len(ds) // 5):]])
    if not near >= min_ratio * max(far, 1.0):
        return [_v("profile", "E -> E synapses per group pair do not fall with distance", near=near, far=far)]
    return []


def all_checks(ex: dict) -> dict:
    """Run every applicable check on one export (dict of arrays and metadata); {check name: violations}."""
    post, types, groups = ex["post"], ex["types"], ex["groups"]
    res = {
        "targets_valid": check_targets_valid(post, types),
        "type_counts": check_type_counts(post, types, ex["conns"]),
        "delay_buckets": check_delay_buckets(ex["bnd"], post.shape[1]),
        "groups": check_groups(ex["pos"], groups, ex["shape"], ex["seg"]),
    }
    G = int(np.prod(ex["seg"]))
    gc = group_cells(ex["pos"], groups, ex["shape"], ex["seg"], G)
    d_max = float(np.linalg.norm(np.asarray(ex["seg"], dtype=np.float64) - 1))
    res["delays"] = check_delays(post, ex["bnd"], groups, gc, ex["D"], ex.get("g2g_delay"), d_max)
    res["weights"] = check_weights_by_type(post, ex["w"], types, ex["conns"])
    if "count_tables" in ex:
        res["count_tables"] = check_count_tables(ex["count_tables"], ex["L"], ex["D"], ex["conns"])
    res["profile"] = check_profile_decreases(post, types, groups, gc)
    return res
