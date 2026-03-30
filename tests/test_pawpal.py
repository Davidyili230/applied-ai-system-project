from datetime import datetime, timedelta
from pawpal_system import Task, Pet, Owner, Scheduler, Frequency


def test_mark_complete_changes_status():
    task = Task(description="Feed Buddy", duration_minutes=5)
    assert task.is_complete is False
    task.mark_complete()
    assert task.is_complete is True


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Buddy", species="Dog", age=3)
    assert len(pet.tasks) == 0
    pet.add_task(Task(description="Morning walk", duration_minutes=30))
    assert len(pet.tasks) == 1
    pet.add_task(Task(description="Evening walk", duration_minutes=45))
    assert len(pet.tasks) == 2


# ---------------------------------------------------------------------------
# Sorting correctness
# ---------------------------------------------------------------------------

def test_get_upcoming_tasks_sorted_chronologically():
    """Tasks with earlier due_times should appear first in the result."""
    now = datetime.now()
    owner = Owner(name="Alice", email="alice@example.com")
    pet = Pet(name="Buddy", species="Dog", age=3)
    owner.add_pet(pet)

    late_task  = Task(description="Evening walk", duration_minutes=30,
                      due_time=now + timedelta(hours=5))
    early_task = Task(description="Morning walk", duration_minutes=30,
                      due_time=now + timedelta(hours=1))
    no_time_task = Task(description="Grooming", duration_minutes=20)

    # Add out of order intentionally
    pet.add_task(late_task)
    pet.add_task(no_time_task)
    pet.add_task(early_task)

    scheduler = Scheduler(owner)
    result = scheduler.get_upcoming_tasks()

    # Chronological order: early → late → no due_time
    assert result[0].description == "Morning walk"
    assert result[1].description == "Evening walk"
    assert result[2].description == "Grooming"


# ---------------------------------------------------------------------------
# Recurrence logic
# ---------------------------------------------------------------------------

def test_mark_daily_task_complete_spawns_next_day():
    """Completing a DAILY task must add a new task due exactly 24 h later."""
    now = datetime.now()
    owner = Owner(name="Bob", email="bob@example.com")
    pet = Pet(name="Luna", species="Cat", age=2)
    owner.add_pet(pet)

    daily_task = Task(
        description="Feed Luna",
        duration_minutes=5,
        due_time=now,
        recurrence=Frequency.DAILY,
    )
    pet.add_task(daily_task)

    scheduler = Scheduler(owner)
    scheduler.mark_task_complete(daily_task.id)

    # Original task is now complete
    assert daily_task.is_complete is True

    # A second task should have been appended to the pet
    assert len(pet.tasks) == 2
    new_task = pet.tasks[1]
    assert new_task.is_complete is False
    assert new_task.description == "Feed Luna"
    assert new_task.due_time == daily_task.due_time + timedelta(days=1)


def test_mark_once_task_complete_does_not_spawn():
    """Completing a ONCE task must NOT create any follow-up task."""
    now = datetime.now()
    owner = Owner(name="Carol", email="carol@example.com")
    pet = Pet(name="Max", species="Rabbit", age=1)
    owner.add_pet(pet)

    once_task = Task(
        description="Vet visit",
        duration_minutes=60,
        due_time=now,
        recurrence=Frequency.ONCE,
    )
    pet.add_task(once_task)

    scheduler = Scheduler(owner)
    scheduler.mark_task_complete(once_task.id)

    assert len(pet.tasks) == 1  # no new task added


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

def test_check_conflicts_flags_overlapping_tasks():
    """A new task that overlaps an existing task's time window should return a warning."""
    base_time = datetime(2026, 4, 1, 9, 0)  # 9:00 AM
    owner = Owner(name="Dana", email="dana@example.com")
    pet = Pet(name="Pepper", species="Dog", age=4)
    owner.add_pet(pet)

    existing = Task(description="Morning walk", duration_minutes=30,
                    due_time=base_time)          # 9:00 – 9:30
    pet.add_task(existing)

    # Starts at 9:15 — overlaps the existing 9:00–9:30 window
    conflicting = Task(description="Training", duration_minutes=20,
                       due_time=base_time + timedelta(minutes=15))

    scheduler = Scheduler(owner)
    warning = scheduler.check_conflicts(conflicting)

    assert warning is not None
    assert "WARNING" in warning


def test_check_conflicts_no_warning_for_adjacent_tasks():
    """Tasks that are back-to-back (not overlapping) should not conflict."""
    base_time = datetime(2026, 4, 1, 9, 0)
    owner = Owner(name="Dana", email="dana@example.com")
    pet = Pet(name="Pepper", species="Dog", age=4)
    owner.add_pet(pet)

    first = Task(description="Walk", duration_minutes=30,
                 due_time=base_time)             # 9:00 – 9:30
    pet.add_task(first)

    # Starts exactly at 9:30 — adjacent, not overlapping
    second = Task(description="Feed", duration_minutes=10,
                  due_time=base_time + timedelta(minutes=30))

    scheduler = Scheduler(owner)
    assert scheduler.check_conflicts(second) is None
