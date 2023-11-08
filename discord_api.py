import uuid
import os
from furl import furl
from dotenv import load_dotenv
from werkzeug.exceptions import HTTPException, InternalServerError
import json
from quart import Response, abort
from urllib.parse import urlencode

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://example.com")

class DiscordAPIError(HTTPException):
    ...

class DiscordAuthException(HTTPException):
    ...

async def get_oauth_url():

    state = uuid.uuid4()
    params = {
        "client_id": os.getenv("DISCORD_CLIENT_ID"),
        "redirect_uri": os.getenv("DISCORD_REDIRECT_URI"),
        "response_type": "code",
        "state": state,
        "scope": "role_connections.write identify connections guilds",
        "prompt": "consent",
    }
    url = f"{BASE_URL}/api/oauth2/authorize?{urlencode(params)}"
    return (state, url)

async def get_oauth_tokens(session, code):
    url = f"{BASE_URL}/api/v10/oauth2/token"
    data = {
        "client_id": os.getenv("DISCORD_CLIENT_ID"),
        "client_secret": os.getenv("DISCORD_CLIENT_SECRET"),
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.getenv("DISCORD_REDIRECT_URI"),
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = await session.post(url, data=data, headers=headers)
    except Exception:
        raise HTTPException("Error while getting oauth tokens")
    if response.status != 200:
        raise HTTPException("Error while getting oauth tokens")
    return await response.json()

async def get_user_data(session, tokens: dict):
    url = f"{BASE_URL}/api/v10/oauth2/@me"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await session.get(url, headers=headers)
    if response.status != 200:
        raise HTTPException("Error while getting user data")
    return await response.json()

async def get_metadata(session, tokens):
    url = f"{BASE_URL}/api/v10/users/@me/applications/{os.getenv('DISCORD_CLIENT_ID')}/role-connection"
    headers = {"Authorization": f"Bearer {tokens['access_token']}", "Content-Type": "application/json"}

    response = await session.get(url, headers=headers)
    if response.status != 200:
        raise HTTPException("Error while getting metadata")
    return await response.json()

async def push_metadata(session, tokens, metadata):
    if not metadata:
        metadata = {
            "epiceligibility": "0",
            "steameligibility": "0"
        }
    url = f"{BASE_URL}/api/v10/users/@me/applications/{os.getenv('DISCORD_CLIENT_ID')}/role-connection"
    data = {
        "platform_name": "Eligibility",
        "metadata": metadata,
    }
    headers = {"Authorization": f"Bearer {tokens['access_token']}", "Content-Type": "application/json"}

    response = await session.put(url, data=json.dumps(data), headers=headers)
    if response.status != 200:
        raise HTTPException("Error while pushing metadata")
    return await response.json()

async def get_user_connections(session, tokens):
    url = f"{BASE_URL}/api/v10/users/@me/connections"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await session.get(url, headers=headers)
    if response.status != 200:
        raise HTTPException("Error while getting user connections")
    return await response.json()

async def get_user_guilds(session, tokens):
    url = f"{BASE_URL}/api/v10/users/@me/guilds"
    headers = {'Authorization': f"Bearer {tokens['access_token']}"}

    response = await session.get(url, headers=headers)
    if response.status != 200:
        raise HTTPException("Error while getting user guilds")
    return await response.json()