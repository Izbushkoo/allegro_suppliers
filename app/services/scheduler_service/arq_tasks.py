from arq import cron
from arq.connections import RedisSettings
from arq.jobs import Job, deserialize_job_raw
from arq.cron import cron
from arq.typing import WorkerSettingsBase
import asyncio


async def dynamic_task(ctx, message: str):
    print(f"Running dynamic task with message: {message}")



class WorkerSettings:
    functions = [dynamic_task]
    cron_jobs = []
    redis_settings = RedisSettings(host='redis_suppliers', port=6379)
