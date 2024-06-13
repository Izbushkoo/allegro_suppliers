from typing import Callable, Coroutine, Any


class TaskWrapper:

    def __init__(self, task: Callable[..., Coroutine[Any, Any, Any]]):
        self.task = task

    def run_task(self, *args, **kwargs):
        async def task_wrapper():
            await self.task(*args, **kwargs)
        return task_wrapper
