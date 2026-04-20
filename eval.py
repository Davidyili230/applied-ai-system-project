"""
PawPal+ Evaluation Harness
==========================
Runs a suite of deterministic unit tests (no API key required) and an optional
live integration test against the Claude API (pass --live to enable).

Usage:
    python eval.py           # run offline tests only
    python eval.py --live    # also run live Claude API tests
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Test result tracking
# ---------------------------------------------------------------------------

_results: list[dict] = []  # {"category", "test", "result", "score"}


def _record(category: str, test: str, passed: bool, score: Optional[float] = None) -> None:
    _results.append({
        "category": category,
        "test": test,
        "result": "PASS" if passed else "FAIL",
        "score": 1.0 if passed else 0.0 if score is None else score,
    })


def _run(category: str, test: str, fn):
    """Execute *fn* and record pass/fail, catching any exception as a failure."""
    try:
        fn()
        _record(category, test, True)
    except AssertionError as exc:
        _record(category, test, False)
        print(f"  [FAIL] {category} / {test}: {exc}")
    except Exception as exc:
        _record(category, test, False)
        print(f"  [ERROR] {category} / {test}: {exc}")
        traceback.print_exc()


# ===========================================================================
# Category 1: RAG tests (no API needed)
# ===========================================================================

def _rag_tests():
    from ai_assistant import KnowledgeBase

    # Load the real knowledge_base/ directory
    kb = KnowledgeBase("knowledge_base")

    # ---- Test 1: Dog query retrieves dog_care ----
    # "dog walk exercise breed" has 0.75 overlap with dog_care vs 0.5 for general_care, 0.0 for cat_care
    def test_dog_query_retrieves_dog_care():
        kb.retrieve("dog walk exercise breed")
        assert kb.last_retrieved_doc == "dog_care", (
            f"Expected 'dog_care', got '{kb.last_retrieved_doc}'"
        )
        assert kb.last_confidence > 0.0, "Confidence should be > 0 for a relevant query"

    _run("RAG", "Dog query retrieves dog_care", test_dog_query_retrieves_dog_care)

    # ---- Test 2: Cat query retrieves cat_care ----
    def test_cat_query_retrieves_cat_care():
        kb.retrieve("cat grooming brushing feeding cats")
        assert kb.last_retrieved_doc == "cat_care", (
            f"Expected 'cat_care', got '{kb.last_retrieved_doc}'"
        )
        assert kb.last_confidence > 0.0

    _run("RAG", "Cat query retrieves cat_care", test_cat_query_retrieves_cat_care)

    # ---- Test 3: General scheduling query retrieves general_care ----
    # "pet care priority framework conflict" has 1.0 overlap with general_care
    def test_general_query_retrieves_general_care():
        kb.retrieve("pet care priority framework conflict")
        assert kb.last_retrieved_doc == "general_care", (
            f"Expected 'general_care', got '{kb.last_retrieved_doc}'"
        )
        assert kb.last_confidence > 0.0

    _run("RAG", "General query retrieves general_care", test_general_query_retrieves_general_care)

    # ---- Test 4: Zero-overlap query returns empty string ----
    def test_zero_overlap_returns_empty():
        result = kb.retrieve("xylophone quantum saxophone")
        assert result == "", f"Expected empty string, got: {result!r}"
        assert kb.last_confidence == 0.0
        assert kb.last_retrieved_doc == ""

    _run("RAG", "Zero-overlap query returns empty string", test_zero_overlap_returns_empty)

    # ---- Test 5: get_all_scores returns one score per document ----
    def test_get_all_scores_structure():
        scores = kb.get_all_scores("dog feeding walk daily")
        assert isinstance(scores, dict), "get_all_scores must return a dict"
        assert len(scores) == len(kb.docs), (
            f"Expected {len(kb.docs)} scores, got {len(scores)}"
        )
        for name, score in scores.items():
            assert 0.0 <= score <= 1.0, f"Score for '{name}' out of range: {score}"

    _run("RAG", "get_all_scores returns normalized scores", test_get_all_scores_structure)


# ===========================================================================
# Category 2: Scheduler tests (no API needed)
# ===========================================================================

def _scheduler_tests():
    from pawpal_system import Owner, Pet, Task, Scheduler, Frequency, Priority

    def _fresh():
        """Return a clean owner + scheduler with one dog."""
        owner = Owner(name="TestOwner", email="test@example.com")
        dog = Pet(name="Buddy", species="dog", age=3)
        owner.add_pet(dog)
        return owner, Scheduler(owner)

    # ---- Test 1: Add pets and verify count ----
    def test_add_pets():
        owner, sched = _fresh()
        assert len(owner.pets) == 1
        owner.add_pet(Pet(name="Whiskers", species="cat", age=2))
        assert len(owner.pets) == 2

    _run("Scheduler", "Add pets and verify count", test_add_pets)

    # ---- Test 2: Add tasks and list them ----
    def test_add_tasks():
        owner, sched = _fresh()
        t = Task(description="Morning walk", duration_minutes=30)
        owner.pets[0].add_task(t)
        all_tasks = sched.get_all_tasks()
        assert len(all_tasks) == 1
        assert all_tasks[0].description == "Morning walk"

    _run("Scheduler", "Add tasks and list them", test_add_tasks)

    # ---- Test 3: Conflict detection fires on overlapping tasks ----
    def test_conflict_detection():
        owner, sched = _fresh()
        base_time = datetime(2025, 6, 1, 9, 0)
        t1 = Task(description="Walk", duration_minutes=60, due_time=base_time)
        owner.pets[0].add_task(t1)
        # t2 starts 30 minutes into t1 — overlaps
        t2 = Task(description="Bath", duration_minutes=30, due_time=base_time + timedelta(minutes=30))
        conflict = sched.check_conflicts(t2)
        assert conflict is not None, "Expected a conflict warning"
        assert "Walk" in conflict or "Bath" in conflict

    _run("Scheduler", "Conflict detection on overlapping tasks", test_conflict_detection)

    # ---- Test 4: No conflict for non-overlapping tasks ----
    def test_no_conflict_separate_tasks():
        owner, sched = _fresh()
        base_time = datetime(2025, 6, 1, 9, 0)
        t1 = Task(description="Walk", duration_minutes=30, due_time=base_time)
        owner.pets[0].add_task(t1)
        # t2 starts after t1 ends
        t2 = Task(description="Feed", duration_minutes=15, due_time=base_time + timedelta(minutes=30))
        conflict = sched.check_conflicts(t2)
        assert conflict is None, f"Expected no conflict, got: {conflict}"

    _run("Scheduler", "No conflict for non-overlapping tasks", test_no_conflict_separate_tasks)

    # ---- Test 5: Mark complete ----
    def test_mark_complete():
        owner, sched = _fresh()
        t = Task(description="Vet visit", duration_minutes=60)
        owner.pets[0].add_task(t)
        result = sched.mark_task_complete(t.id)
        assert result is True, "mark_task_complete should return True"
        assert owner.pets[0].tasks[0].is_complete is True

    _run("Scheduler", "Mark task complete", test_mark_complete)

    # ---- Test 6: Find slot with no existing tasks returns start_from ----
    def test_find_slot_empty():
        owner, sched = _fresh()
        start = datetime(2025, 6, 1, 8, 0)
        slot = sched.find_next_available_slot(30, start_from=start)
        assert slot == start, f"Expected {start}, got {slot}"

    _run("Scheduler", "find_next_available_slot with no tasks", test_find_slot_empty)

    # ---- Test 7: Find slot skips conflicting window ----
    def test_find_slot_skips_conflict():
        owner, sched = _fresh()
        start = datetime(2025, 6, 1, 8, 0)
        # Block 8:00–9:00
        t = Task(description="Long walk", duration_minutes=60, due_time=start)
        owner.pets[0].add_task(t)
        slot = sched.find_next_available_slot(30, start_from=start)
        assert slot >= start + timedelta(minutes=60), (
            f"Expected slot at or after 9:00, got {slot}"
        )

    _run("Scheduler", "find_next_available_slot skips conflict", test_find_slot_skips_conflict)


# ===========================================================================
# Category 3: Custom KB test (no API needed)
# ===========================================================================

def _custom_kb_tests():
    from ai_assistant import KnowledgeBase

    # Use a temp KB with no files to avoid bleed from real docs
    kb = KnowledgeBase.__new__(KnowledgeBase)
    kb.docs = {}
    kb.last_confidence = 0.0
    kb.last_retrieved_doc = ""

    # ---- Test 1: add_document adds to kb.docs ----
    def test_add_document_stored():
        kb.add_document("hamster_care", "Hamsters need fresh vegetables and wheel exercise daily.")
        assert "hamster_care" in kb.docs
        assert "Hamsters" in kb.docs["hamster_care"]

    _run("Custom KB", "add_document stores content", test_add_document_stored)

    # ---- Test 2: Custom doc is retrievable with high confidence ----
    def test_custom_doc_retrieved():
        kb.add_document("hamster_care", "Hamsters need fresh vegetables and wheel exercise daily.")
        result = kb.retrieve("hamsters vegetables exercise")
        assert kb.last_retrieved_doc == "hamster_care", (
            f"Expected 'hamster_care', got '{kb.last_retrieved_doc}'"
        )
        assert kb.last_confidence > 0.5, (
            f"Expected high confidence, got {kb.last_confidence:.2f}"
        )
        assert result != ""

    _run("Custom KB", "Custom doc retrieved with high confidence", test_custom_doc_retrieved)

    # ---- Test 3: Multiple docs — correct one wins ----
    def test_multiple_docs_correct_winner():
        kb.add_document("rabbit_care", "Rabbits eat hay pellets and need daily grooming.")
        kb.add_document("fish_care", "Fish require clean water and daily feeding of fish flakes.")
        kb.retrieve("fish flakes water feeding")
        assert kb.last_retrieved_doc == "fish_care", (
            f"Expected 'fish_care', got '{kb.last_retrieved_doc}'"
        )

    _run("Custom KB", "Correct doc wins when multiple are present", test_multiple_docs_correct_winner)


# ===========================================================================
# Category 4: Few-shot system prompt test (no API needed)
# ===========================================================================

def _fewshot_tests():
    from ai_assistant import PawPalAI, FEW_SHOT_EXAMPLES
    from pawpal_system import Owner

    owner = Owner(name="TestOwner", email="test@example.com")

    # Instantiate both variants.  We intercept the system prompt by monkey-patching
    # client.messages.create so no real API call is made.
    class _FakeBlock:
        type = "text"
        text = "ok"

    class _FakeResponse:
        stop_reason = "end_turn"
        content = [_FakeBlock()]

    captured_prompts: dict[str, str] = {}

    def _make_fake_create(label: str):
        def _fake_create(**kwargs):
            captured_prompts[label] = kwargs.get("system", "")
            return _FakeResponse()
        return _fake_create

    # ---- Test 1: specialized=False does NOT include FEW_SHOT_EXAMPLES ----
    def test_no_fewshot_when_not_specialized():
        ai = PawPalAI(owner, kb_dir="knowledge_base", specialized=False)
        ai.client.messages.create = _make_fake_create("plain")
        ai.chat("hello")
        assert "STYLE GUIDE AND FEW-SHOT EXAMPLES" not in captured_prompts.get("plain", ""), (
            "FEW_SHOT_EXAMPLES should NOT appear in plain system prompt"
        )

    _run("Few-shot", "specialized=False excludes FEW_SHOT_EXAMPLES", test_no_fewshot_when_not_specialized)

    # ---- Test 2: specialized=True DOES include FEW_SHOT_EXAMPLES ----
    def test_fewshot_when_specialized():
        ai = PawPalAI(owner, kb_dir="knowledge_base", specialized=True)
        ai.client.messages.create = _make_fake_create("specialized")
        ai.chat("hello")
        assert "STYLE GUIDE AND FEW-SHOT EXAMPLES" in captured_prompts.get("specialized", ""), (
            "FEW_SHOT_EXAMPLES should appear in specialized system prompt"
        )

    _run("Few-shot", "specialized=True includes FEW_SHOT_EXAMPLES", test_fewshot_when_specialized)

    # ---- Test 3: FEW_SHOT_EXAMPLES content has at least 3 exchanges ----
    def test_fewshot_examples_content():
        # Each example starts with "User:" — count occurrences
        exchange_count = FEW_SHOT_EXAMPLES.count("User:")
        assert exchange_count >= 3, (
            f"Expected at least 3 few-shot exchanges, found {exchange_count}"
        )

    _run("Few-shot", "FEW_SHOT_EXAMPLES contains >= 3 exchanges", test_fewshot_examples_content)

    # ---- Test 4: specialized toggle changes system prompt length ----
    def test_fewshot_makes_prompt_longer():
        ai_plain = PawPalAI(owner, kb_dir="knowledge_base", specialized=False)
        ai_spec  = PawPalAI(owner, kb_dir="knowledge_base", specialized=True)

        plain_prompts: list[str] = []
        spec_prompts:  list[str] = []

        def _capture_plain(**kwargs):
            plain_prompts.append(kwargs.get("system", ""))
            return _FakeResponse()

        def _capture_spec(**kwargs):
            spec_prompts.append(kwargs.get("system", ""))
            return _FakeResponse()

        ai_plain.client.messages.create = _capture_plain
        ai_spec.client.messages.create  = _capture_spec

        ai_plain.chat("hello")
        ai_spec.chat("hello")

        assert len(spec_prompts[0]) > len(plain_prompts[0]), (
            "Specialized system prompt should be longer than plain one"
        )

    _run("Few-shot", "Specialized prompt is longer than plain", test_fewshot_makes_prompt_longer)


# ===========================================================================
# Category 5: Live AI integration test (requires --live)
# ===========================================================================

def _live_ai_tests():
    from ai_assistant import PawPalAI
    from pawpal_system import Owner, Pet

    owner = Owner(name="LiveTestOwner", email="live@test.com")
    owner.add_pet(Pet(name="Rex", species="dog", age=4))
    ai = PawPalAI(owner, kb_dir="knowledge_base")

    # ---- Live Test 1: Schedule summary query ----
    def test_live_schedule_summary():
        reply, steps = ai.chat("What is my schedule summary?")
        assert isinstance(reply, str) and len(reply) > 0, "Reply should be a non-empty string"
        lower = reply.lower()
        assert any(kw in lower for kw in ["pet", "task", "schedule", "pending", "summary"]), (
            f"Expected schedule-related keywords in reply. Got: {reply[:200]}"
        )

    _run("Live AI", "Schedule summary query returns relevant content", test_live_schedule_summary)

    # ---- Live Test 2: Pet care knowledge query ----
    def test_live_dog_care_query():
        reply, steps = ai.chat("How often should I feed my dog?")
        assert isinstance(reply, str) and len(reply) > 0
        lower = reply.lower()
        assert any(kw in lower for kw in ["feed", "meal", "food", "day", "daily", "twice"]), (
            f"Expected feeding-related keywords. Got: {reply[:200]}"
        )

    _run("Live AI", "Dog feeding query returns relevant advice", test_live_dog_care_query)

    # ---- Live Test 3: Tool use — list pets ----
    def test_live_list_pets():
        reply, steps = ai.chat("List all my registered pets.")
        assert isinstance(reply, str) and len(reply) > 0
        assert "Rex" in reply or any(s["tool"] == "list_pets" for s in steps), (
            "Expected either 'Rex' in reply or list_pets tool call in steps"
        )

    _run("Live AI", "List pets triggers tool use or mentions pet name", test_live_list_pets)


# ===========================================================================
# Report rendering
# ===========================================================================

def _print_report():
    header = "PawPal+ Evaluation Harness"
    box_width = 62

    print()
    print("╔" + "═" * box_width + "╗")
    print("║" + header.center(box_width) + "║")
    print("╚" + "═" * box_width + "╝")
    print()

    cat_col   = 18
    test_col  = 42
    res_col   = 8
    score_col = 6

    header_row = (
        f"{'Category':<{cat_col}}"
        f"{'Test':<{test_col}}"
        f"{'Result':<{res_col}}"
        f"{'Score':>{score_col}}"
    )
    print(header_row)
    print("─" * (cat_col + test_col + res_col + score_col + 2))

    for r in _results:
        cat   = r["category"][:cat_col - 1]
        test  = r["test"][:test_col - 1]
        res   = r["result"]
        score = r["score"]
        print(
            f"{cat:<{cat_col}}"
            f"{test:<{test_col}}"
            f"{res:<{res_col}}"
            f"{score:>{score_col}.2f}"
        )

    total  = len(_results)
    passed = sum(1 for r in _results if r["result"] == "PASS")
    pct    = (passed / total * 100) if total else 0.0
    print()
    print(f"Summary: {passed}/{total} passed ({pct:.1f}%)")


# ===========================================================================
# Entry point
# ===========================================================================

def main():
    run_live = "--live" in sys.argv

    print("Running PawPal+ Evaluation Harness…")
    print()

    print("[ RAG Tests ]")
    _rag_tests()

    print("[ Scheduler Tests ]")
    _scheduler_tests()

    print("[ Custom KB Tests ]")
    _custom_kb_tests()

    print("[ Few-shot / Specialization Tests ]")
    _fewshot_tests()

    if run_live:
        print("[ Live AI Integration Tests ]")
        _live_ai_tests()
    else:
        print("[ Live AI Integration Tests ] — SKIPPED (pass --live to enable)")

    _print_report()


if __name__ == "__main__":
    main()
