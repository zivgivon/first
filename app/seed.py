"""
Seed script — populates the DB with mock data including 6 planted groups.

Planted Groups (each group has 5-7 members with very similar behavioral profiles):
  A — "לוחמי לילה"   Night communicators: high night activity, encrypted comms, low movement
  B — "נוודים"       Frequent travelers: very high movement radius, many unique locations
  C — "רשת חברתית"   Social hubs: dozens of unique contacts, high call volume
  D — "סייבר כבד"    Cyber-heavy: high data volume, many domains, mostly HTTPS
  E — "שקטים"        Silent profiles: low activity across all domains
  F — "צפון פעיל"    Northern active: concentrated in Haifa area, medium-high comms

All other persons (~250) are random noise for realistic search conditions.
"""
import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import Base, Person, CellularEvent, LocationEvent, CyberEvent, PersonFeature

fake = Faker("he_IL")
random.seed(42)

REGIONS = ["צפון", "מרכז", "דרום", "ירושלים", "חיפה"]
PROTOCOLS = ["HTTP", "HTTPS", "DNS", "FTP"]
CALL_TYPES = ["inbound", "outbound"]

COMMON_DOMAINS = ["google.com", "facebook.com", "youtube.com", "ynet.co.il", "walla.co.il", "instagram.com"]
WORK_DOMAINS   = ["gov.il", "zoom.us", "dropbox.com", "mail.com", "slack.com", "teams.microsoft.com"]
DARK_DOMAINS   = ["protonmail.com", "signal.org", "tor2web.org", "duckduckgo.com", "privatebin.net"]

GEO_CLUSTERS = {
    "tel_aviv":   (32.08, 34.78, 0.04),
    "jerusalem":  (31.77, 35.21, 0.04),
    "haifa":      (32.82, 34.99, 0.04),
    "beer_sheva": (31.25, 34.79, 0.04),
    "sharon":     (32.32, 34.86, 0.04),
}


def rand_date(days_back=90):
    return datetime.utcnow() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )


# ── helpers ──────────────────────────────────────────────────────────────────

def add_cellular(db, person_id, n, night_bias=False, many_contacts=False, n_persons=300, long_calls=False):
    contacts = random.sample(range(1, n_persons + 1), min(40 if many_contacts else 8, n_persons))
    for _ in range(n):
        if night_bias:
            hour = random.choice([22, 23, 0, 1, 2, 3]) if random.random() < 0.75 else random.randint(8, 21)
        else:
            hour = random.randint(8, 21)
        ts = datetime.utcnow() - timedelta(days=random.randint(0, 90), hours=hour, minutes=random.randint(0, 59))
        db.add(CellularEvent(
            person_id=person_id,
            timestamp=ts,
            call_duration_sec=random.uniform(120, 900) if long_calls else (random.uniform(5, 300) if random.random() > 0.3 else 0),
            sms_count=random.randint(0, 3),
            contact_id=random.choice(contacts),
            call_type=random.choice(CALL_TYPES),
        ))


def add_location(db, person_id, n, geo_key="tel_aviv", wide_travel=False):
    lat_c, lon_c, std = GEO_CLUSTERS[geo_key]
    radius = std * 6 if wide_travel else std
    for _ in range(n):
        db.add(LocationEvent(
            person_id=person_id,
            timestamp=rand_date(),
            lat=lat_c + random.gauss(0, radius),
            lon=lon_c + random.gauss(0, radius),
            accuracy=random.uniform(5, 30),
        ))


def add_cyber(db, person_id, n, heavy=False, encrypted=False, domains_pool=None):
    pool = domains_pool or (DARK_DOMAINS if encrypted else COMMON_DOMAINS)
    for _ in range(n):
        ts = rand_date()
        db.add(CyberEvent(
            person_id=person_id,
            timestamp=ts,
            domain=random.choice(pool),
            ip_address=fake.ipv4(),
            data_volume_kb=random.uniform(500, 8000) if heavy else random.uniform(1, 500),
            protocol="HTTPS" if encrypted else random.choice(["HTTP", "HTTPS", "HTTPS", "DNS"]),
        ))


# ── planted group profiles ────────────────────────────────────────────────────

def plant_group_A(db, person_id, n_persons):
    """לוחמי לילה — Night communicators: night calls, encrypted cyber, low movement."""
    add_cellular(db, person_id, n=random.randint(120, 160), night_bias=True, n_persons=n_persons)
    add_location(db, person_id, n=random.randint(25, 40), geo_key="tel_aviv", wide_travel=False)
    add_cyber(db, person_id, n=random.randint(80, 120), encrypted=True, domains_pool=DARK_DOMAINS)


def plant_group_B(db, person_id, n_persons):
    """נוודים — Frequent travelers: very wide movement, many unique locations."""
    add_cellular(db, person_id, n=random.randint(30, 60), n_persons=n_persons)
    add_location(db, person_id, n=random.randint(350, 500), geo_key=random.choice(list(GEO_CLUSTERS)), wide_travel=True)
    add_cyber(db, person_id, n=random.randint(30, 60))


def plant_group_C(db, person_id, n_persons):
    """רשת חברתית — Social hubs: very many contacts, high call volume, long calls."""
    add_cellular(db, person_id, n=random.randint(200, 280), many_contacts=True, long_calls=True, n_persons=n_persons)
    add_location(db, person_id, n=random.randint(40, 70), geo_key="tel_aviv")
    add_cyber(db, person_id, n=random.randint(50, 90), domains_pool=COMMON_DOMAINS)


def plant_group_D(db, person_id, n_persons):
    """סייבר כבד — Cyber-heavy: massive data, many domains, fully HTTPS."""
    all_domains = COMMON_DOMAINS + WORK_DOMAINS + DARK_DOMAINS
    add_cellular(db, person_id, n=random.randint(15, 30), n_persons=n_persons)
    add_location(db, person_id, n=random.randint(20, 40), geo_key="tel_aviv")
    add_cyber(db, person_id, n=random.randint(400, 600), heavy=True, encrypted=True, domains_pool=all_domains)


def plant_group_E(db, person_id, n_persons):
    """שקטים — Silent: very low activity everywhere."""
    add_cellular(db, person_id, n=random.randint(5, 15), n_persons=n_persons)
    add_location(db, person_id, n=random.randint(10, 20), geo_key="jerusalem")
    add_cyber(db, person_id, n=random.randint(5, 15))


def plant_group_F(db, person_id, n_persons):
    """צפון פעיל — Northern cluster: Haifa-area, medium comms, work domains."""
    add_cellular(db, person_id, n=random.randint(70, 110), n_persons=n_persons)
    add_location(db, person_id, n=random.randint(80, 130), geo_key="haifa", wide_travel=False)
    add_cyber(db, person_id, n=random.randint(80, 130), domains_pool=WORK_DOMAINS)


def random_person_data(db, person_id, n_persons):
    """Background noise: random archetype."""
    archetype = random.choice(["high_comm", "low_comm", "traveler", "cyber_heavy", "night_owl", "normal"])
    geo_key = random.choice(list(GEO_CLUSTERS.keys()))

    n_cel = {"high_comm": (80, 180), "low_comm": (5, 30), "traveler": (20, 60),
             "cyber_heavy": (10, 40), "night_owl": (40, 90), "normal": (30, 80)}[archetype]
    n_loc = {"high_comm": (30, 80), "low_comm": (15, 40), "traveler": (200, 380),
             "cyber_heavy": (15, 40), "night_owl": (20, 60), "normal": (40, 100)}[archetype]
    n_cyb = {"high_comm": (20, 70), "low_comm": (10, 30), "traveler": (20, 60),
             "cyber_heavy": (200, 450), "night_owl": (30, 80), "normal": (40, 120)}[archetype]

    add_cellular(db, person_id, n=random.randint(*n_cel),
                 night_bias=(archetype == "night_owl"), n_persons=n_persons)
    add_location(db, person_id, n=random.randint(*n_loc), geo_key=geo_key,
                 wide_travel=(archetype == "traveler"))
    add_cyber(db, person_id, n=random.randint(*n_cyb),
              heavy=(archetype == "cyber_heavy"))


# ── main seed ─────────────────────────────────────────────────────────────────

PLANTED_GROUPS = {
    "A": {"label": "לוחמי לילה",  "fn": plant_group_A, "size": 6, "region": "מרכז"},
    "B": {"label": "נוודים",      "fn": plant_group_B, "size": 7, "region": "צפון"},
    "C": {"label": "רשת חברתית", "fn": plant_group_C, "size": 6, "region": "מרכז"},
    "D": {"label": "סייבר כבד",  "fn": plant_group_D, "size": 5, "region": "מרכז"},
    "E": {"label": "שקטים",      "fn": plant_group_E, "size": 7, "region": "ירושלים"},
    "F": {"label": "צפון פעיל",  "fn": plant_group_F, "size": 6, "region": "חיפה"},
}

N_NOISE = 250


def seed():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # Clear existing data
    for model in [PersonFeature, CyberEvent, LocationEvent, CellularEvent, Person]:
        db.query(model).delete()
    db.commit()

    total_planted = sum(g["size"] for g in PLANTED_GROUPS.values())
    n_persons = total_planted + N_NOISE

    # ── create all persons ──
    all_persons = []
    group_registry = {}  # group_id -> [person_ids]

    for gid, ginfo in PLANTED_GROUPS.items():
        group_registry[gid] = []
        for i in range(ginfo["size"]):
            p = Person(name=fake.name(), age=random.randint(20, 55), region=ginfo["region"])
            db.add(p)
            all_persons.append((p, gid))

    for _ in range(N_NOISE):
        p = Person(name=fake.name(), age=random.randint(18, 75), region=random.choice(REGIONS))
        db.add(p)
        all_persons.append((p, None))

    db.flush()  # get IDs without committing

    # ── generate events ──
    for p, gid in all_persons:
        if gid is not None:
            group_registry[gid].append(p.id)
            PLANTED_GROUPS[gid]["fn"](db, p.id, n_persons)
        else:
            random_person_data(db, p.id, n_persons)

    db.commit()
    db.close()

    print(f"\n✓ Seeded {n_persons} persons total ({total_planted} planted + {N_NOISE} noise)\n")
    print("═" * 60)
    print(f"{'קבוצה':<6} {'שם':<18} {'גודל':<8} {'IDs'}")
    print("─" * 60)
    for gid, ginfo in PLANTED_GROUPS.items():
        ids_str = ", ".join(str(i) for i in group_registry[gid])
        print(f"  {gid}    {ginfo['label']:<18} {ginfo['size']:<8} {ids_str}")
    print("═" * 60)
    print("\nדוגמאות לחיפוש — הזן חלק מהקבוצה וצפה בתוצאות:")
    for gid, ginfo in PLANTED_GROUPS.items():
        sample = group_registry[gid][:3]
        print(f"  קבוצה {gid} ({ginfo['label']}): {', '.join(str(i) for i in sample)}")
    print()


if __name__ == "__main__":
    seed()
