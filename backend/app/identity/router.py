"""Authentication HTTP endpoints only; dashboard/domain routes arrive later."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_tenant, get_current_user, get_db
from app.core.config import settings
from app.identity.models import User
from app.identity.schemas import CurrentUserResponse, LoginRequest, RegisterRequest, TokenResponse
from app.identity.service import AuthenticationError, DuplicateEmailError, login_user, register_user, revoke_refresh_token, rotate_refresh_token
from app.tenancy.models import Tenant


router = APIRouter(prefix="/api/auth", tags=["Authentication"])
REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    production = settings.environment.lower() == "production"
    response.set_cookie(
        REFRESH_COOKIE, raw_token, httponly=True, secure=production,
        samesite="none" if production else "lax", path="/api/auth", max_age=settings.refresh_token_expire_days * 86400,
    )


def _token_response(access_token: str) -> TokenResponse:
    return TokenResponse(access_token=access_token, expires_in=settings.access_token_expire_minutes * 60)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, response: Response, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        _, _, access_token, refresh_token = await register_user(session, **payload.model_dump())
    except DuplicateEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    _set_refresh_cookie(response, refresh_token)
    return _token_response(access_token)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    try:
        _, _, access_token, refresh_token = await login_user(session, **payload.model_dump())
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.") from exc
    _set_refresh_cookie(response, refresh_token)
    return _token_response(access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> TokenResponse:
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is required.")
    try:
        _, _, access_token, replacement = await rotate_refresh_token(session, raw_token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token.") from exc
    _set_refresh_cookie(response, replacement)
    return _token_response(access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, session: AsyncSession = Depends(get_db)) -> Response:
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if raw_token:
        await revoke_refresh_token(session, raw_token)
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth", httponly=True, secure=settings.environment.lower() == "production")
    return response


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: User = Depends(get_current_user), tenant: Tenant = Depends(get_current_tenant)) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, email=user.email, display_name=user.display_name, tenant_id=tenant.id, tenant_name=tenant.name)
