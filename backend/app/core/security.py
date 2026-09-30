import json
import os

from fastapi import Header, HTTPException, status


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() == "production"


def _verify_with_firebase(token: str) -> str:
    """Return a verified Firebase UID; never treat an unverified token as an identity."""
    credentials_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not credentials_json:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase Admin no está configurado",
        )

    try:
        import firebase_admin
        from firebase_admin import auth, credentials

        if not firebase_admin._apps:
            firebase_admin.initialize_app(
                credentials.Certificate(json.loads(credentials_json))
            )
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        if not isinstance(uid, str) or not uid:
            raise ValueError("Firebase token has no uid")
        return uid
    except HTTPException:
        raise
    except Exception as exception:
        # Configuration errors are service failures; invalid credentials are 401.
        if isinstance(exception, (json.JSONDecodeError, ValueError, ImportError, KeyError)):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Configuración de Firebase Admin inválida",
            ) from exception
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Firebase inválido",
        ) from exception


def optional_bearer_token(authorization: str | None = Header(default=None)) -> str | None:
    """Resolve the request identity.

    Anonymous/local token identities are intentionally supported only outside
    production to keep local development convenient. Production must validate
    every supplied bearer token with Firebase Admin.
    """
    production = _is_production()
    if authorization is None:
        if production:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticación requerida",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None

    scheme, separator, token = authorization.partition(" ")
    token = token.strip()
    if (
        not separator
        or scheme.lower() != "bearer"
        or not token
        or any(character.isspace() for character in token)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Bearer inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if production:
        return _verify_with_firebase(token)

    # Development-only identity shortcut. Never enable this in production.
    verified_uid = None
    if os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
        verified_uid = _verify_with_firebase(token)
    return verified_uid or token
