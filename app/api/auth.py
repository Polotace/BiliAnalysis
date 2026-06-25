"""Authentication: password hashing, session, user lookup."""
import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.db.user_schema import User
from api.config import ApiSettings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def authenticate(db: AsyncSession, username: str, password: str,
                       settings: ApiSettings) -> User | None:
    """Authenticate a user. On first login, creates DB record from config."""
    user = await get_user_by_username(db, username)
    if user is not None:
        if verify_password(password, user.password_hash):
            return user
        return None

    # First login — match against config admin credentials
    if username == settings.admin_user and password == settings.admin_password:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role="admin",
            must_change_password=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    return None
