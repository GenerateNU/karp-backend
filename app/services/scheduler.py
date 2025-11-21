from apscheduler.schedulers.asyncio import AsyncIOScheduler


class SchedulerService:
    _instance: "SchedulerService" = None

    def __init__(self):
        if SchedulerService._instance is not None:
            raise Exception("This class is a singleton!")
        self.scheduler: AsyncIOScheduler | None = None
        self._started = False

    @classmethod
    def get_instance(cls) -> "SchedulerService":
        if SchedulerService._instance is None:
            SchedulerService._instance = cls()
        return SchedulerService._instance

    def start(self) -> None:
        if not self._started:
            self.scheduler = AsyncIOScheduler()
            self.scheduler.start()
            self._started = True

    def shutdown(self) -> None:
        if self._started and self.scheduler:
            self.scheduler.shutdown()
            self._started = False

    def get_scheduler(self) -> AsyncIOScheduler:
        if self.scheduler is None:
            raise ValueError("Scheduler not started")
        return self.scheduler


scheduler_service = SchedulerService.get_instance()
