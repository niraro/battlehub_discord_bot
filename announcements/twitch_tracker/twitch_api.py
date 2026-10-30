import os
import time
from datetime import datetime
import asyncio
import aiohttp

API_URL = "https://api.twitch.tv/helix"
TOKEN_URL = "https://id.twitch.tv/oauth2/token"

def describe_twitch_error(error):
    if isinstance(error, aiohttp.ClientResponseError):
        if error.status >= 500:
            return "Twitch having issues"
        if error.status == 429:
            return "Rate limited"
        return f"Twitch rejected the request ({error.status}): check credentials and the request"
    if isinstance(error, asyncio.TimeoutError):
        return "Timed out"
    return "Network problem reaching Twitch"

class TwitchClient:
    def __init__(self):
        self._session = None
        self._token = None
        self._token_expires = 0
    
    def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout = aiohttp.ClientTimeout(total = 15))
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            
    async def _refresh_token(self):
        client_id = os.getenv("TWITCH_CLIENT_ID")
        client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError("TWITCH_CLIENT_ID and/or TWITCH_CLIENT_SECRET are not set")
        async with self._get_session().post(TOKEN_URL, data = {"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"}) as resp:
            resp.raise_for_status()
            data = await resp.json()
        self._token = data["access_token"]
        self._token_expires = time.time() + data["expires_in"] - 300
        
    async def _get(self, path, params):
        if self._token is None or time.time() >= self._token_expires:
            await self._refresh_token()
        for attempt in range(2):
            headers = {"Client-ID": os.getenv("TWITCH_CLIENT_ID"), "Authorization": f"Bearer {self._token}"}
            async with self._get_session().get(f"{API_URL}/{path}", params = params, headers = headers) as resp:
                if resp.status == 401 and attempt == 0:
                    await self._refresh_token()
                    continue
                resp.raise_for_status()
                return await resp.json()
            
    async def get_user(self, login):
        data = await self._get("users", [("login", login)])
        users = data.get("data", [])
        if not users:
            return None
        u = users[0]
        return {"id": u["id"], "login": u["login"], "display_name": u["display_name"]}
    
    async def get_streams(self, user_ids):
        live = {}
        ids = list(user_ids)
        for i in range(0, len(ids), 100):
            chunk = ids[i:i + 100]
            data = await self._get("streams", [("user_id", uid) for uid in chunk] + [("first", "100")])
            for s in data.get("data", []):
                if s.get("type") != "live":
                    continue
                live[s["user_id"]] = {
                    "id": s["id"],
                    "title": s.get("title", ""),
                    "game_name": s.get("game_name", ""),
                    "viewer_count": s.get("viewer_count", 0),
                    "thumbnail_url": s.get("thumbnail_url"),
                    "started_at_ts": int(datetime.fromisoformat(s["started_at"]).timestamp()),
                }
            return live

twitch_client = TwitchClient()