import os
from redis import Redis
from rq import Worker, Queue

redis_conn = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

if __name__ == "__main__":
    queue = Queue(connection=redis_conn)
    worker = Worker([queue], connection=redis_conn)
    worker.work()