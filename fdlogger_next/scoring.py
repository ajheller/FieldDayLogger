"""Field Day scoring for the rewrite prototype."""


def calculate_score(qsos, qrp=False, alt_power=False):
    """Return total score and base score for active QSOs."""
    base_score = 0
    for qso in qsos:
        if qso.deleted:
            continue
        if qso.mode in {"CW", "DI", "DG", "FT8"}:
            base_score += 2
        else:
            base_score += 1
    multiplier = 5 if qrp and alt_power else 2
    return base_score * multiplier, base_score
