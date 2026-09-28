"""Reglas de dominio para trazabilidad de tratamientos dentro de una campaña."""


def build_treatment_summary(campaign, treatments: list, decisions: list) -> dict:
    products = {item.product_name.strip().lower() for item in treatments if item.product_name.strip()}
    days = sum(item.safety_period_days or 0 for item in treatments)
    linked_decisions = {
        item.disease_code
        for item in treatments
        if item.disease_code
    } & {
        item.get("disease_code")
        for item in decisions
        if item.get("disease_code")
    }
    return {
        "campaign": campaign,
        "treatment_count": len(treatments),
        "distinct_product_count": len(products),
        "treatment_days": days,
        "linked_decision_count": len(linked_decisions),
        "latest_treatment_at": max((item.applied_at for item in treatments), default=None),
    }
