import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from features import group_profile, FEATURE_NAMES


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def find_similar_groups(feature_df: pd.DataFrame,
                        query_ids: list,
                        n_clusters: int = 80,
                        top_k: int = 10) -> list[dict]:
    scaler = StandardScaler()
    X = scaler.fit_transform(feature_df.values)
    feat_scaled = pd.DataFrame(X, index=feature_df.index, columns=feature_df.columns)

    n_clusters = min(n_clusters, len(feature_df) // 3)
    n_clusters = max(n_clusters, 2)

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    cluster_series = pd.Series(labels, index=feature_df.index)

    query_vec = group_profile(feat_scaled, query_ids)

    results = []
    for cid in range(n_clusters):
        members = cluster_series[cluster_series == cid].index.tolist()
        if not members:
            continue
        candidate_vec = group_profile(feat_scaled, members)
        sim = cosine_sim(query_vec, candidate_vec)
        raw_profile = group_profile(feature_df, members)
        results.append({
            "cluster_id": int(cid),
            "members": members,
            "size": len(members),
            "similarity": round(sim, 4),
            "profile": {name: round(float(v), 3) for name, v in zip(FEATURE_NAMES, raw_profile)},
        })

    results.sort(key=lambda r: r["similarity"], reverse=True)
    return results[:top_k]
