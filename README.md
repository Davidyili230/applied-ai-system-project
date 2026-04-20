# PawPal+

**PawPal+** is an AI-powered pet care management system for busy pet owners. It combines smart scheduling algorithms with a Claude-backed assistant that can understand natural language requests, execute multi-step actions, and provide grounded advice — all in a clean Streamlit interface.

---

## Original Project (Modules 1–3)

The original PawPal+ (Modules 1–3) was a pure-Python scheduling engine for multi-pet households. Its goals were to let a single owner register multiple pets, create time-boxed care tasks with recurrence rules, detect scheduling conflicts before they were committed, and automatically spawn the next occurrence of a recurring task when the current one was marked complete. The system already included priority-aware sorting, a greedy next-available-slot algorithm, and full JSON persistence — no AI involved.

---

## Title and Summary

**PawPal+ — Smart Pet Care Scheduling with an AI Assistant**

Managing daily care across multiple pets is error-prone: double-booked tasks, forgotten medications, and no easy way to see which animal needs attention next. PawPal+ solves this with a scheduling engine that prevents conflicts before they happen, resurfaces high-priority tasks automatically, and adds a Claude-powered AI assistant that can plan an entire care routine from a single sentence. It matters because reliability in a care schedule has real health consequences for animals, and a tool that actively prevents mistakes is more valuable than one that simply records them.

---

## Architecture Overview

The system is organized into three independent layers that only communicate through well-defined interfaces:

```
┌─────────────────────────────────────────────────────────┐
│  Streamlit UI  (app.py)                                 │
│  Tab 1: Manual forms — add pets, create tasks,          │
│          mark complete, filter, find next slot          │
│  Tab 2: AI Chat — natural-language interface            │
└───────────────────┬─────────────────────────────────────┘
                    │ calls Scheduler methods
┌───────────────────▼─────────────────────────────────────┐
│  Domain Model + Scheduling Engine  (pawpal_system.py)   │
│  Owner → Pet → Task                                     │
│  Scheduler: conflict detection, sorting, recurrence,    │
│             next-slot algorithm, JSON persistence       │
└───────────────────┬─────────────────────────────────────┘
                    │ reads/writes
          ┌─────────▼─────────┐
          │   data.json       │  auto-generated persistence
          └───────────────────┘

┌─────────────────────────────────────────────────────────┐
│  AI Layer  (ai_assistant.py)                            │
│  ┌──────────────┐   ┌──────────────────────────────┐   │
│  │ KnowledgeBase│   │ Agentic Loop (≤8 rounds)     │   │
│  │ RAG retriever│   │ 7 tools → Scheduler methods  │   │
│  │ 3 markdown   │   │ claude-haiku-4-5 backbone    │   │
│  │ docs         │   │                              │   │
│  └──────────────┘   └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
          │ reads pet care context from
┌─────────▼─────────────────┐
│  knowledge_base/          │
│  dog_care.md              │
│  cat_care.md              │
│  general_care.md          │
└───────────────────────────┘
```

**Key design choice:** The AI layer never touches `data.json` directly. It only calls the same seven `Scheduler` methods the manual UI uses — so AI-driven changes go through identical validation (conflict detection, recurrence logic) as manual ones.

### Class relationships

| Class | Responsibility |
|---|---|
| `Owner` | Holds `List[Pet]`; owns `save_to_json` / `load_from_json` |
| `Pet` | Holds `List[Task]`; owned by `Owner` |
| `Task` | Single care activity — description, duration, due time, recurrence, priority, completion state |
| `Scheduler` | All scheduling logic — conflict detection, sorting, filtering, next-slot algorithm, recurrence |
| `Frequency` | Enum — `ONCE`, `DAILY`, `WEEKLY` |
| `Priority` | Enum — `LOW`, `MEDIUM`, `HIGH` |
| `KnowledgeBase` | Token-overlap RAG retriever over three markdown docs |

---

## Setup Instructions

### Prerequisites

- Python 3.10+
- An Anthropic API key (only required for the AI Assistant tab)

### Install

```bash
git clone <repo-url>
cd applied-ai-system-project

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configure API key (AI tab only)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

The app runs without the key — the AI Assistant tab is hidden if the `anthropic` library is unavailable or the key is not set. All manual scheduling features work without it.

### Run the app

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. All data is saved automatically to `data.json` and restored on restart.

### Run the demo script (no browser required)

```bash
python main.py
```

Runs seven scripted scenarios: task sorting, status filtering, per-pet filtering, recurring task auto-scheduling, and conflict detection.

### Run the test suite

```bash
PYTHONPATH=. python -m pytest tests/test_pawpal.py -v
```

---

## Sample Interactions

### 1 — Manual: Conflict detection at task creation

The owner tries to book a vet appointment at 7:15 AM for 60 minutes. Buddy already has a morning walk at 7:00 AM for 30 minutes (window: 7:00–7:30).

**System output (inline warning before saving):**

```
⚠️  WARNING: 'Vet appointment' (07:15–08:15) conflicts with
    'Morning walk' (07:00–07:30) for Buddy.
    Consider rescheduling to avoid a double-booking.
```

The task is not saved until the owner picks a different time. The conflict check uses interval-overlap arithmetic (`new_start < existing_end AND new_end > existing_start`) and scans every task across every pet.

---

### 2 — Manual: Completing a daily task auto-schedules the next occurrence

The owner clicks **Mark Complete** on Buddy's morning walk (due today at 7:00 AM, recurrence: DAILY).

**Before:**
```
[ ]  07:00 AM  |  Morning walk  (30 min)  DAILY
```

**After (system output in UI):**
```
✅  'Morning walk' marked complete.
    Next occurrence scheduled for tomorrow at 07:00 AM.
```

**Buddy's updated task list:**
```
[x]  Today 07:00 AM   |  Morning walk  (30 min)  [DONE]
[ ]  Tomorrow 07:00 AM|  Morning walk  (30 min)  DAILY
```

No manual re-entry. The new task inherits the same description, duration, and priority as the original.

---

### 3 — AI Assistant: Multi-step natural language request

**User input:**
> "Add a dog named Buddy, age 3. Then schedule a daily morning walk at 7 AM for 30 minutes and a weekly vet check at 10 AM on Saturdays for 60 minutes. What's Buddy's schedule look like?"

**Claude's agentic execution (internal tool calls, shown for transparency):**

```
→ add_pet("Buddy", "dog", 3)
  ← {"status": "success", "pet_id": "abc123"}

→ add_task("Buddy", "Morning walk", 30, "high", "daily", "2026-04-21T07:00:00")
  ← {"status": "success", "task_id": "t1", "conflict": null}

→ add_task("Buddy", "Vet check", 60, "high", "weekly", "2026-04-25T10:00:00")
  ← {"status": "success", "task_id": "t2", "conflict": null}

→ list_tasks("Buddy", "pending")
  ← [{"description": "Morning walk", "due": "07:00", "recurrence": "daily"},
     {"description": "Vet check", "due": "10:00 Sat", "recurrence": "weekly"}]
```

**Claude's response to the user:**

```
I've added Buddy (3-year-old dog) and set up two recurring tasks:

• 🦮 Morning walk — every day at 7:00 AM, 30 minutes (High priority)
• 🏥 Vet check — every Saturday at 10:00 AM, 60 minutes (High priority)

For a 3-year-old dog, daily walks of at least 30 minutes are ideal for
maintaining a healthy weight and preventing boredom-related behaviors.
Annual vet visits are recommended at this age; your weekly slot gives
you flexibility to adjust as needed.

Both tasks are saved and will auto-reschedule when you mark them complete.
```

The RAG layer retrieved `dog_care.md` to ground the advice about exercise frequency and vet schedules. The entire exchange — two pet mutations, one read, and a grounded reply — happened in a single user message.

---

### 4 — AI Assistant: Finding the next available slot

**User input:**
> "I need to add a grooming session for Whiskers today. It'll take about 45 minutes. When's the earliest I can fit it in without conflicts?"

**Claude's tool call:**
```
→ find_available_slot(45)
  ← {"slot": "2026-04-20T14:30:00", "message": "Next open 45-minute window starts at 2:30 PM"}
```

**Claude's response:**
```
The earliest conflict-free 45-minute window for a grooming session is
2:30 PM today. I can add it now if you'd like — just confirm and I'll
schedule ✂️ Whiskers' grooming at 2:30 PM.
```

---

## Design Decisions

### 1. Conflict detection is global (across all pets), not per-pet

`Scheduler.check_conflicts()` scans every task from every pet. This means a dog walk and a simultaneous cat feeding register as a conflict even though they involve different animals.

**Tradeoff:** This is intentional for the MVP, which assumes a single owner managing all pets alone. Any two overlapping tasks genuinely compete for one person's time. A multi-caregiver system would need per-person scoping — that's the one clear extension point if the scope grows.

### 2. Recurring task logic lives in `mark_task_complete`, not `generate_recurring_tasks`

The original design had a separate `generate_recurring_tasks()` sweep method, but it created tasks that were never attached to any pet (an "orphaned task" bug flagged during AI review). Moving the spawn logic into `mark_task_complete` means a new occurrence is always attached to the correct pet immediately and can never be lost.

### 3. Pet context is resolved in the UI layer, not stored on `Task`

AI review suggested adding a `pet_id` field to `Task` so flat task lists could identify their owning pet. This was rejected: `Task` is already stored inside `pet.tasks`, making `pet_id` a second source of truth with no enforcement that both stay consistent. Instead, a `pet_lookup` dict (`task.id → pet.name`) is built at render time in `app.py` — display concerns stay in the display layer.

### 4. RAG retrieval uses token-overlap scoring, not embeddings

The knowledge base has three short documents. A full embedding model would add latency and API cost for a search space that is small enough for simple token overlap to produce accurate results. The scorer picks the document with the most shared words with the user's query, injects it into the system prompt, and discards it after the response — no vector database required.

### 5. The agentic loop cap is 8 rounds

Eight rounds is enough to handle the most complex realistic request (add pet → add multiple tasks → query schedule → respond) while preventing runaway API spend if Claude gets stuck in a tool-call loop. The cap is explicit and documented in `ai_assistant.py`.

---

## Testing Summary

### What was tested

Seven pytest tests cover the three behaviors most likely to fail silently:

| Test | Behavior |
|---|---|
| `test_mark_complete_changes_status` | `mark_complete()` flips `is_complete` |
| `test_add_task_increases_pet_task_count` | `Pet.add_task()` appends correctly |
| `test_get_upcoming_tasks_sorted_chronologically` | Incomplete tasks in ascending due-time order; undated tasks last |
| `test_mark_daily_task_complete_spawns_next_day` | DAILY task completion creates a new task due +24 hours |
| `test_mark_once_task_complete_does_not_spawn` | ONCE task completion creates no follow-up |
| `test_check_conflicts_flags_overlapping_tasks` | Overlapping time windows return a warning string |
| `test_check_conflicts_no_warning_for_adjacent_tasks` | Back-to-back (non-overlapping) tasks pass cleanly |

All 7 pass. **Confidence: 4/5.**

### What didn't get covered

- **Multi-pet simultaneous conflict policy** — the global conflict detector should warn on two pets' tasks at the same time, but no test explicitly verifies this policy decision.
- **Timezone-aware datetimes** — all test datetimes are naive. A timezone-aware `datetime.now()` from some environments would raise `TypeError` in comparisons.
- **Weekly recurrence end-to-end** — only the `DAILY` branch of `mark_task_complete` is tested through a full pytest. `WEEKLY` uses the same logic with `timedelta(weeks=1)` but is exercised only in `main.py`.

### What I learned

Silent failures are harder to catch than exceptions. A broken sort doesn't raise an error — it just returns tasks in the wrong order. The most valuable tests were for behaviors where a bug would look like "nothing happened": sorting, recurrence spawning, and the false-negative conflict case (adjacent tasks that should *not* trigger a warning). Writing those tests first would have caught the orphaned-task bug in `generate_recurring_tasks` before it reached code review.

---

## Reflection

### What this project taught me about AI and problem-solving

**AI tools are most valuable after you have made the hard design decisions, not before.** Early in the project, vague prompts ("build me a scheduler") produced generic suggestions that didn't fit the architecture I was building. Once I had a clear class diagram and could prompt with specific constraints ("I have a `Scheduler` that holds one `Owner` which holds many `Pets` — write the body of `mark_task_complete` given this structure"), the AI produced accurate, immediately usable output.

The corollary is that the cost of a blurry spec falls on the human, not the model. Every time I accepted a suggestion that felt reasonable in isolation but violated an existing design decision, I spent more time reconciling the mismatch than I would have spent writing the code myself. Being the lead architect means writing the spec — clearly enough that the AI can implement it, and clearly enough that you can tell immediately whether its output fits.

**The agentic AI pattern changed how I think about user interfaces.** A traditional UI requires the user to know which form to fill out, in what order, with what values. An agentic assistant inverts that: the user states an intent, and the system figures out the sequence. Designing the tool definitions for the AI layer forced me to think about what operations are truly atomic — what is the smallest action the AI might need to take independently? That exercise clarified the domain model in ways that purely UI-driven design had not.

**Conflict detection is a product decision, not just an algorithm.** The interval-overlap math is straightforward. The hard question is: when *should* a conflict be flagged? The decision to scope conflicts globally (across all pets) rather than per-pet required me to think about the user — a single owner managing multiple animals alone — and document the assumption explicitly. That kind of reasoning about who uses the system and how became as important as any implementation detail.

**Testing for absence is as important as testing for presence.** The most critical test in the suite is `test_check_conflicts_no_warning_for_adjacent_tasks`. An over-eager conflict detector that fires on back-to-back tasks would make the app unusable — and it would fail silently, returning a warning string instead of raising an exception. Writing tests that assert a warning is *not* returned taught me to think about the false-positive failure mode, not just the false-negative one.

---

## Project Structure

```
applied-ai-system-project/
├── app.py                  # Streamlit UI (manual + AI tabs)
├── pawpal_system.py        # Domain model and scheduling engine
├── ai_assistant.py         # RAG retriever and agentic tool loop
├── main.py                 # Demo/evaluation script (no browser needed)
├── requirements.txt        # streamlit, pytest, anthropic
├── data.json               # Auto-generated persistence (created on first run)
├── tests/
│   └── test_pawpal.py      # 7 pytest tests
├── knowledge_base/
│   ├── dog_care.md         # RAG context: dog feeding, exercise, vet schedules
│   ├── cat_care.md         # RAG context: cat feeding, litter, play, vet schedules
│   └── general_care.md     # RAG context: priority framework, task duration reference
├── class_diagram.md        # Mermaid UML class diagram
├── system_diagram.md       # ASCII system architecture diagram
├── reflection.md           # Extended design and AI collaboration notes
└── img/                    # UI screenshots
```
