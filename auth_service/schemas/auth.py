from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    name    : str
    email   : EmailStr
    password: str

class LoginRequest(BaseModel):
    email   : EmailStr
    password: str

class AuthResponse(BaseModel):
    access_token : str
    token_type   : str = "bearer"
    developer_id : str
    name         : str
    plan         : str

class RefreshRequest(BaseModel):
    pass  # refresh token comes from cookie, no body needed

class MessageResponse(BaseModel):
    message: str