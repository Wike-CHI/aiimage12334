from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi.security import OAuth2PasswordRequestForm
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, Token, UserResponse, UserUpdate
from app.auth import get_password_hash, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def generate_user_code(db: Session) -> str:
    """生成用户编号，如 WB2024001"""
    year = datetime.now().year
    # 获取当年注册用户数量
    count = db.query(func.count(User.id)).filter(
        func.year(User.created_at) == year
    ).scalar() or 0
    return f"WB{year}{str(count + 1).zfill(4)}"


@router.post("/register", response_model=Token)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # 检查用户名是否已存在
    existing_username = db.query(User).filter(User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    user_code = generate_user_code(db)

    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        username=user_data.username,
        user_code=user_code,
        credits=100  # 新用户默认100积分
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 生成 token
    access_token = create_access_token(data={"sub": str(new_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # 查找用户
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 生成 token
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserResponse)
def update_user_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户信息"""
    if update_data.username:
        # 检查用户名是否被其他用户使用
        existing = db.query(User).filter(
            User.username == update_data.username,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = update_data.username

    if update_data.theme:
        if update_data.theme not in ['light', 'dark', 'auto']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid theme value"
            )
        current_user.theme = update_data.theme

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/refresh", response_model=Token)
def refresh_token(current_user: User = Depends(get_current_user)):
    access_token = create_access_token(data={"sub": str(current_user.id)})
    return {"access_token": access_token, "token_type": "bearer"}
