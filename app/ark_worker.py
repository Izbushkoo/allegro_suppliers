from arq import run_worker
from app.services.scheduler_service.arq_tasks import WorkerSettings


if __name__ == '__main__':
    run_worker(WorkerSettings)
