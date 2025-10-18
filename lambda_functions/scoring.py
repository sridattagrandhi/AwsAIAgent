# lambda_functions/scoring.py
def compute_campaign_score(fit, intent, penalties=0):
    try:
        fit = float(fit)
        intent = float(intent)
        penalties = float(penalties)
        score = (fit * 0.6) + (intent * 0.4) - penalties
        return round(max(0, min(100, score)), 2)
    except Exception:
        return 0.0
