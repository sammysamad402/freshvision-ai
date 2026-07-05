"""Auth routes."""
import logging

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth import verify_password, hash_password, create_access_token, get_current_user
from app.core.config import ALLOW_REGISTRATION, DEFAULT_USER_ROLE
from app.core.limiter import limiter
from app.db.database import get_user, create_user, log_audit, UsernameTakenError
from app.models.schemas import Token, UserOut, UserRegister

logger = logging.getLogger("freshvision.routes.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user = await get_user(form_data.username)
    # Always run the hash comparison (even on unknown users) via a dummy hash,
    # so login timing doesn't reveal whether a username exists.
    if not user:
        verify_password(form_data.password, "$2b$12$CwTycUXWue0Thq9StjUM0uJ8s.qNjRJqxNwCpNQFTgqSJf/aY2Vum")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    await log_audit(user["username"], "login")
    return {"access_token": token}


@router.post("/register", response_model=Token, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, payload: UserRegister):
    """
    Create a brand-new account. Every account is private by default: its
    inspections, history, and analytics belong only to it and are never
    visible to other users (only the built-in 'admin' role can see all data).
    """
    if not ALLOW_REGISTRATION:
        raise HTTPException(status_code=403, detail="Self-service sign-up is disabled.")
    try:
        user = await create_user(
            username=payload.username,
            password_hash=hash_password(payload.password),
            role=DEFAULT_USER_ROLE,
        )
    except UsernameTakenError:
        raise HTTPException(status_code=409, detail="That username is already taken.")
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    await log_audit(user["username"], "register")
    logger.info("New account registered: %s", user["username"])
    return {"access_token": token}


@router.get("/me", response_model=UserOut)
async def me(current_user=Depends(get_current_user)):
    return {"username": current_user["username"], "role": current_user["role"]}
