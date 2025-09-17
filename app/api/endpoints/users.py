import logging
import re
from datetime import timedelta
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import EmailStr

from app.models.user import user_model
from app.schemas.user import User, UserResponse
from app.utils import create_access_token, hash_password, settings, verify_password

router = APIRouter()


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/oauth2-scheme-token")


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
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
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


@router.post("/", response_model=UserResponse)
async def create_user(
    username: Annotated[str, Form(...)],
    email: Annotated[EmailStr, Form(...)],
    password: Annotated[str, Form(...)],
    first_name: Annotated[str | None, Form()] = None,
    last_name: Annotated[str | None, Form()] = None,
):
    """
    Create a new user
    """
    logger.info(f"Creating new user with email: {email}")

    # Check if user exists
    user_exists = await user_model.check_existing_username_and_email(
        username.lower(), email.lower()
    )

    if user_exists:
        detail = "Email or username already registered"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    # Create user document
    user_id = str(ObjectId())
    hashed_password = hash_password(password)

    # Create user data dictionary
    user_data = {
        "id": user_id,
        "email": email.lower(),
        "username": username.lower(),
        "hashed_password": hashed_password,
        "first_name": first_name,
        "last_name": last_name,
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
        data={"sub": email.lower()}, expires_delta=access_token_expires
    )

    # Prepare user response
    user_response = UserResponse(
        access_token=access_token,
        token_type="bearer",
        user=User(
            id=user_id,
            email=email.lower(),
            username=username.lower(),
            first_name=first_name,
            last_name=last_name,
        ),
    )

    logger.info(f"Successfully created user with email: {email}")
    return user_response


# Update the login endpoint
@router.post("/token", response_model=UserResponse)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    logger.info(f"Login attempt for user: {form_data.username}")

    # Find user by username (case insensitive)
    user = await user_model.get_by_username(form_data.username.lower())
    logger.info(f"User found: {user}")

    if not user:
        logger.error("User not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
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

    logger.info(f"Login successful for user: {form_data.username}")
    return user_response


@router.post("/oauth2-scheme-token", response_model=dict)
async def oauth_scheme_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    """
    Generate access token using email (provided in OAuth2 `username` field).
    Returns only the token payload for OAuth2 compatibility.
    """
    user = await user_model.get_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


# Protected route to get current user info
@router.get("/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.get("/all", response_model=list[User])
async def get_all_users():
    """get all users"""
    users = await user_model.get_all()
    return users


@router.get("/{user_id}", response_model=User)
async def get_user(user_id: str):
    """get user by id"""
    print(user_id)
    user = await user_model.get_by_id(user_id)
    return user


@router.delete("/clear", response_model=None)
async def clear_users():
    return await user_model.delete_all_users()
