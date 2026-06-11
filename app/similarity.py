import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session
from app.models import Person, PersonFeature
from app.features import get_or_compute_features, FEATURE_NAMES


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _group_vector(person_ids: list, all_vectors: dict) -> np.ndarray:
    vecs = [np.array(all_vectors[pid]) for pid in person_ids if pid in all_vectors]
    if not vecs:
        return np.zeros(len(FEATURE_NAMES))
    return np.mean(vecs, axis=0)


def find_similar_groups(db: Session, query_ids: list, n_clusters: int = 80, top_k: int = 10) -> list:
    all_persons = db.query(Person).all()
    all_ids = [p.id for p in all_persons]

    # Load all feature vectors
    all_vectors = {}
    for pid in all_ids:
        vec = get_or_compute_features(db, pid)
        all_vectors[pid] = vec

    if not all_vectors:
        return []

    ids_array = list(all_vectors.keys())
    matrix = np.array([all_vectors[pid] for pid in ids_array])

    # Normalize
    scaler = StandardScaler()
    matrix_scaled = scaler.fit_transform(matrix)

    # Cluster
    k = min(n_clusters, len(ids_array) // 2)
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(matrix_scaled)

    # Build clusters: {cluster_id -> [person_ids]}
    clusters = {}
    for idx, label in enumerate(labels):
        clusters.setdefault(int(label), []).append(ids_array[idx])

    # Query group vector (in scaled space)
    query_vec_raw = _group_vector(query_ids, all_vectors)
    query_vec_scaled = scaler.transform([query_vec_raw])[0]

    # Score each cluster
    results = []
    for cluster_id, members in clusters.items():
        # Skip clusters that are identical to query group
        if set(members) == set(query_ids):
            continue
        centroid = kmeans.cluster_centers_[cluster_id]
        sim = _cosine_similarity(query_vec_scaled, centroid)

        # Build raw centroid summary (inverse transform for readability)
        centroid_raw = scaler.inverse_transform([centroid])[0]
        profile_summary = {FEATURE_NAMES[i]: round(float(centroid_raw[i]), 3) for i in range(len(FEATURE_NAMES))}

        results.append({
            "similarity": sim,
            "members": members,
            "profile_summary": profile_summary,
        })

    results.sort(key=lambda x: x["similarity"], reverse=True)

    return [
        {
            "rank": i + 1,
            "similarity": round(r["similarity"], 4),
            "members": r["members"],
            "size": len(r["members"]),
            "profile_summary": r["profile_summary"],
        }
        for i, r in enumerate(results[:top_k])
    ]
