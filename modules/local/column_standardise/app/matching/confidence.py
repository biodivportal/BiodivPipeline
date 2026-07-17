"""
Confidence scoring and manual review logic.

This module estimates how reliable a mapping prediction is based on the score
difference between the best and second-best candidate, the semantic score and
additional supporting signals from string matching, profiling and heuristics.

It also determines whether a prediction should be flagged for manual review.
"""

def compute_confidence(top1, top2):
    """
    Compute a confidence score for the highest-ranked mapping candidate.

    The score combines three signals: the margin between the best and
    second-best candidate, the semantic similarity of the best candidate and
    additional support from string matching, profiling and heuristic rules.

    Args:
        top1: Highest-ranked candidate row from the mapping result.
        top2: Second-highest-ranked candidate row from the mapping result.

    Returns:
        A confidence score between 0.0 and 1.0.
    """
    margin = top1["final_score"] - top2["final_score"]
    margin_component = min(margin / 0.10, 1.0)

    # semantic score below 0.7 are treated as weak evidence
    semantic_component = min(
        max((top1["semantic_score"] - 0.70) / 0.20, 0.0),
        1.0,
    )

    # additional supporting signals from string matching, profiling and heuristics
    support_component = 0.0

    if top1["surface_string_score"] >= 0.75:
        support_component += 0.15
    if top1["term_string_score"] >= 0.75:
        support_component += 0.15
    if top1["profile_boost"] > 0:
        support_component += 0.10
    if top1["heuristic_bonus"] > 0:
        support_component += 0.10

    # margin receives the highest weight because threshold evaluation showed
    # that it separates correct and incorrect mappings best
    confidence = (
        0.55 * margin_component
        + 0.30 * semantic_component
        + 0.15 * min(support_component, 1.0)
    )

    return round(min(confidence, 1.0), 3)


def get_review_reasons(margin, confidence_score):
    """
    Determine why a mapping prediction should be reviewed manually.

    Args:
        margin: Score difference between the best and second-best candidate.
        confidence_score: Confidence score of the best candidate.

    Returns:
        A list of reason labels. The list is empty if no manual review is needed.
    """
    reasons = []
    if margin < 0.04:
        # small margins indicate ambiguity between top candidates
        reasons.append("small_margin")
    if confidence_score < 0.40:
        # low confidence scores indicate overall uncertainty in the prediction
        reasons.append("low_confidence")

    return reasons


def manual_review_flag(margin, confidence_score):
    """
    Decide whether a mapping prediction should be flagged for manual review.

    Args:
        margin: Score difference between the best and second-best candidate.
        confidence_score: Confidence score of the best candidate.

    Returns:
        True if at least one review reason exists, otherwise False.
    """
    return len(get_review_reasons(margin, confidence_score)) > 0
