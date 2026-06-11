"""Generate mock data for development/demo purposes."""
import random
from datetime import datetime, timedelta
from faker import Faker
from sqlalchemy.orm import Session
from app.database import engine, SessionLocal
from app.models import Base, Person, CellularEvent, LocationEvent, CyberEvent

fake = Faker("he_IL")
random.seed(42)

REGIONS = ["צפון", "מרכז", "דרום", "ירושלים", "חיפה"]
PROTOCOLS = ["HTTP", "HTTPS", "DNS", "FTP"]
CALL_TYPES = ["inbound", "outbound"]
DOMAINS = [
    "google.com", "facebook.com", "youtube.com", "ynet.co.il",
    "walla.co.il", "instagram.com", "twitter.com", "amazon.com",
    "gov.il", "mail.com", "dropbox.com", "zoom.us",
]

# Geographic clusters (lat, lon center, std)
GEO_CLUSTERS = [
    (32.08, 34.78, 0.05),   # Tel Aviv area
    (31.77, 35.21, 0.05),   # Jerusalem area
    (32.82, 34.99, 0.05),   # Haifa area
    (31.25, 34.79, 0.05),   # Beer Sheva area
    (32.32, 34.86, 0.05),   # Sharon area
]


def rand_date(days_back=90):
    return datetime.utcnow() - timedelta(days=random.randint(0, days_back), hours=random.randint(0, 23))


def seed(n_persons=300):
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    # Clear existing data
    for model in [CyberEvent, LocationEvent, CellularEvent, Person]:
        db.query(model).delete()
    db.commit()

    persons = []
    for _ in range(n_persons):
        p = Person(
            name=fake.name(),
            age=random.randint(18, 75),
            region=random.choice(REGIONS),
        )
        db.add(p)
        persons.append(p)
    db.commit()

    for p in persons:
        geo = random.choice(GEO_CLUSTERS)
        lat_center, lon_center, geo_std = geo

        # Behavioral archetype: determines intensity
        archetype = random.choice(["high_comm", "low_comm", "traveler", "cyber_heavy", "night_owl"])

        n_cellular = random.randint(50, 200) if archetype == "high_comm" else random.randint(5, 50)
        n_location = random.randint(100, 400) if archetype == "traveler" else random.randint(20, 100)
        n_cyber = random.randint(150, 500) if archetype == "cyber_heavy" else random.randint(20, 100)
        night_bias = archetype == "night_owl"

        contacts = random.sample(range(1, n_persons + 1), min(15, n_persons))

        for _ in range(n_cellular):
            hour = random.randint(22, 23) if (night_bias and random.random() < 0.6) else random.randint(7, 21)
            ts = datetime.utcnow() - timedelta(days=random.randint(0, 90), hours=hour, minutes=random.randint(0, 59))
            db.add(CellularEvent(
                person_id=p.id,
                timestamp=ts,
                call_duration_sec=random.uniform(10, 600) if random.random() > 0.3 else 0,
                sms_count=random.randint(0, 5),
                contact_id=random.choice(contacts),
                call_type=random.choice(CALL_TYPES),
            ))

        for _ in range(n_location):
            radius = geo_std * 3 if archetype == "traveler" else geo_std
            db.add(LocationEvent(
                person_id=p.id,
                timestamp=rand_date(),
                lat=lat_center + random.gauss(0, radius),
                lon=lon_center + random.gauss(0, radius),
                accuracy=random.uniform(5, 50),
            ))

        for _ in range(n_cyber):
            ts = rand_date()
            db.add(CyberEvent(
                person_id=p.id,
                timestamp=ts,
                domain=random.choice(DOMAINS),
                ip_address=fake.ipv4(),
                data_volume_kb=random.uniform(1, 5000),
                protocol=random.choice(PROTOCOLS),
            ))

    db.commit()
    db.close()
    print(f"Seeded {n_persons} persons with cellular, location, and cyber data.")


if __name__ == "__main__":
    seed()
