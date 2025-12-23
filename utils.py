import secrets
from datetime import datetime
from fractions import Fraction


def generate_join_code(length: int = 8) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def current_month_yyyy_mm() -> str:
    return datetime.now().strftime("%Y-%m")


def format_iqd(n: float | int) -> str:
    try:
        n_int = int(round(n))
    except Exception:
        n_int = 0
    return f"{n_int:,} IQD"


def _round_net_fractions_to_int(net_frac_by_user_id: dict[int, Fraction]) -> dict[int, int]:
    base = {}
    frac_parts = []
    base_sum = 0

    for uid, net in net_frac_by_user_id.items():
        floor_int = net.numerator // net.denominator
        base[uid] = int(floor_int)
        base_sum += int(floor_int)
        frac = net - floor_int
        frac_parts.append((uid, frac))

    residual = -base_sum
    if residual <= 0:
        return base

    frac_parts.sort(key=lambda x: (x[1], -x[0]), reverse=True)

    for uid, _frac in frac_parts[:residual]:
        base[uid] += 1

    return base


def compute_net_balances(users, expenses, participants_map):
    paid = {u.id: 0 for u in users}
    consumed = {u.id: Fraction(0, 1) for u in users}

    for e in expenses:
        paid[e.payer_id] += int(e.amount_iqd)
        parts = participants_map.get(e.id, [])
        if not parts:
            continue

        n = len(parts)
        share = Fraction(int(e.amount_iqd), n)
        for uid in parts:
            consumed[uid] += share

    net_frac = {uid: Fraction(paid[uid], 1) - consumed[uid] for uid in paid.keys()}
    return _round_net_fractions_to_int(net_frac)


def simplify_debts(net_by_user_id):
    creditors = [(uid, amt) for uid, amt in net_by_user_id.items() if amt > 0]
    debtors = [(uid, -amt) for uid, amt in net_by_user_id.items() if amt < 0]

    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    transfers = []
    i = j = 0
    while i < len(debtors) and j < len(creditors):
        d_uid, d_amt = debtors[i]
        c_uid, c_amt = creditors[j]
        pay = min(d_amt, c_amt)
        if pay > 0:
            transfers.append((d_uid, c_uid, pay))
            d_amt -= pay
            c_amt -= pay

        if d_amt == 0:
            i += 1
        else:
            debtors[i] = (d_uid, d_amt)

        if c_amt == 0:
            j += 1
        else:
            creditors[j] = (c_uid, c_amt)

    return transfers
