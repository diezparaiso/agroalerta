from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.schemas import DiseaseRisk, RiskSnapshot

RiskAlertReason = Literal[
    "first_risk",
    "risk_increase",
    "risk_decrease",
    "unchanged",
]


@dataclass(frozen=True)
class RiskAlertDecision:
    should_create: bool
    should_notify: bool
    reason_code: RiskAlertReason
    alert_type: str
    message: str


_LEVEL_ORDER = {"bajo": 0, "medio": 1, "alto": 2}


def decide_risk_alert(
    risk: DiseaseRisk,
    previous: RiskSnapshot | None,
    minimum_alert_level: str = "medio",
) -> RiskAlertDecision:
    """Decide si un nuevo cálculo de riesgo debe convertirse en una alerta.

    El motor separa el cálculo agronómico de la generación de eventos.
    No envía notificaciones: solo devuelve una decisión determinista.
    """
    minimum_level = _LEVEL_ORDER.get(minimum_alert_level)
    current_level = _LEVEL_ORDER.get(risk.risk_level)
    if minimum_level is None or current_level is None:
        raise ValueError("Nivel de alerta no válido")

    if previous is None:
        if current_level >= minimum_level:
            return RiskAlertDecision(
                should_create=True,
                should_notify=True,
                reason_code="first_risk",
                alert_type="riesgo_inicial",
                message=_message_for_level(risk),
            )
        return RiskAlertDecision(False, False, "unchanged", "sin_alerta", "")

    previous_level = _LEVEL_ORDER.get(previous.risk_level)
    if previous_level is None:
        raise ValueError("Nivel de riesgo anterior no válido")

    if current_level > previous_level and current_level >= minimum_level:
        return RiskAlertDecision(
            should_create=True,
            should_notify=True,
            reason_code="risk_increase",
            alert_type="riesgo_incrementado",
            message=_message_for_level(risk),
        )

    if current_level < previous_level:
        return RiskAlertDecision(
            should_create=False,
            should_notify=False,
            reason_code="risk_decrease",
            alert_type="riesgo_reducido",
            message="El nivel de riesgo ha disminuido.",
        )

    return RiskAlertDecision(
        should_create=False,
        should_notify=False,
        reason_code="unchanged",
        alert_type="sin_cambio",
        message="El nivel de riesgo se mantiene.",
    )


def _message_for_level(risk: DiseaseRisk) -> str:
    labels = {"bajo": "bajo", "medio": "medio", "alto": "alto"}
    disease_labels = {"repilo": "repilo", "mildiu": "mildiu"}
    disease = disease_labels.get(risk.disease_code, risk.disease_code)
    level = labels[risk.risk_level]
    return f"Riesgo {level} de {disease} detectado en la parcela."
