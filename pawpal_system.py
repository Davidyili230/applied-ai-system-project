from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from typing import Optional, List
import uuid
import json
import os


class Frequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Maps priority → sort order (lower number = sorts first)
_PRIORITY_ORDER = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}


@dataclass
class Task:
    description: str
    duration_minutes: int
    due_time: Optional[datetime] = None
    recurrence: Frequency = Frequency.ONCE
    priority: Priority = Priority.MEDIUM
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    is_complete: bool = False

    def mark_complete(self):
        """Mark this task as completed."""
        self.is_complete = True

    def to_dict(self) -> dict:
        """Serialize this task to a JSON-safe dictionary."""
        return {
            "description": self.description,
            "duration_minutes": self.duration_minutes,
            "due_time": self.due_time.isoformat() if self.due_time else None,
            "recurrence": self.recurrence.value,
            "priority": self.priority.value,
            "id": self.id,
            "is_complete": self.is_complete,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        """Deserialize a task from a dictionary produced by to_dict()."""
        due_time = datetime.fromisoformat(data["due_time"]) if data.get("due_time") else None
        return cls(
            description=data["description"],
            duration_minutes=data["duration_minutes"],
            due_time=due_time,
            recurrence=Frequency(data["recurrence"]),
            priority=Priority(data.get("priority", "medium")),
            id=data["id"],
            is_complete=data["is_complete"],
        )

    def __repr__(self):
        """Return a human-readable string representation of the task."""
        status = "done" if self.is_complete else "pending"
        return f"Task({self.description!r}, {self.duration_minutes}min, {self.priority.value}, {status})"


@dataclass
class Pet:
    name: str
    species: str
    age: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task):
        """Attach a care task to this pet."""
        self.tasks.append(task)

    def to_dict(self) -> dict:
        """Serialize this pet (and its tasks) to a JSON-safe dictionary."""
        return {
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "id": self.id,
            "tasks": [task.to_dict() for task in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Pet":
        """Deserialize a pet from a dictionary produced by to_dict()."""
        pet = cls(
            name=data["name"],
            species=data["species"],
            age=data["age"],
            id=data["id"],
        )
        pet.tasks = [Task.from_dict(t) for t in data.get("tasks", [])]
        return pet

    def __repr__(self):
        """Return a human-readable string representation of the pet."""
        return f"Pet({self.name!r}, {self.species}, age={self.age})"


@dataclass
class Owner:
    name: str
    email: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet):
        """Register a pet under this owner's care."""
        self.pets.append(pet)

    def remove_pet(self, pet_id: str) -> bool:
        """Remove a pet by ID, returning True if found and removed."""
        for i, pet in enumerate(self.pets):
            if pet.id == pet_id:
                self.pets.pop(i)
                return True
        return False

    def get_all_tasks(self) -> list[Task]:
        """Collect and return all tasks across every owned pet."""
        return [task for pet in self.pets for task in pet.tasks]

    def to_dict(self) -> dict:
        """Serialize this owner (pets and tasks included) to a JSON-safe dictionary."""
        return {
            "name": self.name,
            "email": self.email,
            "id": self.id,
            "pets": [pet.to_dict() for pet in self.pets],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Owner":
        """Deserialize an owner from a dictionary produced by to_dict()."""
        owner = cls(name=data["name"], email=data["email"], id=data["id"])
        owner.pets = [Pet.from_dict(p) for p in data.get("pets", [])]
        return owner

    def save_to_json(self, filepath: str) -> None:
        """Persist the owner, pets, and all tasks to a JSON file at *filepath*."""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_json(cls, filepath: str) -> "Owner":
        """Load and return an Owner from a JSON file previously written by save_to_json()."""
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def __repr__(self):
        """Return a human-readable string representation of the owner."""
        return f"Owner({self.name!r}, pets={len(self.pets)})"


class Scheduler:
    def __init__(self, owner: "Owner"):
        """Initialize the scheduler for the given owner."""
        self.owner = owner

    def get_all_tasks(self) -> list[Task]:
        """Delegate to owner to retrieve all tasks across all pets."""
        return self.owner.get_all_tasks()

    def get_upcoming_tasks(self) -> list[Task]:
        """Return incomplete tasks sorted by due time, undated tasks last."""
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

    def sort_by_time(self, tasks: Optional[List[Task]] = None) -> List[Task]:
        """Return tasks sorted by priority first (High → Medium → Low), then by due_time.

        If *tasks* is provided, sort that list. Otherwise sort all tasks owned
        by this scheduler's owner (including completed ones).
        Undated tasks sort after all dated tasks within the same priority tier.
        """
        source = tasks if tasks is not None else self.get_all_tasks()
        return sorted(
            source,
            key=lambda t: (_PRIORITY_ORDER[t.priority], t.due_time or datetime.max),
        )

    def filter_by_status(self, complete: bool) -> list[Task]:
        """Return all tasks whose completion status matches *complete*."""
        return [t for t in self.get_all_tasks() if t.is_complete == complete]

    def filter_by_pet(self, pet_name: str) -> list[Task]:
        """Return all tasks belonging to the pet whose name matches *pet_name* (case-insensitive)."""
        for pet in self.owner.pets:
            if pet.name.lower() == pet_name.lower():
                return list(pet.tasks)
        return []

    def mark_task_complete(self, task_id: str) -> bool:
        """Mark a task complete and, for daily/weekly tasks, schedule the next occurrence.

        Searches each pet's task list directly so the next occurrence can be
        attached to the correct pet using timedelta arithmetic:
          - Frequency.DAILY  → due_time + timedelta(days=1)
          - Frequency.WEEKLY → due_time + timedelta(weeks=1)

        Returns True if the task was found and marked complete, False otherwise.
        """
        from datetime import timedelta

        for pet in self.owner.pets:
            for task in pet.tasks:
                if task.id != task_id:
                    continue
                task.mark_complete()
                if task.due_time is not None:
                    if task.recurrence == Frequency.DAILY:
                        next_due = task.due_time + timedelta(days=1)
                    elif task.recurrence == Frequency.WEEKLY:
                        next_due = task.due_time + timedelta(weeks=1)
                    else:
                        next_due = None
                    if next_due is not None:
                        pet.add_task(Task(
                            description=task.description,
                            duration_minutes=task.duration_minutes,
                            due_time=next_due,
                            recurrence=task.recurrence,
                            priority=task.priority,
                        ))
                return True
        return False

    def check_conflicts(self, task: Task) -> Optional[str]:
        """Return a warning message if the given task overlaps with any existing task, else None.

        Lightweight strategy: scan all scheduled tasks and compare time windows using
        interval-overlap arithmetic (task starts before other ends AND ends after other starts).
        Returns the first conflict found as a human-readable string so callers can print
        a warning without crashing.
        """
        if task.due_time is None:
            return None
        task_end = datetime.fromtimestamp(
            task.due_time.timestamp() + task.duration_minutes * 60
        )
        for pet in self.owner.pets:
            for existing in pet.tasks:
                if existing is task or existing.due_time is None:
                    continue
                existing_end = datetime.fromtimestamp(
                    existing.due_time.timestamp() + existing.duration_minutes * 60
                )
                if task.due_time < existing_end and task_end > existing.due_time:
                    return (
                        f"WARNING: '{task.description}' "
                        f"({task.due_time.strftime('%I:%M %p')}–"
                        f"{task_end.strftime('%I:%M %p')}) conflicts with "
                        f"'{existing.description}' for {pet.name} "
                        f"({existing.due_time.strftime('%I:%M %p')}–"
                        f"{existing_end.strftime('%I:%M %p')})"
                    )
        return None

    def find_next_available_slot(
        self,
        duration_minutes: int,
        start_from: Optional[datetime] = None,
    ) -> datetime:
        """Find the earliest datetime where a task of *duration_minutes* fits without conflicts.

        Algorithm (greedy gap scan):
          1. Collect all incomplete, timed tasks and sort them by due_time.
          2. Starting from *start_from* (default: now), maintain a *candidate* start time.
          3. For each existing task whose window overlaps the candidate window, push the
             candidate forward to that task's end time.
          4. After processing all tasks, *candidate* is the earliest conflict-free slot.

        This is O(n log n) for the sort and O(n) for the scan — efficient even with
        hundreds of tasks.

        Returns the candidate datetime (timezone-naive, matching the system clock).
        """
        from datetime import timedelta

        start_from = start_from or datetime.now()

        timed_tasks = sorted(
            [t for t in self.get_all_tasks() if t.due_time is not None and not t.is_complete],
            key=lambda t: t.due_time,
        )

        candidate = start_from
        for task in timed_tasks:
            task_end = task.due_time + timedelta(minutes=task.duration_minutes)
            candidate_end = candidate + timedelta(minutes=duration_minutes)
            # If the candidate window overlaps this task, slide candidate to after the task
            if task.due_time < candidate_end and task_end > candidate:
                candidate = task_end

        return candidate

    def generate_recurring_tasks(self) -> list[Task]:
        """Create the next occurrence for each daily or weekly recurring task."""
        from datetime import timedelta

        generated = []
        for task in self.get_all_tasks():
            if task.recurrence == Frequency.DAILY and task.due_time:
                next_task = Task(
                    description=task.description,
                    duration_minutes=task.duration_minutes,
                    due_time=task.due_time + timedelta(days=1),
                    recurrence=task.recurrence,
                    priority=task.priority,
                )
                generated.append(next_task)
            elif task.recurrence == Frequency.WEEKLY and task.due_time:
                next_task = Task(
                    description=task.description,
                    duration_minutes=task.duration_minutes,
                    due_time=task.due_time + timedelta(weeks=1),
                    recurrence=task.recurrence,
                    priority=task.priority,
                )
                generated.append(next_task)
        return generated

    def summary(self) -> dict:
        """Return a dict with counts of pets, total tasks, pending, and completed."""
        all_tasks = self.get_all_tasks()
        pending = [t for t in all_tasks if not t.is_complete]
        completed = [t for t in all_tasks if t.is_complete]
        return {
            "owner": self.owner.name,
            "total_pets": len(self.owner.pets),
            "total_tasks": len(all_tasks),
            "pending": len(pending),
            "completed": len(completed),
        }
