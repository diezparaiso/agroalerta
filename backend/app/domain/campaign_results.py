from app.schemas import CampaignResult, CropCampaign


def build_campaign_result(campaign: CropCampaign, result_id: str, owner_id: str, payload: dict, created_at) -> CampaignResult:
    yield_kg_ha = payload["harvested_quantity_kg"] / payload["productive_area_ha"]
    target = campaign.target_yield_t_ha * 1000 if campaign.target_yield_t_ha is not None else None
    deviation = ((yield_kg_ha - target) / target) * 100 if target else None
    return CampaignResult(
        id=result_id,
        owner_id=owner_id,
        created_at=created_at,
        yield_kg_ha=round(yield_kg_ha, 3),
        target_yield_kg_ha=round(target, 3) if target is not None else None,
        target_deviation_pct=round(deviation, 2) if deviation is not None else None,
        **payload,
    )


def build_results_summary(campaign: CropCampaign, results: list[CampaignResult], activities: list, decisions: list) -> dict:
    total_kg = sum(item.harvested_quantity_kg for item in results)
    marketable_kg = sum(item.marketable_quantity_kg or 0 for item in results)
    area = max((item.productive_area_ha for item in results), default=0)
    yield_kg_ha = total_kg / area if area else None
    target = campaign.target_yield_t_ha * 1000 if campaign.target_yield_t_ha is not None else None
    deviation = ((yield_kg_ha - target) / target) * 100 if target and yield_kg_ha is not None else None
    scoped = [a for a in activities if a.occurred_at >= campaign.started_at and (campaign.ended_at is None or a.occurred_at <= campaign.ended_at)]
    return {
        "campaign": campaign,
        "result_count": len(results),
        "harvested_quantity_kg": round(total_kg, 3),
        "marketable_quantity_kg": round(marketable_kg, 3),
        "productive_area_ha": round(area, 4),
        "yield_kg_ha": round(yield_kg_ha, 3) if yield_kg_ha is not None else None,
        "target_yield_kg_ha": round(target, 3) if target is not None else None,
        "target_deviation_pct": round(deviation, 2) if deviation is not None else None,
        "latest_harvest_at": max((item.harvested_at for item in results), default=None),
        "activity_count": len(scoped),
        "treatment_count": sum(a.activity_type == "treatment" for a in scoped),
        "irrigation_count": sum(a.activity_type == "irrigation" for a in scoped),
        "decision_count": len(decisions),
    }
