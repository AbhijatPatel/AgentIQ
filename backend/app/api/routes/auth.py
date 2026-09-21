import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.config.settings import settings
from app.database.models import OtpChallengeModel
from app.database.user_repository import create_user, get_user_by_email
from app.utils.auth import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.utils.otp import (
    OTPAuthError,
    OTPDeliveryError,
    OTPTransientError,
    create_otp,
    hash_otp,
    send_otp_email,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


class RegisterOtpRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    code: Optional[str] = Field(None, min_length=6, max_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class OtpRequest(BaseModel):
    email: EmailStr


class OtpVerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


def _is_in_cooldown(created_at: Optional[datetime], cooldown_seconds: int) -> tuple[bool, int]:
    if not created_at:
        return False, 0
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    elapsed = (now - created_at).total_seconds()
    if 0 <= elapsed < cooldown_seconds:
        remaining = int(cooldown_seconds - elapsed)
        return True, remaining
    return False, 0


@router.post("/register/request-otp")
def request_register_otp(
    request: RegisterOtpRequest,
    db: Session = Depends(get_db),
):
    email = str(request.email).lower().strip()
    existing_user = get_user_by_email(db, email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please sign in.",
        )

    if len(request.password.encode("utf-8")) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    now = datetime.now(timezone.utc)
    latest = (
        db.query(OtpChallengeModel)
        .filter(OtpChallengeModel.email == email)
        .order_by(OtpChallengeModel.created_at.desc())
        .first()
    )
    if latest and latest.created_at:
        in_cooldown, remaining = _is_in_cooldown(latest.created_at, settings.OTP_REQUEST_COOLDOWN_SECONDS)
        if in_cooldown:
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {remaining}s before requesting another verification code",
            )

    code = create_otp()
    challenge = OtpChallengeModel(
        email=email,
        code_hash=hash_otp(code),
        expires_at=now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(challenge)
    db.commit()

    try:
        send_otp_email(email, code, purpose="register")
    except OTPAuthError as exc:
        db.delete(challenge)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email service authentication error. Please contact support.",
        ) from exc
    except (OTPTransientError, OTPDeliveryError) as exc:
        db.delete(challenge)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service is temporarily unavailable. Please try again in a moment.",
        ) from exc
    except Exception as exc:
        db.delete(challenge)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send verification code at this time.",
        ) from exc

    dev_code = code if (not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL) else None
    return {
        "message": f"Verification code sent to {email}",
        "dev_code": dev_code,
    }


@router.post("/register", response_model=AuthResponse)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    email = str(request.email).lower().strip()
    existing_user = get_user_by_email(db, email)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please sign in.",
        )

    if len(request.password.encode("utf-8")) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    # Validate OTP verification code if provided
    if request.code:
        now = datetime.now(timezone.utc)
        challenge = (
            db.query(OtpChallengeModel)
            .filter(
                OtpChallengeModel.email == email,
                OtpChallengeModel.used.is_(False),
            )
            .order_by(OtpChallengeModel.created_at.desc())
            .first()
        )
        expires_at = challenge.expires_at.replace(tzinfo=timezone.utc) if challenge else now
        if not challenge or expires_at < now or not secrets.compare_digest(challenge.code_hash, hash_otp(request.code)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired verification code",
            )

        challenge.used = True

    try:
        password_hash = hash_password(request.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    user = create_user(
        db=db,
        name=request.name.strip(),
        email=email,
        password_hash=password_hash,
    )

    token = create_access_token(
        {"sub": str(user.id)}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
    }



@router.post("/login", response_model=AuthResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, request.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        {"sub": str(user.id)}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
    }


@router.get("/me")
def get_me(
    current_user=Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "created_at": current_user.created_at,
    }


@router.post("/otp/request")
def request_otp(
    request: OtpRequest,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account exists for this email. Please create an account first."
        )

    now = datetime.now(timezone.utc)
    latest = (
        db.query(OtpChallengeModel)
        .filter(OtpChallengeModel.email == str(request.email).lower())
        .order_by(OtpChallengeModel.created_at.desc())
        .first()
    )
    if latest and latest.created_at:
        in_cooldown, remaining = _is_in_cooldown(latest.created_at, settings.OTP_REQUEST_COOLDOWN_SECONDS)
        if in_cooldown:
            raise HTTPException(status_code=429, detail=f"Please wait {remaining}s before requesting another code")

    code = create_otp()
    challenge = OtpChallengeModel(
        email=str(request.email).lower(),
        code_hash=hash_otp(code),
        expires_at=now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(challenge)
    db.commit()
    try:
        send_otp_email(str(request.email), code)
    except OTPAuthError as exc:
        db.delete(challenge)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email service authentication error. Please contact support.",
        ) from exc
    except (OTPTransientError, OTPDeliveryError) as exc:
        db.delete(challenge)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service is temporarily unavailable. Please try again in a moment.",
        ) from exc
    except RuntimeError as exc:
        db.delete(challenge)
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        db.delete(challenge)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not send login code at this time.",
        ) from exc

    dev_code = code if (not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL) else None
    return {
        "message": "A login code was sent to your email",
        "dev_code": dev_code,
    }


@router.post("/otp/verify", response_model=AuthResponse)
def verify_otp(
    request: OtpVerifyRequest,
    db: Session = Depends(get_db),
):
    email = str(request.email).lower()
    now = datetime.now(timezone.utc)
    challenge = (
        db.query(OtpChallengeModel)
        .filter(
            OtpChallengeModel.email == email,
            OtpChallengeModel.used.is_(False),
        )
        .order_by(OtpChallengeModel.created_at.desc())
        .first()
    )
    expires_at = challenge.expires_at.replace(tzinfo=timezone.utc) if challenge else now
    if not challenge or expires_at < now or not secrets.compare_digest(challenge.code_hash, hash_otp(request.code)):
        raise HTTPException(status_code=401, detail="Invalid or expired login code")

    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired login code")
    challenge.used = True
    db.commit()
    return {
        "access_token": create_access_token({"sub": str(user.id)}),
        "token_type": "bearer",
        "user": {"id": user.id, "name": user.name, "email": user.email},
    }