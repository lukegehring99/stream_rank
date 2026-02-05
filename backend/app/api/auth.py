"""Authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import JWTHandler, create_jwt_handler
from app.db import get_db_session
from app.models import User
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
    jwt_handler: JWTHandler = Depends(create_jwt_handler),
) -> LoginResponse:
    """Authenticate and get JWT token."""
    # Find user
    result = await session.execute(
        select(User).where(User.username == credentials.username)
    )
    user = result.scalar_one_or_none()
    
    if user is None or not user.check_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Generate token
    token, expires_at = jwt_handler.create_token(user.username)
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_at=expires_at,
    )
