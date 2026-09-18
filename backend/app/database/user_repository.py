from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import UserModel


def create_user(
    db: Session,
    name: str,
    email: str,
    password_hash: str,
) -> UserModel:
    user = UserModel(
        name=name,
        email=email.lower().strip(),
        password_hash=password_hash,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_user_by_email(
    db: Session,
    email: str,
) -> Optional[UserModel]:
    return (
        db.query(UserModel)
        .filter(UserModel.email == email.lower().strip())
        .first()
    )


def get_user_by_id(
    db: Session,
    user_id: int,
) -> Optional[UserModel]:
    return db.get(UserModel, user_id)