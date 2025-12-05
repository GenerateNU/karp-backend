import hashlib
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
)
from jose import JWTError, jwt

from app.models.user import user_model
from app.schemas.device_token import UnregisterDeviceTokenRequest
from app.schemas.user import (
    CreateUserRequest,
    LoginRequest,
    ResetPasswordRequest,
    User,
    UserRedirectResponse,
    UserResponse,
    UserType,
)
from app.services.cache import cache_service
from app.services.device_token import device_token_service
from app.utils.user import create_access_token, hash_password, settings, verify_password

router = APIRouter()


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/user/oauth2-scheme-token",
    auto_error=False,
)

bearer = HTTPBearer(auto_error=False)


def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength
    Returns: (is_valid: bool, message: str)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"


def validate_email(email: str) -> tuple[bool, str]:
    """
    Validate email format and domain
    Returns: (is_valid: bool, message: str)
    """
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_regex, email):
        return False, "Invalid email format"
    # Add additional domain validation if needed
    return True, "Email is valid"


# Get current user
async def get_current_user(
    oauth_token: Annotated[str | None, Depends(oauth2_scheme)],
    bearer_creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = None
    if oauth_token:
        token = oauth_token
    elif bearer_creds:
        token = bearer_creds.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # check if token is blacklisted
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    is_blacklisted = await cache_service.get("blacklist:token", token_hash)
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is blacklisted",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception from None
    user = await user_model.get_by_email(email)
    if user is None:
        raise credentials_exception
    return user


# Get current admin user
async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access this endpoint",
        )
    return current_user


@router.post("/", response_model=UserResponse)
async def create_user(payload: Annotated[CreateUserRequest, Body(...)]):
    """
    Create a new user
    """
    logger.info(f"Creating new user with email: {payload.email}")

    # Validate email format
    ok_email, email_message = validate_email(payload.email)
    if not ok_email:
        print("hello")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=email_message)

    # Validate password strength
    ok, message = validate_password(payload.password)
    if not ok:
        print("bye")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    # Check if user exists
    user_exists = await user_model.check_existing_username_and_email(
        payload.username.lower(), payload.email.lower()
    )

    if user_exists:
        print("lol")
        detail = "Email or username already registered"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    # Create user document
    user_id = str(ObjectId())
    hashed_password = hash_password(payload.password)

    # Create user data dictionary
    user_data = {
        "id": user_id,
        "email": payload.email.lower(),
        "username": payload.username.lower(),
        "hashed_password": hashed_password,
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "user_type": payload.user_type,
    }

    # Save user to database
    try:
        await user_model.create_user(user_data)
    except Exception as e:
        logger.error(f"Database error during user creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error creating user account"
        ) from None

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": payload.email.lower()}, expires_delta=access_token_expires
    )

    # Prepare user response
    user_response = UserResponse(
        access_token=access_token,
        token_type="bearer",
        user=User(**user_data),
    )

    logger.info(f"Successfully created user with email: {payload.email}")
    return user_response


# Update the login endpoint
@router.post("/token", response_model=UserResponse)
async def login_for_access_token(payload: Annotated[LoginRequest, Body(...)]):
    logger.info(f"Login attempt for user: {payload.username}")

    # Find user by username (case insensitive)
    user = await user_model.get_by_username(payload.username.lower())
    logger.info(f"User found: {user}")

    if not user:
        logger.error("User not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(payload.password, user.hashed_password):
        logger.error("Invalid password")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)

    # Prepare user response
    user_response = UserResponse(
        access_token=access_token,
        token_type="bearer",
        user=user,
    )

    logger.info(f"Login successful for user: {payload.username}")
    return user_response


@router.post("/oauth2-scheme-token", response_model=dict)
async def oauth_scheme_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Generate access token using email (provided in OAuth2 `username` field).
    Returns only the token payload for OAuth2 compatibility.
    """
    user = await user_model.get_by_username(form_data.username.lower())
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/reset-password", response_model=dict)
async def reset_password(
    payload: Annotated[ResetPasswordRequest, Body(...)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Reset password for the authenticated user."""
    # Verify current password
    if not current_user.hashed_password or not verify_password(
        payload.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
        )

    # Validate new password strength
    ok, message = validate_password(payload.new_password)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    # Prevent reusing the same password
    if verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )

    # Hash and update
    new_hashed = hash_password(payload.new_password)
    try:
        await user_model.update_password_by_id(current_user.id, new_hashed)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        ) from None

    return {"detail": "Password updated successfully"}


@router.post("/logout", response_model=dict)
async def logout(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
):
    # Extract token from request
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1]

    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            exp_timestamp = payload.get("exp")

            if exp_timestamp:
                exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=UTC)
                now = datetime.now(UTC)
                remaining_seconds = int((exp_datetime - now).total_seconds())

                if remaining_seconds > 0:
                    token_hash = hashlib.sha256(token.encode()).hexdigest()
                    # Store a simple marker value (string) to avoid Redis serialization errors
                    await cache_service.set(
                        "blacklist:token",
                        token_hash,
                        "1",
                        expire=remaining_seconds,
                    )
        except (JWTError, ValueError) as e:
            logger.warning(f"Could not blacklist token: {e}")

    await device_token_service.unregister_user_token(
        UnregisterDeviceTokenRequest(volunteer_id=current_user.id)
    )
    return {"detail": "Successfully logged out"}


@router.get("/me", response_model=UserRedirectResponse)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return UserRedirectResponse(user_type=current_user.user_type, entity_id=current_user.entity_id)


@router.get("/all", response_model=list[User])
async def get_all_users():
    """get all users"""
    users = await user_model.get_all()
    return users


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str):
    """get user by id"""
    user = await user_model.get_by_id(user_id)
    return user


@router.delete("/clear", response_model=None)
async def clear_users():
    return await user_model.delete_all_users()
