from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from app.schemas import Alert

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PushDeliveryResult:
    status: str
    tokens: int
    sent: int
    failed: int


def send_alert_push(alert: Alert, tokens: list[str]) -> PushDeliveryResult:
    """Envía una alerta por FCM cuando Firebase Admin está configurado.

    La ausencia de credenciales no rompe el cálculo ni la persistencia de alertas.
    """
    if not tokens:
        return PushDeliveryResult("no_tokens", 0, 0, 0)

    credential_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not credential_json:
        return PushDeliveryResult("disabled", len(tokens), 0, 0)

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            credential = credentials.Certificate(json.loads(credential_json))
            firebase_admin.initialize_app(credential)

        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=f"AgroAlerta · {alert.risk_level.capitalize()}",
                body=alert.message,
            ),
            data={
                "alert_id": str(alert.id),
                "parcel_id": alert.parcel_id,
                "disease_code": alert.disease_code,
                "risk_level": alert.risk_level,
            },
            tokens=tokens,
        )
        response = messaging.send_each_for_multicast(message)
        sent = response.success_count
        failed = response.failure_count
        return PushDeliveryResult("sent", len(tokens), sent, failed)
    except Exception:
        logger.exception("Error enviando alerta FCM %s", alert.id)
        return PushDeliveryResult("error", len(tokens), 0, len(tokens))
