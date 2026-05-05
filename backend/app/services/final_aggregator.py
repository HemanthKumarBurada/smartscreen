"""
Final Score Aggregator
final = (score1 * w1 + score2 * w2 + score3 * w3) / (w1 + w2 + w3)
"""

def compute_final_score(
    score1: float,
    score2: float,
    score3: float,
    weight1: float,
    weight2: float,
    weight3: float,
    qualifying_score: float = 60.0,
    malpractice_flag: bool = False
) -> dict:
    total_weight = weight1 + weight2 + weight3
    if total_weight == 0:
        total_weight = 100

    final = (score1 * weight1 + score2 * weight2 + score3 * weight3) / total_weight

    # Hard disqualify if malpractice detected
    if malpractice_flag:
        final = min(final, 20.0)

    is_qualified = final >= qualifying_score

    return {
        "score1": round(score1, 2),
        "score2": round(score2, 2),
        "score3": round(score3, 2),
        "weight1": weight1,
        "weight2": weight2,
        "weight3": weight3,
        "final_score": round(final, 2),
        "qualifying_score": qualifying_score,
        "is_qualified": is_qualified,
        "malpractice_flag": malpractice_flag
    }
