import numpy as np
import pandas as pd

FEATURE_NAMES = [
    "avg_call_duration",
    "calls_per_day",
    "unique_contacts",
    "night_activity_ratio",
    "sms_ratio",
    "movement_radius",
    "unique_locations",
    "travel_frequency",
    "home_lat",
    "home_lon",
    "unique_domains_per_day",
    "avg_data_volume_kb",
    "https_ratio",
    "cyber_active_hours",
    "cyber_events_per_day",
]

FEATURE_DESCRIPTIONS = {
    "avg_call_duration": "Avg call duration (sec)",
    "calls_per_day": "Calls per day",
    "unique_contacts": "Unique contacts",
    "night_activity_ratio": "Night activity ratio",
    "sms_ratio": "SMS ratio",
    "movement_radius": "Movement radius (km)",
    "unique_locations": "Unique locations",
    "travel_frequency": "Travel frequency",
    "home_lat": "Home latitude",
    "home_lon": "Home longitude",
    "unique_domains_per_day": "Domains per day",
    "avg_data_volume_kb": "Avg data volume (KB)",
    "https_ratio": "HTTPS ratio",
    "cyber_active_hours": "Cyber active hours",
    "cyber_events_per_day": "Cyber events per day",
}


def _cellular(df_cel: pd.DataFrame, person_ids: list) -> pd.DataFrame:
    rows = []
    for pid in person_ids:
        sub = df_cel[df_cel["person_id"] == pid] if len(df_cel) else pd.DataFrame()
        if len(sub) == 0:
            rows.append([0.0] * 5)
            continue
        calls = sub[sub["call_duration_sec"] > 0]
        avg_dur = calls["call_duration_sec"].mean() if len(calls) else 0.0
        days = max((sub["timestamp"].max() - sub["timestamp"].min()).days, 1)
        calls_per_day = len(sub) / days
        unique_contacts = sub["contact_id"].nunique()
        if "timestamp" in sub.columns:
            sub = sub.copy()
            sub["hour"] = pd.to_datetime(sub["timestamp"]).dt.hour
            night = sub[(sub["hour"] >= 22) | (sub["hour"] <= 4)]
            night_ratio = len(night) / len(sub)
        else:
            night_ratio = 0.0
        total_events = len(sub)
        sms_count = sub["sms_count"].sum() if "sms_count" in sub.columns else 0
        sms_ratio = sms_count / max(total_events, 1)
        rows.append([avg_dur, calls_per_day, unique_contacts, night_ratio, sms_ratio])
    return pd.DataFrame(rows, index=person_ids,
                        columns=["avg_call_duration", "calls_per_day", "unique_contacts",
                                 "night_activity_ratio", "sms_ratio"])


def _location(df_loc: pd.DataFrame, person_ids: list) -> pd.DataFrame:
    rows = []
    for pid in person_ids:
        sub = df_loc[df_loc["person_id"] == pid] if len(df_loc) else pd.DataFrame()
        if len(sub) == 0:
            rows.append([0.0] * 5)
            continue
        lats = sub["lat"].values
        lons = sub["lon"].values
        home_lat = float(np.median(lats))
        home_lon = float(np.median(lons))
        dists = np.sqrt((lats - home_lat) ** 2 + (lons - home_lon) ** 2) * 111
        radius = float(np.percentile(dists, 90))
        grid = (np.round(lats, 2).astype(str) + "," + np.round(lons, 2).astype(str))
        unique_locs = len(set(grid))
        days = max((pd.to_datetime(sub["timestamp"]).max() -
                    pd.to_datetime(sub["timestamp"]).min()).days, 1)
        travel_freq = len(sub) / days
        rows.append([radius, unique_locs, travel_freq, home_lat, home_lon])
    return pd.DataFrame(rows, index=person_ids,
                        columns=["movement_radius", "unique_locations", "travel_frequency",
                                 "home_lat", "home_lon"])


def _cyber(df_cyb: pd.DataFrame, person_ids: list) -> pd.DataFrame:
    rows = []
    for pid in person_ids:
        sub = df_cyb[df_cyb["person_id"] == pid] if len(df_cyb) else pd.DataFrame()
        if len(sub) == 0:
            rows.append([0.0] * 5)
            continue
        days = max((pd.to_datetime(sub["timestamp"]).max() -
                    pd.to_datetime(sub["timestamp"]).min()).days, 1)
        domains_per_day = sub["domain"].nunique() / days
        avg_vol = sub["data_volume_kb"].mean() if "data_volume_kb" in sub.columns else 0.0
        https_ratio = (sub["protocol"].str.upper() == "HTTPS").mean() if "protocol" in sub.columns else 0.0
        sub2 = sub.copy()
        sub2["hour"] = pd.to_datetime(sub2["timestamp"]).dt.hour
        active_hours = sub2["hour"].nunique()
        events_per_day = len(sub) / days
        rows.append([domains_per_day, avg_vol, https_ratio, active_hours, events_per_day])
    return pd.DataFrame(rows, index=person_ids,
                        columns=["unique_domains_per_day", "avg_data_volume_kb", "https_ratio",
                                 "cyber_active_hours", "cyber_events_per_day"])


def compute_all_features(df_persons: pd.DataFrame,
                         df_cel: pd.DataFrame,
                         df_loc: pd.DataFrame,
                         df_cyb: pd.DataFrame) -> pd.DataFrame:
    person_ids = df_persons["id"].tolist()
    f_cel = _cellular(df_cel, person_ids)
    f_loc = _location(df_loc, person_ids)
    f_cyb = _cyber(df_cyb, person_ids)
    combined = pd.concat([f_cel, f_loc, f_cyb], axis=1)
    combined.index.name = "person_id"
    return combined[FEATURE_NAMES]


def group_profile(feature_df: pd.DataFrame, person_ids: list) -> np.ndarray:
    valid = [pid for pid in person_ids if pid in feature_df.index]
    if not valid:
        return np.zeros(len(FEATURE_NAMES))
    return feature_df.loc[valid].mean(axis=0).values


def vector_to_summary(vec: np.ndarray) -> dict:
    return {name: round(float(val), 3) for name, val in zip(FEATURE_NAMES, vec)}
