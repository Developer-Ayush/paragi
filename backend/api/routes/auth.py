from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

router = APIRouter(tags=['auth'])
_USERS: Dict[str, Dict[str, str]] = {} # user_id -> {password, tier}
_SESSIONS: Dict[str, Dict[str, str]] = {} # token -> {user_id, tier}

class AuthRequest(BaseModel):
    user_id: str
    password: Optional[str] = None
    tier: Optional[str] = 'free'

class AuthResponse(BaseModel):
    user_id: str
    tier: str
    token: str

class TokenRequest(BaseModel):
    token: str

@router.post('/register', response_model=AuthResponse)
@router.post('/auth/register', response_model=AuthResponse)
@router.post('/users/register', response_model=AuthResponse)
async def register(req: AuthRequest):
    tier = req.tier or 'free'
    _USERS[req.user_id] = {'password': req.password or 'pass1234', 'tier': tier}
    token = f"token_{req.user_id}"
    _SESSIONS[token] = {'user_id': req.user_id, 'tier': tier}
    return AuthResponse(user_id=req.user_id, tier=tier, token=token)

@router.post('/login', response_model=AuthResponse)
@router.post('/auth/login', response_model=AuthResponse)
async def login(req: AuthRequest):
    user = _USERS.get(req.user_id)
    if not user or (req.password and user['password'] != req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = f"token_{req.user_id}"
    _SESSIONS[token] = {'user_id': req.user_id, 'tier': user['tier']}
    return AuthResponse(user_id=req.user_id, tier=user['tier'], token=token)

@router.get('/auth/session')
async def session(token: Optional[str] = None):
    sess = _SESSIONS.get(token)
    if not sess:
        return {'user_id': 'guest', 'tier': 'free'}
    return sess

@router.post('/auth/logout')
async def logout(req: TokenRequest):
    return {'ok': True}

@router.get('/users/{user_id}')
async def get_user_profile(user_id: str):
    return {
        'user_id': user_id,
        'tier': 'contributor',
        'credit_balance': 100,
        'main_nodes_contributed': 5,
        'personal_nodes_count': 2,
        'domain_nodes_contributed': {'legal': 5},
        'domain_credits_earned': {'legal': 50}
    }
