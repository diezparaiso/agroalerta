import json
import os

from fastapi import Header, HTTPException, status


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() == "production"


def _firebase_admin():
    """Initialize Firebase Admin or fail with a service-configuration error."""
    credentials_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not credentials_json:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase Admin no está configurado",
        )
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            firebase_admin.initialize_app(
                credentials.Certificate(json.loads(credentials_json))
            )
        return firebase_admin
    except Exception as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configuración de Firebase Admin inválida",
        ) from exception


def _verify_with_firebase(token: str) -> str:
    """Return a verified Firebase UID; never trust an unverified bearer token."""
    firebase_admin = _firebase_admin()
    try:
        from firebase_admin import auth

        decoded_token = auth.verify_id_token(token)
        uid = decoded_token.get("uid")
        if not isinstance(uid, str) or not uid:
            raise ValueError("Firebase token has no uid")
        return uid
    except Exception as exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Firebase inválido",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exception


def optional_bearer_token(authorization: str | None = Header(default=None)) -> str | None:
    """Resolve identity; the development shortcut must never be used in production."""
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

    # Development-only identity shortcut for local tests and development.
    if os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
        return _verify_with_firebase(token)
    return token
