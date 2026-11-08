"""Least-cost cutting of a bed's pieces from the lumber lengths a store stocks.

Used by make_bom.py for the buy lists. A *piece type* is a cut the design needs
(side board 120 in, corner post 14.5 in, ...), with a quantity. A *stock* is a
length the store sells, with a price. The solver enumerates every maximal way
to cut one stick of each stock length (a pattern), then finds the cheapest set
of patterns that covers every piece, by memoised search over the remaining
demand, always through a pattern that covers the first piece type still
wanted. Demands here are small (a few dozen pieces of up to a dozen types), so
this is exact and quick.

Posts may be cut a little short of the model length when that lets one more
fit on a stick: each piece type carries a ``min_len``. Boards are exact.
"""
import math
from collections import Counter
from functools import lru_cache

KERF = 0.125   # saw kerf, in


class Piece:
    def __init__(self, key, label, length, qty, min_len=None, short=None):
        self.key = key              # 'side', 'corner', ...
        self.label = label          # 'side board'
        self.length = float(length)  # model length, in
        self.qty = int(qty)
        self.min_len = float(min_len if min_len is not None else length)
        self.short = short or label  # label for a bar segment

    def __repr__(self):
        return f'Piece({self.key}, {self.length:g} in x {self.qty})'


def fits(stock_len, counts, pieces):
    n = sum(counts)
    if n == 0:
        return False
    need = sum(c * p.min_len for c, p in zip(counts, pieces)) + (n - 1) * KERF
    return need <= stock_len + 1e-9


def cut_lengths(stock_len, counts, pieces):
    """Actual cut length of each piece type on one stick: model length when it
    fits, otherwise the flexible pieces share the shortfall equally (clamped at
    their minimum). Returns (lengths by type, offcut)."""
    n = sum(counts)
    if n == 0:
        return {}, stock_len
    kerfs = (n - 1) * KERF
    slack = stock_len - sum(c * p.length for c, p in zip(counts, pieces)) - kerfs
    lens = {p.key: p.length for c, p in zip(counts, pieces) if c}
    if slack < -1e-9:
        short = -slack
        flex = {p.key: (p, c) for c, p in zip(counts, pieces) if c and p.min_len < p.length - 1e-9}
        # distribute the shortfall over the flexible pieces, clamping at each minimum
        while short > 1e-9 and flex:
            share = short / sum(c for _, c in flex.values())
            done = {}
            for k, (p, c) in flex.items():
                room = lens[k] - p.min_len
                take = min(share, room)
                lens[k] -= take
                short -= take * c
                if room - take < 1e-9:
                    done[k] = True
            for k in done:
                flex.pop(k)
            if not done and short > 1e-9:
                break
        slack = 0.0
    # round cuts down to 1/16 in so they are sawable, and recompute the offcut
    for k in lens:
        lens[k] = math.floor(lens[k] * 16 + 1e-6) / 16
    used = sum(c * lens[p.key] for c, p in zip(counts, pieces) if c) + kerfs
    return lens, max(0.0, stock_len - used)


def patterns(stock_len, pieces):
    """Every maximal count vector that fits one stick, bounded by the demand."""
    caps = [min(p.qty, int((stock_len + KERF) // (p.min_len + KERF))) for p in pieces]
    out = []

    def rec(i, counts):
        if i == len(pieces):
            if not fits(stock_len, counts, pieces):
                return
            # maximal: no further piece of any type (with demand left) fits
            for j, p in enumerate(pieces):
                if counts[j] < p.qty and fits(stock_len, counts[:j] + [counts[j] + 1] + counts[j + 1:], pieces):
                    return
            out.append(tuple(counts))
            return
        for c in range(caps[i], -1, -1):
            if fits(stock_len, counts + [c] + [0] * (len(pieces) - i - 1), pieces) or c == 0:
                rec(i + 1, counts + [c])
    rec(0, [])
    return out


def solve(pieces, stock_prices, allow=None):
    """stock_prices: {length_in: price}. allow: optional set of lengths to use.
    Returns a plan dict or None when some piece fits no allowed stock."""
    pieces = [p for p in pieces if p.qty > 0]
    if not pieces:
        return {'sticks': [], 'cost': 0.0, 'n_sticks': 0, 'offcut': 0.0, 'spare': 0, 'by_length': Counter(), 'pieces': []}
    lengths = sorted(L for L in stock_prices if allow is None or L in allow)
    for p in pieces:
        if not any(p.min_len <= L + 1e-9 for L in lengths):
            return None
    pats = []
    for L in lengths:
        for counts in patterns(L, pieces):
            lens, off = cut_lengths(L, counts, pieces)
            pats.append((L, stock_prices[L], counts, off))
    demand0 = tuple(p.qty for p in pieces)
    # Every pattern in a solution covers some piece, so the solution can be ordered to start with a pattern that
    # covers the first piece type still in demand: searching only those patterns at each step loses nothing and
    # keeps the number of demand states small even when a dozen piece types are cut together.
    pats_by_type = [[pat for pat in pats if pat[2][i]] for i in range(len(pieces))]

    @lru_cache(maxsize=None)
    def f(demand):
        if not any(demand):
            return (0.0, 0, 0, 0, 0.0, ())
        best = None
        i0 = next(i for i, d in enumerate(demand) if d)
        for L, price, counts, off in pats_by_type[i0]:
            nd = tuple(max(0, d - c) for d, c in zip(demand, counts))
            spare = sum(max(0, c - d) for d, c in zip(demand, counts))
            sub = f(nd)
            chosen = ((L, counts),) + sub[5]
            # cheapest first, then fewer sticks, fewer spare pieces, fewer distinct cut patterns, less offcut
            cand = (round(price + sub[0], 2), 1 + sub[1], spare + sub[2], len(set(chosen)), off + sub[4], chosen)
            if best is None or cand[:5] < best[:5]:
                best = cand
        return best

    cost, n, spare, _distinct, off, chosen = f(demand0)
    # replay the chosen patterns against the demand so each stick shows what is really cut from it
    remaining = list(demand0)
    sticks = []
    for L, counts in sorted(chosen, key=lambda x: (-x[0], tuple(-c for c in x[1]))):
        actual = []
        for c, d in zip(counts, remaining):
            k = min(c, d)
            actual.append(k)
        remaining = [d - k for d, k in zip(remaining, actual)]
        lens, offcut = cut_lengths(L, actual, pieces)
        cuts = []
        for c, p in zip(actual, pieces):
            if c:
                cuts.append({'key': p.key, 'label': p.label, 'short': p.short, 'n': c, 'len': lens[p.key], 'model_len': p.length})
        sticks.append({'stock': L, 'price': stock_prices[L], 'cuts': cuts, 'offcut': offcut})
    # group identical sticks
    grouped = []
    for s in sticks:
        sig = (s['stock'], tuple((c['key'], c['n'], c['len']) for c in s['cuts']))
        for g in grouped:
            if g['sig'] == sig:
                g['count'] += 1
                break
        else:
            grouped.append({'sig': sig, 'count': 1, **s})
    for g in grouped:
        g.pop('sig')
    by_length = Counter()
    for g in grouped:
        by_length[g['stock']] += g['count']
    return {'sticks': grouped, 'cost': round(sum(g['price'] * g['count'] for g in grouped), 2), 'n_sticks': sum(g['count'] for g in grouped),
            'offcut': round(sum(g['offcut'] * g['count'] for g in grouped), 3), 'spare': spare, 'by_length': by_length, 'pieces': pieces}


def piece_cuts(plan):
    """{piece key: sorted set of cut lengths used in the plan}."""
    out = {}
    for g in plan['sticks']:
        for c in g['cuts']:
            out.setdefault(c['key'], set()).add(c['len'])
    return {k: sorted(v) for k, v in out.items()}


def single_length_options(pieces, stock_prices):
    """For each stock length S: the plan that uses S for everything that fits it, and for each
    longer piece the shortest stock that holds it. Answers 'should I buy 6 ft or 8 ft sticks?'."""
    opts = []
    lengths = sorted(stock_prices)
    for S in lengths:
        allow = {S}
        for p in pieces:
            if p.qty and p.min_len > S + 1e-9:
                fit = [L for L in lengths if L >= p.min_len - 1e-9]
                if not fit:
                    allow = None
                    break
                allow.add(fit[0])
        if allow is None:
            continue
        if not any(p.qty and p.min_len <= S + 1e-9 for p in pieces):
            continue   # nothing would come from S
        plan = solve(pieces, stock_prices, allow)
        if plan:
            plan['length'] = S
            plan['forced'] = sorted(allow - {S})
            opts.append(plan)
    return opts


def frac(x):
    """23.875 -> '23 7/8', 24.0 -> '24'."""
    whole = int(math.floor(x + 1e-9))
    rem = x - whole
    for den in (2, 4, 8, 16):
        k = round(rem * den)
        if abs(rem - k / den) < 1e-6:
            return f'{whole}' if k == 0 else (f'{k}/{den}' if whole == 0 else f'{whole} {k}/{den}')
    return f'{x:g}'


def cut_phrase(c):
    """'3 corner posts x 14 1/2 in'."""
    return f"{c['n']} {c['label']}{'s' if c['n'] > 1 else ''} x {frac(c['len'])} in"


def stick_text(g, offcut=True):
    """What one stick of a group is cut into: 'side board, whole' or '2 end boards x 47 15/16 in; 1/8 in offcut'."""
    if len(g['cuts']) == 1 and g['cuts'][0]['n'] == 1 and g['offcut'] < 0.5:
        return f"{g['cuts'][0]['label']}, whole"
    body = ' + '.join(cut_phrase(c) for c in g['cuts'])
    if not offcut:
        return body
    return body + (f" ({frac(g['offcut'])} in offcut)" if g['offcut'] >= 0.5 else ' (no offcut)')
