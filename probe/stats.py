"""Rank statistics implemented in-tree (average ranks for ties).

Spearman's rho is the Pearson correlation of ranks. Kendall's tau-b adjusts
for ties in both variables. Both are computed on (intended, landed) order
pairs; landed positions are unique within a block, intended ranks may tie
(e.g. the arrival ladder shares one fee).
"""

import math


def _ranks(values):
    """Average ranks (1-based) for a list of values, ties share the mean rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        mean_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = mean_rank
        i = j + 1
    return ranks


def spearman(xs, ys) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("need >= 2 paired observations")
    rx, ry = _ranks(xs), _ranks(ys)
    n = len(xs)
    mx = sum(rx) / n
    my = sum(ry) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    if vx == 0 or vy == 0:
        return 0.0
    return cov / math.sqrt(vx * vy)


def kendall_tau_b(xs, ys) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("need >= 2 paired observations")
    n = len(xs)
    concordant = discordant = ties_x = ties_y = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = (xs[i] > xs[j]) - (xs[i] < xs[j])
            dy = (ys[i] > ys[j]) - (ys[i] < ys[j])
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                ties_x += 1
            elif dy == 0:
                ties_y += 1
            elif dx == dy:
                concordant += 1
            else:
                discordant += 1
    denom = math.sqrt((concordant + discordant + ties_x) *
                      (concordant + discordant + ties_y))
    if denom == 0:
        return 0.0
    return (concordant - discordant) / denom
