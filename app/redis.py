import os
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Create a connection pool to avoid creating a new connection for every request
redis_pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)

def get_redis_client():
    return redis.Redis(connection_pool=redis_pool)
