# Seed economy simulation (docs/WORLD.md 3장). Daily model, greedy cheapest-first purchases.
# usage: python3 scripts/sim_seed_economy.py
# Archetypes = FEATURES 7장: light 3 days/4 records per week, normal 5/10, heavy 7/21, max 7/70 (cap 10 rewarded/day).
import math

ROOM = [9] * 6 + [12] * 5 + [18] * 4 + [24] * 2 + [30]          # 264, confirmed 2026-11-09
YARD = {                                                           # first update (마당) v2 = same tiers as the room
    "flower_bed": 9, "pinwheel": 9, "mailbox": 12, "duck_float": 12, "garden_lamp": 12,
    "picnic_mat": 18, "bird_feeder": 18, "bench": 18, "hammock": 24, "tent": 30,
}
SEED_PER_RECORD, GIFT, PLANT = 3, 6, 3
PLOTS, DAYS_TO_HARVEST = 3, 9
YARD_BEADS = 10                    # yard opens at 10 records (beads)

ARCH = {"light": (3, 4), "normal": (5, 10), "heavy": (7, 21), "max": (7, 70)}


def schedule(days_per_week, recs_per_week):
    """records per weekday (0..6), spread evenly over the recorded days"""
    rec_days = [round(i * 7 / days_per_week) for i in range(days_per_week)]
    out = [0] * 7
    for k in range(recs_per_week):
        out[rec_days[k % days_per_week]] += 1
    return out


def sim(arch, yard_release_day, garden=True, yard_prices=YARD, weeks=60):
    dpw, rpw = ARCH[arch]
    week = schedule(dpw, rpw)
    seeds, records, rec_days = GIFT, 0, 0
    room_left = sorted(ROOM)
    yard_left = sorted(yard_prices.values())
    plot_progress = [0] * PLOTS        # recorded days since planting; -1 = empty
    first_free = True
    log = {"room_done": None, "yard_done": None, "yard_open": None, "owned_w1": None, "owned_w4": None,
           "yard_owned_2w_after_open": None, "garden_spend": 0}
    for day in range(weeks * 7):
        n = week[day % 7]
        if n:
            records += n; rec_days += 1
            seeds += SEED_PER_RECORD * n
            if garden:
                for i in range(PLOTS):
                    plot_progress[i] += 1
                    need = 1 if first_free and i == 0 else DAYS_TO_HARVEST
                    if plot_progress[i] >= need:          # harvest, replant (3 seeds; very first crop free)
                        if first_free and i == 0:
                            first_free = False
                        if seeds >= PLANT:
                            seeds -= PLANT; log["garden_spend"] += PLANT; plot_progress[i] = 0
                        else:
                            plot_progress[i] = -10 ** 6    # waits; never matters in practice (checked below)
        yard_open = day >= yard_release_day and records >= YARD_BEADS
        if yard_open and log["yard_open"] is None:
            log["yard_open"] = day
        # buy cheapest available
        while True:
            pool = [(p, room_left) for p in room_left] + ([(p, yard_left) for p in yard_left] if yard_open else [])
            if not pool or seeds < min(p for p, _ in pool):
                break
            c, src = min(pool, key=lambda t: t[0])
            seeds -= c
            src.remove(c)
        owned = (len(ROOM) - len(room_left)) + (len(yard_prices) - len(yard_left))
        if day == 6: log["owned_w1"] = owned
        if day == 27: log["owned_w4"] = owned
        if log["yard_open"] is not None and day == log["yard_open"] + 13:
            log["yard_owned_2w_after_open"] = len(yard_prices) - len(yard_left)
        if not room_left and log["room_done"] is None: log["room_done"] = day
        if not yard_left and log["yard_done"] is None: log["yard_done"] = day
    return log


def wk(d):
    return "-" if d is None else f"{d / 7:.1f}주"


if __name__ == "__main__":
    total = sum(YARD.values())
    print(f"yard items {len(YARD)} total {total} seeds (= records {total // 3}); room 264; all {264 + total}")
    for label, release in (("launch user, yard update at week 5", 28), ("new user after the update", 0)):
        print(f"\n== {label}")
        for a in ARCH:
            r = sim(a, release)
            ng = sim(a, release, garden=False)
            print(f"{a:6} open {wk(r['yard_open'])} | room done {wk(r['room_done'])} | yard done {wk(r['yard_done'])} "
                  f"(no garden {wk(ng['yard_done'])}) | owned w1 {r['owned_w1']} w4 {r['owned_w4']} | "
                  f"yard items 2w after open {r['yard_owned_2w_after_open']}")
