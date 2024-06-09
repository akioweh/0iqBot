"""
Module that contains utilities to help with concurrency problems.
"""
from asyncio import AbstractEventLoop, CancelledError, Event, Task, sleep
from collections.abc import Coroutine
from contextlib import suppress
from sys import __stderr__
from traceback import print_exception


class TaskKeeper:
    """
    Class that keeps track of assigned tasks
    and allows for offloaded execution or fine-grained control.
    """

    def __init__(self, loop: AbstractEventLoop):
        self.loop = loop
        self.tasks: list[Task] = []
        self.has_pending = Event()
        self._running = False
        self._awaiter = None

    def run_task(self, task: Task):
        """Run a task in the background."""
        self.tasks.append(task)
        self.has_pending.set()
        return task

    def run_coro(self, coro: Coroutine):
        """Run a coroutine in the background."""
        return self.run_task(self.loop.create_task(coro))

    async def _await_tasks(self):
        # checks if any tasks are done and removes them
        while True:
            await self.has_pending.wait()
            for i, task in enumerate(self.tasks.copy()):
                if task.done():
                    self.tasks.pop(i)
                    if task.exception():
                        print(f'Task {task} raised an exception in TaskKeeper:', file=__stderr__)
                        print_exception(task.exception(), file=__stderr__)
            if not self.tasks:
                self.has_pending.clear()
            else:
                await sleep(1)

    def start(self):
        """Start a self-maintained loop to await tasks in the background."""
        if self._running:
            raise RuntimeError("Tried to start a TaskKeeper that is already running.")
        self._awaiter = self.loop.create_task(self._await_tasks())
        self._running = True

    def stop(self):
        """Stop the self-maintained loop."""
        if not self._running:
            raise RuntimeError("Tried to stop a TaskKeeper that isn't running.")

        if self.has_pending.is_set():
            for task in self.tasks:
                if not task.done():
                    with suppress(CancelledError):
                        task.cancel()

        with suppress(CancelledError):
            self._awaiter.cancel()
        self._running = False
