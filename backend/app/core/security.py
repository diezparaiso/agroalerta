import json
import os

from fastapi import Header, HTTPException, status


def _is_production() -> bool:
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def _verify_with_firebase(token: str) -> str | None:
    credentials_json = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
    if not credentials_json:
        return None
    import firebase_admin
    from firebase_admin import auth, credentials

    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(json.loads(credentials_json)))
    try:
        return auth.verify_id_token(token)['uid']
    except Exception as exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token Firebase invalido') from exception


def optional_bearer_token(authorization: str | None = Header(default=None)) -> str | None:
    if authorization is None:
        if _is_production():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Autenticacion requerida')
        return None
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token Bearer invalido')
    verified_uid = _verify_with_firebase(token)
    if verified_uid:
        return verified_uid
    if _is_production():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Firebase Admin no esta configurado')
    return token
