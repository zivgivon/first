"""
Generates demo Excel files in the data/ folder.
Run once:  python generate_demo_data.py
"""
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from faker import Faker

fake = Faker("he_IL")
random.seed(42)

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

REGIONS = ["צפון", "מרכז", "דרום", "ירושלים", "חיפה"]
PROTOCOLS = ["HTTP", "HTTPS", "DNS"]
CALL_TYPES = ["inbound", "outbound"]
COMMON_DOMAINS = ["google.com", "facebook.com", "youtube.com", "ynet.co.il", "instagram.com"]
WORK_DOMAINS = ["gov.il", "zoom.us", "dropbox.com", "slack.com", "teams.microsoft.com"]
DARK_DOMAINS = ["protonmail.com", "signal.org", "duckduckgo.com", "privatebin.net"]
GEO = {
    "tel_aviv":   (32.08, 34.78, 0.04),
    "jerusalem":  (31.77, 35.21, 0.04),
    "haifa":      (32.82, 34.99, 0.04),
    "beer_sheva": (31.25, 34.79, 0.04),
    "sharon":     (32.32, 34.86, 0.04),
}

PLANTED = {
    "A": {"label": "לוחמי לילה",  "size": 6, "region": "מרכז"},
    "B": {"label": "נוודים",      "size": 7, "region": "צפון"},
    "C": {"label": "רשת חברתית", "size": 6, "region": "מרכז"},
    "D": {"label": "סייבר כבד",  "size": 5, "region": "מרכז"},
    "E": {"label": "שקטים",      "size": 7, "region": "ירושלים"},
    "F": {"label": "צפון פעיל",  "size": 6, "region": "חיפה"},
}
N_NOISE = 250


def rand_ts(days=90, hour=None):
    h = hour if hour is not None else random.randint(0, 23)
    return datetime.utcnow() - timedelta(
        days=random.randint(0, days), hours=h, minutes=random.randint(0, 59)
    )


persons_rows, cel_rows, loc_rows, cyb_rows = [], [], [], []
group_ids: dict[str, list[int]] = {g: [] for g in PLANTED}
pid_counter = 1


def add_person(region):
    global pid_counter
    pid = pid_counter
    pid_counter += 1
    persons_rows.append({"id": pid, "name": fake.name(), "age": random.randint(18, 70), "region": region})
    return pid


def add_cel(pid, n, night_bias=False, many_contacts=False, long_calls=False, n_persons=300):
    contacts = random.sample(range(1, n_persons + 1), min(40 if many_contacts else 8, n_persons))
    for _ in range(n):
        if night_bias:
            hour = random.choice([22, 23, 0, 1, 2, 3]) if random.random() < 0.75 else random.randint(8, 21)
        else:
            hour = random.randint(8, 21)
        cel_rows.append({
            "person_id": pid,
            "timestamp": rand_ts(hour=hour),
            "call_duration_sec": random.uniform(120, 900) if long_calls else random.uniform(5, 300),
            "sms_count": random.randint(0, 3),
            "contact_id": random.choice(contacts),
            "call_type": random.choice(CALL_TYPES),
        })


def add_loc(pid, n, geo_key="tel_aviv", wide=False):
    lat_c, lon_c, std = GEO[geo_key]
    r = std * 6 if wide else std
    for _ in range(n):
        loc_rows.append({"person_id": pid, "timestamp": rand_ts(),
                         "lat": lat_c + random.gauss(0, r), "lon": lon_c + random.gauss(0, r),
                         "accuracy": random.uniform(5, 30)})


def add_cyb(pid, n, heavy=False, encrypted=False, pool=None):
    pool = pool or (DARK_DOMAINS if encrypted else COMMON_DOMAINS)
    for _ in range(n):
        cyb_rows.append({"person_id": pid, "timestamp": rand_ts(),
                         "domain": random.choice(pool),
                         "ip_address": fake.ipv4(),
                         "data_volume_kb": random.uniform(500, 8000) if heavy else random.uniform(1, 500),
                         "protocol": "HTTPS" if encrypted else random.choice(["HTTP", "HTTPS", "HTTPS", "DNS"])})


total_planted = sum(g["size"] for g in PLANTED.values())
n_persons = total_planted + N_NOISE

for gid, info in PLANTED.items():
    for _ in range(info["size"]):
        pid = add_person(info["region"])
        group_ids[gid].append(pid)
        if gid == "A":
            add_cel(pid, random.randint(120, 160), night_bias=True, n_persons=n_persons)
            add_loc(pid, random.randint(25, 40), "tel_aviv")
            add_cyb(pid, random.randint(80, 120), encrypted=True, pool=DARK_DOMAINS)
        elif gid == "B":
            add_cel(pid, random.randint(30, 60), n_persons=n_persons)
            add_loc(pid, random.randint(350, 500), random.choice(list(GEO)), wide=True)
            add_cyb(pid, random.randint(30, 60))
        elif gid == "C":
            add_cel(pid, random.randint(200, 280), many_contacts=True, long_calls=True, n_persons=n_persons)
            add_loc(pid, random.randint(40, 70), "tel_aviv")
            add_cyb(pid, random.randint(50, 90), pool=COMMON_DOMAINS)
        elif gid == "D":
            add_cel(pid, random.randint(15, 30), n_persons=n_persons)
            add_loc(pid, random.randint(20, 40), "tel_aviv")
            add_cyb(pid, random.randint(400, 600), heavy=True, encrypted=True,
                    pool=COMMON_DOMAINS + WORK_DOMAINS + DARK_DOMAINS)
        elif gid == "E":
            add_cel(pid, random.randint(5, 15), n_persons=n_persons)
            add_loc(pid, random.randint(10, 20), "jerusalem")
            add_cyb(pid, random.randint(5, 15))
        elif gid == "F":
            add_cel(pid, random.randint(70, 110), n_persons=n_persons)
            add_loc(pid, random.randint(80, 130), "haifa")
            add_cyb(pid, random.randint(80, 130), pool=WORK_DOMAINS)

for _ in range(N_NOISE):
    pid = add_person(random.choice(REGIONS))
    arch = random.choice(["high_comm", "low_comm", "traveler", "cyber_heavy", "night_owl", "normal"])
    geo = random.choice(list(GEO))
    cel_n = {"high_comm": (80, 180), "low_comm": (5, 30), "traveler": (20, 60),
             "cyber_heavy": (10, 40), "night_owl": (40, 90), "normal": (30, 80)}[arch]
    loc_n = {"high_comm": (30, 80), "low_comm": (15, 40), "traveler": (200, 380),
             "cyber_heavy": (15, 40), "night_owl": (20, 60), "normal": (40, 100)}[arch]
    cyb_n = {"high_comm": (20, 70), "low_comm": (10, 30), "traveler": (20, 60),
             "cyber_heavy": (200, 450), "night_owl": (30, 80), "normal": (40, 120)}[arch]
    add_cel(pid, random.randint(*cel_n), night_bias=(arch == "night_owl"), n_persons=n_persons)
    add_loc(pid, random.randint(*loc_n), geo, wide=(arch == "traveler"))
    add_cyb(pid, random.randint(*cyb_n), heavy=(arch == "cyber_heavy"))

pd.DataFrame(persons_rows).to_excel(DATA_DIR / "persons.xlsx", index=False)
pd.DataFrame(cel_rows).to_excel(DATA_DIR / "cellular.xlsx", index=False)
pd.DataFrame(loc_rows).to_excel(DATA_DIR / "location.xlsx", index=False)
pd.DataFrame(cyb_rows).to_excel(DATA_DIR / "cyber.xlsx", index=False)

print(f"Generated {n_persons} persons, {len(cel_rows)} cellular events, "
      f"{len(loc_rows)} location events, {len(cyb_rows)} cyber events")
print("\nPlanted groups:")
for gid, info in PLANTED.items():
    ids = ", ".join(str(i) for i in group_ids[gid])
    print(f"  Group {gid} ({info['label']}): {ids}")
