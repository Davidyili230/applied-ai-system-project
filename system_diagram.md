# PawPal+ System Diagram

```
╔══════════════════════════════════════════════════════════════════════╗
║                        USER INTERFACES                               ║
║                                                                      ║
║   ┌──────────────────────────┐   ┌──────────────────────────────┐   ║
║   │    Manual Tab (app.py)   │   │    AI Chat Tab (app.py)      │   ║
║   │  - Add pets / tasks      │   │  - Natural language input    │   ║
║   │  - View schedule         │   │  - Persistent chat history   │   ║
║   │  - Mark complete         │   │  - AI response display       │   ║
║   │  - Find open time slots  │   │                              │   ║
║   └────────────┬─────────────┘   └──────────────┬───────────────┘   ║
╚════════════════╪════════════════════════════════╪═══════════════════╝
                 │ direct calls                   │ user message
                 ▼                                ▼
╔════════════════════════════╗   ╔══════════════════════════════════════╗
║   SCHEDULER (pawpal_sys)   ║   ║      AI ASSISTANT (ai_assistant.py)  ║
║                            ║   ║                                      ║
║  sort_by_time()            ║   ║  ┌─────────────────────────────────┐ ║
║  filter_by_status()        ║   ║  │  KnowledgeBase (RAG Retriever)  │ ║
║  filter_by_pet()           ║◄──╫──│  ┌─────────┐ ┌────────────────┐│ ║
║  check_conflicts()         ║   ║  │  │dog_care │ │  cat_care.md   ││ ║
║  find_next_available_slot()║   ║  │  │  .md    │ │ general_care.md││ ║
║  mark_task_complete()      ║   ║  │  └─────────┘ └────────────────┘│ ║
╚════════════════╪═══════════╝   ║  │  retrieve(query) → top doc      │ ║
                 │               ║  └──────────────┬──────────────────┘ ║
                 │               ║                 │ injected context   ║
                 ▼               ║                 ▼                    ║
╔════════════════════════════╗   ║  ┌─────────────────────────────────┐ ║
║  DATA MODEL (pawpal_sys)   ║   ║  │  PawPalAI — Agentic Loop        │ ║
║                            ║   ║  │  (claude-haiku-4-5)             │ ║
║  Owner ─► Pet ─► Task      ║◄──╫──│                                 │ ║
║                            ║   ║  │  system prompt + history        │ ║
║  Priority  (HIGH/MED/LOW)  ║   ║  │        ↓                        │ ║
║  Frequency (ONCE/DAILY/    ║   ║  │  Claude API call                │ ║
║            WEEKLY)         ║   ║  │        ↓                        │ ║
╚════════════════╪═══════════╝   ║  │  stop_reason == tool_use?       │ ║
                 │               ║  │    YES → _dispatch(tool)        │ ║
                 ▼               ║  │         → call Scheduler        │ ║
╔════════════════════════════╗   ║  │         → save_callback()       │ ║
║    PERSISTENCE (data.json) ║   ║  │    NO  → return text response   │ ║
║                            ║   ║  │  (max 8 tool rounds)            │ ║
║  Owner / Pet / Task state  ║   ║  └─────────────────────────────────┘ ║
║  datetime → ISO string     ║   ╚══════════════════════════════════════╝
║  Enum → .value             ║
║  load_from_json() on start ║
╚════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════╗
║                  HUMAN / TESTING CHECKPOINTS                         ║
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐    ║
║  │  Human-in-the-Loop                                          │    ║
║  │  • User reviews AI-suggested tasks before accepting them    │    ║
║  │  • "Mark Complete" is always a deliberate user action       │    ║
║  │  • Conflict warnings surfaced to user before task is saved  │    ║
║  └─────────────────────────────────────────────────────────────┘    ║
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐    ║
║  │  Automated Testing (tests/test_pawpal.py — 7 pytest tests)  │    ║
║  │  • mark_complete() flips status                             │    ║
║  │  • DAILY tasks auto-spawn next occurrence (+24h)            │    ║
║  │  • ONCE tasks do NOT spawn follow-ups                       │    ║
║  │  • Upcoming tasks sorted chronologically                    │    ║
║  │  • Overlap detection: overlapping → warning, adjacent → OK  │    ║
║  └─────────────────────────────────────────────────────────────┘    ║
║                                                                      ║
║  ┌─────────────────────────────────────────────────────────────┐    ║
║  │  Demo Script (main.py) — manual evaluation                  │    ║
║  │  • Runs 7 representative scenarios end-to-end               │    ║
║  │  • Checks sorting, filtering, recurrence, conflict cases    │    ║
║  └─────────────────────────────────────────────────────────────┘    ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Data Flow Summary

User input hits either the **Manual tab** (direct Scheduler calls) or the **AI Chat tab**
(Claude + RAG → agentic tool dispatch → Scheduler), and every mutation lands in
`data.json` which is reloaded on app start.

## Components

| Component | File | Role |
|---|---|---|
| Manual UI | `app.py` | Form-based pet/task management |
| AI Chat UI | `app.py` | Natural language interface |
| Scheduler | `pawpal_system.py` | Sorting, filtering, conflict detection |
| Data Model | `pawpal_system.py` | Owner → Pet → Task hierarchy |
| RAG Retriever | `ai_assistant.py` | Token-overlap doc scoring |
| Agentic AI | `ai_assistant.py` | Claude with 7 tools, up to 8 rounds |
| Persistence | `data.json` | JSON state (auto-created) |
| Tests | `tests/test_pawpal.py` | 7 automated pytest cases |
| Demo | `main.py` | 7 manual evaluation scenarios |
