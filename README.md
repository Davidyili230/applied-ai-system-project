# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

PawPal+ now includes three algorithmic scheduling features:

- **Sorting** — `sort_by_time()` orders any list of tasks by `due_time` ascending; tasks with no due time sort to the end so urgent items always surface first.
- **Filtering** — `filter_by_status(complete)` returns only pending or completed tasks, and `filter_by_pet(name)` scopes the task list to a single pet, making it easy to view a per-pet schedule.
- **Conflict detection** — `check_conflicts(task)` uses interval-overlap arithmetic to scan all existing tasks before a new one is committed. If the new task's time window overlaps any existing window it returns a human-readable warning so the owner can reschedule rather than double-book.

Together these features give owners a clear, ordered view of the day and prevent accidental scheduling collisions across multiple pets.

## Testing PawPal+

### Running the test suite

```bash
PYTHONPATH=. python -m pytest tests/test_pawpal.py -v
```

### What the tests cover

| Test | Behavior verified |
|------|-------------------|
| `test_mark_complete_changes_status` | `Task.mark_complete()` flips `is_complete` to `True` |
| `test_add_task_increases_pet_task_count` | `Pet.add_task()` appends tasks to the pet's list |
| `test_get_upcoming_tasks_sorted_chronologically` | `Scheduler.get_upcoming_tasks()` returns incomplete tasks in ascending `due_time` order, with undated tasks last |
| `test_mark_daily_task_complete_spawns_next_day` | Completing a `DAILY` task creates a new task due exactly 24 hours later |
| `test_mark_once_task_complete_does_not_spawn` | Completing a `ONCE` task does **not** create a follow-up task |
| `test_check_conflicts_flags_overlapping_tasks` | `check_conflicts()` returns a `WARNING` when a new task's window overlaps an existing one |
| `test_check_conflicts_no_warning_for_adjacent_tasks` | Back-to-back tasks (no overlap) do **not** trigger a conflict warning |

### Confidence Level

**★★★★☆ (4 / 5)**

All 7 tests pass and cover the three highest-risk behaviors: chronological sorting, recurring-task generation, and conflict detection. One star is held back because edge cases around timezone-naive vs timezone-aware datetimes and multi-pet conflict scenarios are not yet tested.

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
