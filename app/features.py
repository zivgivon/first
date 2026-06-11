import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import CellularEvent, LocationEvent, CyberEvent, PersonFeature

FEATURE_NAMES = [
    "avg_call_duration",
    "calls_per_day",
    "unique_contacts",
    "night_activity_ratio",
    "sms_ratio",
    "movement_radius",
    "unique_locations",
    "travel_frequency",
    "home_lat_norm",
    "home_lon_norm",
    "unique_domains_per_day",
    "avg_data_volume_kb",
    "https_ratio",
    "cyber_active_hours",
    "cyber_events_per_day",
]


def _cellular_features(db: Session, person_id: int) -> dict:
    rows = db.query(CellularEvent).filter(CellularEvent.person_id == person_id).all()
    if not rows:
        return {k: 0.0 for k in FEATURE_NAMES[:5]}
    df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "call_duration_sec": r.call_duration_sec or 0,
        "sms_count": r.sms_count or 0,
        "contact_id": r.contact_id,
        "call_type": r.call_type,
    } for r in rows])
    df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
    span_days = max((df["timestamp"].max() - df["timestamp"].min()).days, 1)
    total = len(df)
    calls = df[df["call_duration_sec"] > 0]
    return {
        "avg_call_duration": calls["call_duration_sec"].mean() if len(calls) else 0.0,
        "calls_per_day": total / span_days,
        "unique_contacts": df["contact_id"].nunique(),
        "night_activity_ratio": ((df["hour"] >= 22) | (df["hour"] <= 5)).mean(),
        "sms_ratio": (df["sms_count"] > 0).mean(),
    }


def _location_features(db: Session, person_id: int) -> dict:
    rows = db.query(LocationEvent).filter(LocationEvent.person_id == person_id).all()
    if not rows:
        return {k: 0.0 for k in ["movement_radius", "unique_locations", "travel_frequency", "home_lat_norm", "home_lon_norm"]}
    lats = np.array([r.lat for r in rows])
    lons = np.array([r.lon for r in rows])
    timestamps = [r.timestamp for r in rows]
    span_days = max((max(timestamps) - min(timestamps)).days, 1)
    lat_bins = np.round(lats, 2)
    lon_bins = np.round(lons, 2)
    unique_locs = len(set(zip(lat_bins, lon_bins)))
    return {
        "movement_radius": float(np.std(lats) + np.std(lons)),
        "unique_locations": float(unique_locs),
        "travel_frequency": float(unique_locs / span_days),
        "home_lat_norm": float(np.mean(lats)),
        "home_lon_norm": float(np.mean(lons)),
    }


def _cyber_features(db: Session, person_id: int) -> dict:
    rows = db.query(CyberEvent).filter(CyberEvent.person_id == person_id).all()
    if not rows:
        return {k: 0.0 for k in ["unique_domains_per_day", "avg_data_volume_kb", "https_ratio", "cyber_active_hours", "cyber_events_per_day"]}
    df = pd.DataFrame([{
        "timestamp": r.timestamp,
        "domain": r.domain,
        "data_volume_kb": r.data_volume_kb or 0,
        "protocol": r.protocol,
    } for r in rows])
    df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
    span_days = max((df["timestamp"].max() - df["timestamp"].min()).days, 1)
    return {
        "unique_domains_per_day": df["domain"].nunique() / span_days,
        "avg_data_volume_kb": df["data_volume_kb"].mean(),
        "https_ratio": (df["protocol"].str.upper() == "HTTPS").mean(),
        "cyber_active_hours": float(df["hour"].nunique()),
        "cyber_events_per_day": len(df) / span_days,
    }


def compute_person_features(db: Session, person_id: int) -> list:
    feats = {}
    feats.update(_cellular_features(db, person_id))
    feats.update(_location_features(db, person_id))
    feats.update(_cyber_features(db, person_id))
    return [feats.get(name, 0.0) for name in FEATURE_NAMES]


def get_or_compute_features(db: Session, person_id: int) -> list:
    cached = db.query(PersonFeature).filter(PersonFeature.person_id == person_id).first()
    if cached:
        return cached.feature_vector
    vec = compute_person_features(db, person_id)
    pf = PersonFeature(person_id=person_id, feature_vector=vec, last_computed=datetime.utcnow())
    db.add(pf)
    db.commit()
    return vec


def recompute_all_features(db: Session, person_ids: list):
    db.query(PersonFeature).delete()
    db.commit()
    for pid in person_ids:
        vec = compute_person_features(db, pid)
        pf = PersonFeature(person_id=pid, feature_vector=vec, last_computed=datetime.utcnow())
        db.add(pf)
    db.commit()


def vector_to_summary(vec: list) -> dict:
    return {name: round(val, 3) for name, val in zip(FEATURE_NAMES, vec)}
