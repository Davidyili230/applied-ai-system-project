from enum import Enum
from datetime import datetime
from typing import Optional
import uuid


class Frequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


class Task:
    def __init__(
        self,
        description: str,
        duration_minutes: int,
        due_time: Optional[datetime] = None,
        recurrence: Frequency = Frequency.ONCE,
    ):
        self.id = str(uuid.uuid4())
        self.description = description
        self.duration_minutes = duration_minutes
        self.due_time = due_time
        self.recurrence = recurrence
        self.is_complete = False

    def mark_complete(self):
        self.is_complete = True

    def __repr__(self):
        status = "done" if self.is_complete else "pending"
        return f"Task({self.description!r}, {self.duration_minutes}min, {status})"


class Pet:
    def __init__(self, name: str, species: str, age: int):
        self.id = str(uuid.uuid4())
        self.name = name
        self.species = species
        self.age = age
        self.tasks: list[Task] = []

    def add_task(self, task: Task):
        self.tasks.append(task)

    def __repr__(self):
        return f"Pet({self.name!r}, {self.species}, age={self.age})"


class Scheduler:
    def __init__(self):
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet):
        self.pets.append(pet)

    def get_all_tasks(self) -> list[Task]:
        return [task for pet in self.pets for task in pet.tasks]

    def get_upcoming_tasks(self) -> list[Task]:
        now = datetime.now()
        upcoming = []
        for task in self.get_all_tasks():
            if task.is_complete:
                continue
            if task.due_time is None or task.due_time >= now:
                upcoming.append(task)
        return sorted(
            upcoming,
            key=lambda t: (t.due_time or datetime.max),
        )

    def check_conflicts(self, task: Task) -> bool:
        if task.due_time is None:
            return False
        task_end = datetime.fromtimestamp(
            task.due_time.timestamp() + task.duration_minutes * 60
        )
        for existing in self.get_all_tasks():
            if existing is task or existing.due_time is None:
                continue
            existing_end = datetime.fromtimestamp(
                existing.due_time.timestamp() + existing.duration_minutes * 60
            )
            if task.due_time < existing_end and task_end > existing.due_time:
                return True
        return False

    def generate_recurring_tasks(self) -> list[Task]:
        from datetime import timedelta

        generated = []
        for task in self.get_all_tasks():
            if task.recurrence == Frequency.DAILY and task.due_time:
                next_task = Task(
                    description=task.description,
                    duration_minutes=task.duration_minutes,
                    due_time=task.due_time + timedelta(days=1),
                    recurrence=task.recurrence,
                )
                generated.append(next_task)
            elif task.recurrence == Frequency.WEEKLY and task.due_time:
                next_task = Task(
                    description=task.description,
                    duration_minutes=task.duration_minutes,
                    due_time=task.due_time + timedelta(weeks=1),
                    recurrence=task.recurrence,
                )
                generated.append(next_task)
        return generated
