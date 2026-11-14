# Seed economy simulation (docs/WORLD.md 3장). Daily model, greedy cheapest-first purchases.
# usage: python3 scripts/sim_seed_economy.py
# Archetypes = FEATURES 7장: light 3 days/4 records per week, normal 5/10, heavy 7/21, max 7/70,
# binge = real tester week (2,35,17,16,11,3,9 records/day). Seeds go to the first DAILY_CAP records of a day
# (5 since 2026-11-15 대표 결정 I1·I2; was 10).
import math

ROOM = [9] * 6 + [12] * 5 + [18] * 4 + [24] * 2 + [30]          # 264, confirmed 2026-11-09
YARD = {                                                           # first update (마당) v2 = same tiers as the room
    "flower_bed": 9, "pinwheel": 9, "mailbox": 12, "duck_float": 12, "garden_lamp": 12,
    "picnic_mat": 18, "bird_feeder": 18, "bench": 18, "hammock": 24, "tent": 30,
}
SEED_PER_RECORD, GIFT, PLANT = 3, 6, 3
DAILY_CAP = 5                      # rewarded records per day (2026-11-15: 10 -> 5)
PLOTS, DAYS_TO_HARVEST = 3, 9
YARD_OPEN_DAYS = 7                 # yard opens after 7 recorded days (cumulative, 2026-11-10 대표 결정)
ZONES = [60, 120]                  # extra yard zones bought with seeds (2026-11-10 대표 결정: 씨앗으로 삼)

ARCH = {"light": (3, 4), "normal": (5, 10), "heavy": (7, 21), "max": (7, 70), "binge": [2, 35, 17, 16, 11, 3, 9]}


def schedule(days_per_week, recs_per_week):
    """records per weekday (0..6), spread evenly over the recorded days"""
    rec_days = [round(i * 7 / days_per_week) for i in range(days_per_week)]
    out = [0] * 7
    for k in range(recs_per_week):
        out[rec_days[k % days_per_week]] += 1
    return out


def sim(arch, yard_release_day, garden=True, yard_prices=YARD, weeks=60, zones=None, cap=None):
    zones = list(ZONES if zones is None else zones)
    cap = DAILY_CAP if cap is None else cap
    week = ARCH[arch] if isinstance(ARCH[arch], list) else schedule(*ARCH[arch])
    seeds, records, rec_days = GIFT, 0, 0
    room_left = sorted(ROOM)
    yard_left = sorted(yard_prices.values())
    plot_progress = [0] * PLOTS        # recorded days since planting; -1 = empty
    first_free = True
    log = {"room_done": None, "yard_done": None, "yard_open": None, "owned_w1": None, "owned_w4": None,
           "yard_owned_2w_after_open": None, "garden_spend": 0, "zones": []}
    for day in range(weeks * 7):
        n = week[day % 7]
        if n:
            records += n; rec_days += 1
            seeds += SEED_PER_RECORD * min(n, cap)
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
        yard_open = day >= yard_release_day and rec_days >= YARD_OPEN_DAYS
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
        # zones: bought (in order) once every item on sale is owned — zone items come with later updates
        while yard_open and zones and not room_left and not yard_left and seeds >= zones[0]:
            seeds -= zones.pop(0); log["zones"].append(day)
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
                  f"yard items 2w after open {r['yard_owned_2w_after_open']} | zones {[wk(d) for d in r['zones']]}")
    print("\n== daily cap options (launch user): room done / week-1 owned")
    for cap in (10, 5, 3):
        print(cap, {a: (wk(r["room_done"]), r["owned_w1"]) for a in ARCH for r in [sim(a, 28, cap=cap)]})
    print("\n== zone price options (launch user): weeks when zone 2 / zone 3 become affordable after the yard is full")
    for zs in ([45, 90], [60, 120], [90, 180], [120, 240]):
        print(zs, {a: [wk(d) for d in sim(a, 28, zones=zs)["zones"]] for a in ARCH})
