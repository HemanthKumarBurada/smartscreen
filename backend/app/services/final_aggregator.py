"""
Final Score Aggregator
final = (score1 * w1 + score2 * w2 + score3 * w3) / (w1 + w2 + w3)
"""

def compute_final_score(s1, s2, s3, s4, w1, w2, w3, w4, qualifying_score, malpractice_flag):
    total_weight = w1 + w2 + w3 + w4 or 100
    final = (s1*w1 + s2*w2 + s3*w3 + s4*w4) / total_weight
    if malpractice_flag:
        final = min(final, 20.0)
    return {
        "score1": round(s1,2), "score2": round(s2,2),
        "score3": round(s3,2), "score4": round(s4,2),
        "final_score": round(final,2),
        "is_qualified": final >= qualifying_score,
        "malpractice_flag": malpractice_flag
    }