from apscheduler.schedulers.asyncio import AsyncIOScheduler


if __name__ == "__main__":
    scheduler = AsyncIOScheduler()
    scheduler.add_job()
    scheduler.start()
