import asyncio
import json
import os
import random
import time

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
CACHE_TTL = int(os.getenv("CACHE_TTL", 30))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

ATTRACTIONS = {
    "eiffel-tower": {"name": "Eiffel Tower", "city": "Paris", "rating": 4.7},
    "shibuya-crossing": {"name": "Shibuya Crossing", "city": "Tokyo", "rating": 4.5},
    "marina-bay-sands": {"name": "Marina Bay Sands", "city": "Singapore", "rating": 4.6},
    "burj-khalifa": {"name": "Burj Khalifa", "city": "Dubai", "rating": 4.8},
}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api/attraction/{slug}")
async def get_attraction(slug: str):
    cache_key = f"attraction:{slug}"

    cached = await redis_client.get(cache_key)
    if cached:
        payload = json.loads(cached)
        payload["_cache"] = "HIT"
        return JSONResponse(content=payload)

    await asyncio.sleep(random.uniform(0.01, 0.08))

    data = ATTRACTIONS.get(slug)
    if data is None:
        return JSONResponse(status_code=404, content={"error": "not found"})

    result = dict(data)
    result["_cache"] = "MISS"
    result["_ts"] = time.time()

    await redis_client.set(cache_key, json.dumps(result), ex=CACHE_TTL)
    return JSONResponse(content=result)
