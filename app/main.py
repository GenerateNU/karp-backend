from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import health, persons, users, event, vendors

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost",
    "http://192.168.1.34:8000",
    "http://localhost:8000",
    "http://localhost:3000",  # Add your frontend URL here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the users router
app.include_router(health.router, prefix="", tags=["health"])

app.include_router(users.router, prefix="/users", tags=["users"])

app.include_router(persons.router, prefix="/persons", tags=["persons"])

app.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
app.include_router(health.router, prefix="", tags=["Health"])

app.include_router(event.router, prefix="/events", tags=["events"])

# Login
@app.post("/token", response_model=dict)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await user_model.get_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
