import json
import os
import time


class FcmDispatcher:
    def __init__(self) -> None:
        self._messaging = None
        self._consecutive_failures = 0
        self._opened_until = 0.0
        credentials_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
        if credentials_json:
            import firebase_admin
            from firebase_admin import credentials, messaging

            if not firebase_admin._apps:
                firebase_admin.initialize_app(credentials.Certificate(json.loads(credentials_json)))
            self._messaging = messaging

    def send_risk_alert(self, token: str, disease: str, parcel: str, level: str) -> str | None:
        if self._messaging is None:
            return None
        if time.time() < self._opened_until:
            return None
        message = self._messaging.Message(
            notification=self._messaging.Notification(
                title=f'Riesgo {level}: {disease}',
                body=f'Revisa la parcela {parcel}',
            ),
            token=token,
            data={'disease': disease, 'level': level, 'parcel': parcel},
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                result = self._messaging.send(message)
                self._consecutive_failures = 0
                return result
            except Exception as error:
                last_error = error
                self._consecutive_failures += 1
                if attempt < 2:
                    time.sleep(2**attempt)
        if self._consecutive_failures >= 3:
            self._opened_until = time.time() + 60
        if last_error is not None:
            raise last_error
        return None

    def send_risk_alert_to_tokens(self, tokens: list[str], disease: str, parcel: str, level: str) -> tuple[int, list[str]]:
        sent = 0
        failed: list[str] = []
        for token in tokens:
            try:
                if self.send_risk_alert(token, disease, parcel, level):
                    sent += 1
            except Exception:
                failed.append(token)
        return sent, failed
