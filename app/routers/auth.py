from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.enums import Role
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse, UserRead, UserUpdate, PasswordChange
from app.schemas.response import ApiResponse, ok
from app.utils.security import hash_password, verify_password, create_access_token
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=ApiResponse[UserRead], status_code=201)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        hashed_password=await hash_password(body.password),
        role=Role.team_member,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return ok(UserRead.model_validate(user), "Account created successfully")


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not await verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id, "role": user.role.value})
    return ok(TokenResponse(access_token=token), "Login successful")


@router.get("/me", response_model=ApiResponse[UserRead])
async def get_me(current_user: User = Depends(get_current_user)):
    return ok(UserRead.model_validate(current_user), "User retrieved")


@router.put("/profile", response_model=ApiResponse[UserRead])
async def update_profile(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return ok(UserRead.model_validate(current_user), "Profile updated")


@router.post("/change-password", response_model=ApiResponse[None])
async def change_password(
    body: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = await hash_password(body.new_password)
    await db.commit()
    return ok(None, "Password changed successfully")


@router.post("/logout", response_model=ApiResponse[None])
async def logout(current_user: User = Depends(get_current_user)):
    return ok(None, "Logged out successfully")
