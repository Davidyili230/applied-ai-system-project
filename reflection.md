# PawPal+ Project Reflection

## 1. System Design

**a. Three core user actions**

1. **Add a pet** — the owner enters their pet's name, species, and age to create a profile in the system.
2. **Schedule a care task** — the owner adds a task (walk, feeding, medication, grooming, etc.) with a due time, duration, and recurrence to a pet's plan.
3. **View today's plan** — the owner sees all upcoming tasks sorted by time, with conflict warnings if any tasks overlap.

**b. Initial design**

My initial UML design centered on three core classes: `Task`, `Pet`, and `Scheduler`.

- **Task** is a dataclass that holds a single care activity. It stores the task's id, description, due time, duration in minutes, completion status, and recurrence frequency (Once, Daily, or Weekly). It has a single `mark_complete()` method to flip its completion flag.

- **Pet** is a dataclass representing a pet's profile. It stores the pet's id, name, species, and age, and maintains a list of `Task` objects associated with that pet. It exposes an `add_task()` method to append new tasks to its list.

- **Scheduler** is the coordinating class that manages all pets and their tasks. It holds a list of `Pet` objects and provides methods to aggregate tasks across all pets (`get_all_tasks`), retrieve upcoming tasks in sorted order (`get_upcoming_tasks`), detect scheduling conflicts for a new task (`check_conflicts`), and generate next instances of recurring tasks (`generate_recurring_tasks`).

**c. Design changes**

Yes, the design changed during implementation. Initially I expected the `Task` class to handle conflict detection by comparing its own time range against others, but I moved that responsibility into `Scheduler.check_conflicts()` instead. The `Scheduler` already has visibility into every pet's task list, so it was a more natural place to compare time ranges (start time through start time plus duration) across all tasks. Giving conflict logic to `Task` would have required passing in external task lists, which violated the principle that a task should only know about itself.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
