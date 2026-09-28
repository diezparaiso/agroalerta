from app.schemas import CropCampaign


_RISK_ORDER = {"ninguno": 0, "bajo": 1, "medio": 2, "alto": 3}


def _progress(status: str) -> str:
    return {"planned": "planificada", "active": "en_curso", "closed": "cerrada", "cancelled": "cancelada"}[status]


def build_campaign_summary(campaign: CropCampaign, activities: list, risks: list, decisions: list | None = None) -> dict:
    scoped = [
        activity for activity in activities
        if activity.occurred_at >= campaign.started_at
        and (campaign.ended_at is None or activity.occurred_at <= campaign.ended_at)
    ]
    irrigation = [a for a in scoped if a.activity_type == "irrigation"]
    treatments = [a for a in scoped if a.activity_type == "treatment"]
    observations = [a for a in scoped if a.activity_type == "observation"]
    harvests = [a for a in scoped if a.activity_type == "harvest"]
    highest = "ninguno"
    for risk in risks:
        level = getattr(risk, "risk_level", "ninguno")
        if _RISK_ORDER.get(level, 0) > _RISK_ORDER[highest]:
            highest = level
    latest = max((a.occurred_at for a in scoped), default=None)
    return {
        "campaign": campaign,
        "activity_count": len(scoped),
        "irrigation_count": len(irrigation),
        "irrigation_quantity": round(sum((a.quantity or 0) for a in irrigation), 3),
        "treatment_count": len(treatments),
        "observation_count": len(observations),
        "harvest_count": len(harvests),
        "latest_activity_at": latest,
        "risk_event_count": len(risks),
        "highest_risk": highest,
        "progress": _progress(campaign.status),
    }
