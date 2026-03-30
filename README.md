# 🐾 PawPal+

**PawPal+** is a Streamlit app that helps busy pet owners plan, track, and schedule daily care tasks across multiple pets — with smart conflict detection, chronological sorting, and automatic recurring reminders.

---

## 📸 Demo

**Adding a pet** — register pets by name, species, and age; all registered pets are listed instantly below the form with their short IDs.

<a href="img/Screenshot 2026-03-30 at 1.57.13 AM.png" target="_blank">
  <img src="img/Screenshot 2026-03-30 at 1.57.13 AM.png" alt="PawPal+ — Add a Pet" width="800"/>
</a>

**Adding a task with priority** — assign a care task to any pet with duration, recurrence, priority (🔴 High / 🟡 Medium / 🟢 Low), and an optional due date/time. Task-type emojis are applied automatically based on keywords in the description.

<a href="img/Screenshot 2026-03-30 at 1.57.17 AM.png" target="_blank">
  <img src="img/Screenshot 2026-03-30 at 1.57.17 AM.png" alt="PawPal+ — Add a Task with Priority" width="800"/>
</a>

**Schedule dashboard** — summary metrics, filter-by-pet and filter-by-status dropdowns, a priority-sorted `st.table` (High → Medium → Low, then by time), and one-click Mark Complete buttons with priority and task-type emojis.

<a href="img/Screenshot 2026-03-30 at 1.57.21 AM.png" target="_blank">
  <img src="img/Screenshot 2026-03-30 at 1.57.21 AM.png" alt="PawPal+ — Schedule Dashboard" width="800"/>
</a>

---

## ✨ Features

### Pet & Owner Management
- Register an owner profile (name, email) that persists across the session.
- Add multiple pets with name, species, and age — each with their own independent task list.

### Task Creation with Conflict Detection
- Create care tasks (walks, feeding, medication, grooming, enrichment, etc.) with a description, duration, recurrence, priority, and optional due date/time.
- **Conflict detection** — before a task is saved, `Scheduler.check_conflicts()` uses interval-overlap arithmetic to scan all existing tasks. If the new task's time window overlaps any existing window, a `st.warning` banner immediately names both conflicting tasks, their exact time ranges, and the affected pet — so the owner can reschedule rather than accidentally double-book.

### Smart Scheduling Algorithms
- **Priority-aware sorting** — `Scheduler.sort_by_time()` sorts by priority tier first (High → Medium → Low), then by `due_time` within each tier. Tasks without a due time sort last within their tier. This ensures urgent tasks always surface before routine ones, even if their due time is later.
- **Next available slot** — `Scheduler.find_next_available_slot(duration_minutes)` uses a greedy gap-scan algorithm to find the earliest conflict-free window in the schedule. It sorts all timed tasks, then iterates through them advancing a candidate start time whenever an overlap is detected — returning the first gap that fits the requested duration.
- **Filter by pet** — `Scheduler.filter_by_pet(name)` scopes the schedule view to a single pet, making per-pet daily plans easy to read.
- **Filter by status** — `Scheduler.filter_by_status(complete)` returns only pending or completed tasks, letting owners quickly see what still needs to be done today.

### Automatic Recurring Tasks
- **Daily recurrence** — completing a `DAILY` task automatically schedules the next occurrence exactly 24 hours later, preserving the original task's priority.
- **Weekly recurrence** — completing a `WEEKLY` task schedules the next occurrence exactly 7 days later.
- One-off (`ONCE`) tasks are marked done without spawning a follow-up.

### Data Persistence
- All pets and tasks are saved to `data.json` automatically after every change (add pet, add task, mark complete).
- On next launch, `Owner.load_from_json()` restores the full state — no re-entry needed.
- Custom dictionary serialization (`to_dict` / `from_dict`) on every class handles `datetime` ISO strings and enum values without external libraries.

### Professional UI & Output
- **Priority color coding** — 🔴 High, 🟡 Medium, 🟢 Low labels in every task row and on Mark Complete buttons.
- **Task-type emojis** — descriptions are scanned for keywords (walk, feed, medication, groom, vet, play, train, water, clean) and matched to representative emojis (🦮 🍽️ 💊 ✂️ 🏥 🎾 🎓 💧 🧹).
- **Next slot finder** — inline UI widget to find the next open time window for a given task duration.

### Schedule Dashboard
- Summary metrics (total pets, pending tasks, completed tasks) rendered as `st.metric` cards.
- Filtered and priority-sorted task list displayed in a clean `st.table` with columns for Priority, Pet, Task, Duration, Due, Recurrence, and Status.
- One-click **Mark Complete** buttons per pending task; the UI refreshes immediately and confirms any auto-scheduled recurrence.

---

## 🏗️ Architecture

```
pawpal_system.py   — data model and scheduling logic (Owner, Pet, Task, Scheduler, Frequency, Priority)
app.py             — Streamlit UI; reads/writes only through Scheduler methods; auto-saves to data.json
data.json          — auto-generated persistence file (created on first run)
tests/             — pytest suite covering sorting, conflict detection, and recurrence
class_diagram.md   — up-to-date Mermaid UML class diagram
uml_final.png      — rendered UML diagram (final state)
```

### Class relationships

| Class | Owns / Uses |
|---|---|
| `Owner` | holds `List[Pet]`; provides `get_all_tasks()`, `save_to_json()`, `load_from_json()` |
| `Pet` | holds `List[Task]`; owned by `Owner` |
| `Task` | uses `Frequency` and `Priority` enums; owned by `Pet` |
| `Scheduler` | holds one `Owner`; all scheduling logic lives here |
| `Frequency` | enum — `ONCE`, `DAILY`, `WEEKLY` |
| `Priority` | enum — `LOW`, `MEDIUM`, `HIGH` |

### Agent Mode — how it was used

Challenge 1's `find_next_available_slot` algorithm was designed with Agent Mode. The agent was given the full `pawpal_system.py` file and prompted: *"Add a third algorithmic capability to the Scheduler class — given a desired task duration in minutes, find the earliest available time slot in the existing schedule without creating any conflicts."*

The agent proposed the greedy gap-scan approach: sort all timed tasks, maintain a sliding `candidate` start time, and advance it past any task whose window overlaps the candidate window. This O(n log n) strategy was chosen over a brute-force minute-by-minute search because it terminates in a single pass through the sorted list. The agent generated the method body and a plain-English explanation of the algorithm. The implementation was reviewed, the edge case of an empty schedule was verified (returns `start_from` immediately), and the method was integrated as-is.

Challenge 2's persistence layer was also implemented via Agent Mode. The agent was prompted: *"Add `save_to_json` and `load_from_json` methods to the Owner class in pawpal_system.py, then update the Streamlit session state in app.py to load this data on startup."* The agent identified that Python `datetime` objects and `Enum` values are not JSON-serializable and proposed the custom `to_dict` / `from_dict` pattern on each dataclass — converting datetimes to ISO strings and enums to their `.value` strings. The agent also placed the `_save()` helper in `app.py` and added its call at every mutation point (add pet, add task, mark complete) to keep the file in sync.

See [class_diagram.md](class_diagram.md) or [uml_final.png](uml_final.png) for the full diagram.

---

## 🧪 Tests

```bash
PYTHONPATH=. python -m pytest tests/test_pawpal.py -v
```

| Test | Behavior verified |
|---|---|
| `test_mark_complete_changes_status` | `Task.mark_complete()` flips `is_complete` to `True` |
| `test_add_task_increases_pet_task_count` | `Pet.add_task()` appends to the pet's task list |
| `test_get_upcoming_tasks_sorted_chronologically` | `get_upcoming_tasks()` returns incomplete tasks in ascending due-time order, undated last |
| `test_mark_daily_task_complete_spawns_next_day` | Completing a `DAILY` task creates a new task due exactly 24 hours later |
| `test_mark_once_task_complete_does_not_spawn` | Completing a `ONCE` task does **not** create a follow-up |
| `test_check_conflicts_flags_overlapping_tasks` | `check_conflicts()` returns a warning string when windows overlap |
| `test_check_conflicts_no_warning_for_adjacent_tasks` | Back-to-back tasks (no gap, no overlap) do **not** trigger a warning |

**Confidence: ★★★★☆ (4/5)** — all 7 tests pass; edge cases around timezone-naive/aware datetimes and multi-pet simultaneous conflicts are not yet covered.

---

## 🚀 Getting Started

### Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## 📐 UML Diagram

The final class diagram reflects all methods built across every phase of development.

![PawPal+ UML Class Diagram](uml_final.png)
