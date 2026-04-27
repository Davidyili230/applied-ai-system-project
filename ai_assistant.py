"""
PawPal+ AI Assistant
====================
Integrates two advanced AI features using Google Gemini:

1. RAG (Retrieval-Augmented Generation): KnowledgeBase retrieves relevant pet
   care guidelines before each response, grounding Gemini's advice in domain facts.

2. Agentic Workflow: Gemini uses function calling to autonomously read and mutate the
   PawPal schedule (list pets, add pets, add tasks, complete tasks, find slots)
   across multiple reasoning steps within a single user request.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import google.generativeai as genai

from pawpal_system import Frequency, Owner, Pet, Priority, Scheduler, Task

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("pawpal_ai")

# ---------------------------------------------------------------------------
# RAG: Knowledge Base
# ---------------------------------------------------------------------------

class KnowledgeBase:
    """Lightweight RAG retrieval layer backed by local markdown files.

    Each .md file in *kb_dir* is loaded as a named document. retrieve() scores
    documents by token overlap with the query and returns the best match as
    additional context for the LLM.
    """

    def __init__(self, kb_dir: str = "knowledge_base"):
        self.docs: dict[str, str] = {}
        self.last_confidence: float = 0.0  # normalized 0.0–1.0; updated by retrieve()
        self.last_retrieved_doc: str = ""   # name of the document selected by retrieve()
        kb_path = Path(kb_dir)
        if kb_path.exists():
            for f in sorted(kb_path.glob("*.md")):
                self.docs[f.stem] = f.read_text(encoding="utf-8")
        logger.info("KnowledgeBase: loaded %d document(s) from '%s'", len(self.docs), kb_dir)

    def add_document(self, name: str, content: str) -> None:
        """Add or replace a document in the knowledge base at runtime.

        Args:
            name: A short identifier for the document (used as the doc stem).
            content: The full text content of the document.
        """
        self.docs[name] = content
        logger.info("KnowledgeBase: added/updated document '%s' (%d chars)", name, len(content))

    def retrieve(self, query: str) -> str:
        """Return the most relevant knowledge base document for *query*.

        Scores each document by the count of query tokens that appear in the
        document text (token overlap). Normalizes the score to 0.0–1.0 by
        dividing by the number of unique query tokens and stores it as
        ``self.last_confidence`` for logging and testing.
        """
        if not self.docs:
            self.last_confidence = 0.0
            self.last_retrieved_doc = ""
            return ""

        query_tokens = set(query.lower().split())
        scores = {
            name: len(query_tokens & set(content.lower().split()))
            for name, content in self.docs.items()
        }
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            self.last_confidence = 0.0
            self.last_retrieved_doc = ""
            return ""

        self.last_confidence = scores[best] / len(query_tokens) if query_tokens else 0.0
        self.last_retrieved_doc = best
        logger.info(
            "RAG: '%s' selected (overlap=%d, confidence=%.2f) for query %r",
            best, scores[best], self.last_confidence, query,
        )
        return f"[Reference: {best.replace('_', ' ').title()}]\n{self.docs[best]}"

    def get_all_scores(self, query: str) -> dict[str, float]:
        """Return normalized retrieval scores for every document in the knowledge base.

        Args:
            query: The search query to score against all documents.

        Returns:
            A dict mapping document name → normalized score (0.0–1.0).
        """
        if not self.docs:
            return {}

        query_tokens = set(query.lower().split())
        if not query_tokens:
            return {name: 0.0 for name in self.docs}

        scores = {
            name: len(query_tokens & set(content.lower().split())) / len(query_tokens)
            for name, content in self.docs.items()
        }
        return scores


# ---------------------------------------------------------------------------
# Few-shot examples for specialized mode (Feature 3)
# ---------------------------------------------------------------------------

FEW_SHOT_EXAMPLES = """
User: How often should I feed my golden retriever?
Assistant: Great question for your 🐕! Here's a simple feeding guide for adult golden retrievers:

- **Morning meal** — around 7–8 AM, roughly 1–1.5 cups of high-quality kibble
- **Evening meal** — around 5–6 PM, same portion
- **Fresh water** — always available and refreshed at least twice daily

Goldens can be enthusiastic eaters, so measure portions carefully to avoid overfeeding. If your pup has any health conditions (like weight issues or allergies), your vet may suggest a customized plan.

*Follow-up: Does your golden have any dietary restrictions I should factor into their schedule?* 🐾

---

User: My cat hasn't used the litter box in a day — should I be worried?
Assistant: Oh no — that's definitely worth paying close attention to! 🐈 Here's what to consider:

**When to act right away:**
- If your cat is straining, crying in pain, or producing no urine at all → **call your vet immediately** (urinary blockage is an emergency)
- Vomiting or lethargy alongside litter box avoidance → vet visit today

**Possible causes (less urgent):**
1. Litter box isn't clean enough — cats are particular!
2. Stress from changes at home (new pet, moved furniture, guests)
3. New litter brand they dislike
4. A UTI or mild digestive upset

**Quick checklist:**
- Scoop and clean the box thoroughly
- Offer an extra box in a quiet spot
- Watch for any signs of discomfort when they try

I'm routing this as a **high-priority** item in your schedule so you don't lose track!

*Follow-up: How old is your cat, and have there been any recent changes at home?* 🐈

---

User: Can you add a weekly grooming session for my rabbit Biscuit?
Assistant: Absolutely — Biscuit deserves a spa day! 🐇 I've added a weekly grooming session to the schedule. Here's what that looks like:

**Task added:**
- 📋 Description: Weekly grooming — Biscuit
- ⏱ Duration: 20 minutes
- 🔁 Recurrence: Weekly
- ⭐ Priority: Medium

**Quick grooming tips for rabbits:**
- Use a soft slicker brush; long-haired breeds may need daily attention
- Check ears, nails, and teeth during each session
- Never bathe a rabbit in water — spot-clean only if needed

I'll remind you each week so Biscuit's coat stays healthy and mat-free!

*Follow-up: Would you like me to find the best time slot so grooming doesn't clash with Biscuit's feeding schedule?* 🐾
"""


_TOOLS_SCHEMA: list[dict] = [
    {
        "name": "list_pets",
        "description": "Return all pets registered under the current owner.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "add_pet",
        "description": "Register a new pet for the owner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Pet's name"},
                "species": {"type": "string", "description": "Species, e.g. dog, cat, rabbit"},
                "age": {"type": "integer", "description": "Age in years (0 for unknown)"},
            },
            "required": ["name", "species", "age"],
        },
    },
    {
        "name": "list_tasks",
        "description": "List scheduled care tasks, with optional filters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {
                    "type": "string",
                    "description": "Filter to this pet's tasks. Empty string means all pets.",
                },
                "status": {
                    "type": "string",
                    "enum": ["all", "pending", "completed"],
                    "description": "Filter by completion status (default: all).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "add_task",
        "description": (
            "Add a care task to a specific pet. Automatically warns about schedule conflicts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pet_name": {"type": "string", "description": "Name of the pet to assign the task"},
                "description": {"type": "string", "description": "Short description of the task"},
                "duration_minutes": {"type": "integer", "description": "How long the task takes"},
                "priority": {
                    "type": "string",
                    "enum": ["high", "medium", "low"],
                    "description": "Task priority (default: medium)",
                },
                "recurrence": {
                    "type": "string",
                    "enum": ["once", "daily", "weekly"],
                    "description": "How often the task repeats (default: once)",
                },
                "due_time": {
                    "type": "string",
                    "description": (
                        "ISO 8601 datetime for when the task is due, e.g. 2024-01-15T09:00:00. "
                        "Omit or leave empty for no scheduled time."
                    ),
                },
            },
            "required": ["pet_name", "description", "duration_minutes"],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as complete by its unique task ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The full UUID of the task"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "find_available_slot",
        "description": "Find the earliest conflict-free time slot for a task of the given duration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "duration_minutes": {
                    "type": "integer",
                    "description": "Task duration in minutes",
                },
                "start_from": {
                    "type": "string",
                    "description": "ISO 8601 datetime to start searching from (defaults to now)",
                },
            },
            "required": ["duration_minutes"],
        },
    },
    {
        "name": "get_schedule_summary",
        "description": "Return a high-level summary: pet count, pending tasks, completed tasks.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


# ---------------------------------------------------------------------------
# PawPalAI: agentic assistant
# ---------------------------------------------------------------------------

class PawPalAI:
    """AI-powered assistant for PawPal+ with RAG context and agentic tool use.

    Attributes:
        MAX_TOOL_ROUNDS: Safety guardrail limiting how many tool-call / response
            cycles are allowed per user message to prevent runaway loops.
    """

    MAX_TOOL_ROUNDS = 8
    MODEL = "gemini-2.0-flash"

    def __init__(
        self,
        owner: Owner,
        kb_dir: str = "knowledge_base",
        save_callback=None,
        specialized: bool = False,
    ):
        self.owner = owner
        self.scheduler = Scheduler(owner)
        self.kb = KnowledgeBase(kb_dir)
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Build base system prompt
        system_prompt = (
            "You are PawPal AI, a friendly and knowledgeable pet care scheduling assistant. "
            "Help the owner manage their pets' daily care tasks using the tools available. "
            "Be concise and practical."
        )
        
        # Create tools from schema
        tools = self._convert_tools_to_gemini_format(_TOOLS_SCHEMA)
        
        self.client = genai.GenerativeModel(
            self.MODEL,
            tools=tools,
            system_instruction=system_prompt
        )
        self.save_callback = save_callback
        self.specialized = specialized
        self.conversation_history: list[dict] = []
        logger.info("PawPalAI ready for owner '%s'", owner.name)
    
    @staticmethod
    def _convert_tools_to_gemini_format(tools_schema):
        """Convert tool definitions to Gemini's Tool format."""
        try:
            from google.generativeai.protos import Tool, FunctionDeclaration
            
            tools = []
            for tool_def in tools_schema:
                # Convert input_schema to parameters
                params = tool_def.get("input_schema", {})
                
                # Create function declaration - FunctionDeclaration expects 'parameters' not 'input_schema'
                func_decl = FunctionDeclaration(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    parameters=params
                )
                tool = Tool(function_declarations=[func_decl])
                tools.append(tool)
            return tools
        except Exception as e:
            logger.warning("Could not convert tools to proto format: %s. Using fallback.", e)
            # Return None to use genai's default handling
            return None

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    def _run_tool(self, name: str, inputs: dict) -> str:
        logger.info("Tool → %s(%s)", name, json.dumps(inputs, default=str))
        try:
            result = self._dispatch(name, inputs)
        except Exception as exc:
            logger.error("Tool '%s' raised: %s", name, exc, exc_info=True)
            result = f"Error executing {name}: {exc}"
        logger.info("Tool ← %s", str(result)[:300])
        return result

    def _dispatch(self, name: str, inp: dict) -> str:  # noqa: C901
        if name == "list_pets":
            return self._list_pets()
        if name == "add_pet":
            return self._add_pet(inp["name"], inp["species"], int(inp["age"]))
        if name == "list_tasks":
            return self._list_tasks(inp.get("pet_name", ""), inp.get("status", "all"))
        if name == "add_task":
            return self._add_task(
                inp["pet_name"],
                inp["description"],
                int(inp["duration_minutes"]),
                inp.get("priority", "medium"),
                inp.get("recurrence", "once"),
                inp.get("due_time", ""),
            )
        if name == "complete_task":
            return self._complete_task(inp["task_id"])
        if name == "find_available_slot":
            return self._find_slot(int(inp["duration_minutes"]), inp.get("start_from", ""))
        if name == "get_schedule_summary":
            return json.dumps(self.scheduler.summary(), indent=2)
        return f"Unknown tool: {name}"

    # ------ individual tool implementations ------

    def _list_pets(self) -> str:
        if not self.owner.pets:
            return "No pets registered yet."
        return "\n".join(
            f"- {p.name} ({p.species}, age {p.age}) [id: {p.id}]"
            for p in self.owner.pets
        )

    def _add_pet(self, name: str, species: str, age: int) -> str:
        pet = Pet(name=name, species=species, age=age)
        self.owner.add_pet(pet)
        if self.save_callback:
            self.save_callback()
        return f"Registered pet '{name}' ({species}, age {age}). ID: {pet.id}"

    def _list_tasks(self, pet_name: str = "", status: str = "all") -> str:
        if pet_name:
            tasks = self.scheduler.filter_by_pet(pet_name)
            pet_map = {t.id: pet_name for t in tasks}
        else:
            tasks = self.scheduler.get_all_tasks()
            pet_map = {t.id: p.name for p in self.owner.pets for t in p.tasks}

        if status == "pending":
            tasks = [t for t in tasks if not t.is_complete]
        elif status == "completed":
            tasks = [t for t in tasks if t.is_complete]

        if not tasks:
            return "No tasks found."

        lines = []
        for t in self.scheduler.sort_by_time(tasks):
            due_str = t.due_time.strftime("%b %d %I:%M %p") if t.due_time else "no due time"
            icon = "✅" if t.is_complete else "⏳"
            lines.append(
                f"{icon} [{t.priority.value}] {t.description} "
                f"({t.duration_minutes} min, {due_str}) "
                f"[id: {t.id}] — {pet_map.get(t.id, '?')}"
            )
        return "\n".join(lines)

    def _add_task(
        self,
        pet_name: str,
        description: str,
        duration_minutes: int,
        priority: str = "medium",
        recurrence: str = "once",
        due_time: str = "",
    ) -> str:
        pet = next(
            (p for p in self.owner.pets if p.name.lower() == pet_name.lower()), None
        )
        if pet is None:
            known = [p.name for p in self.owner.pets]
            return f"Pet '{pet_name}' not found. Registered pets: {known}"

        due_dt = None
        if due_time:
            try:
                due_dt = datetime.fromisoformat(due_time)
            except ValueError:
                return (
                    f"Invalid due_time '{due_time}'. "
                    "Use ISO 8601 format, e.g. 2024-01-15T09:00:00."
                )

        task = Task(
            description=description,
            duration_minutes=duration_minutes,
            due_time=due_dt,
            recurrence=Frequency(recurrence),
            priority=Priority(priority),
        )

        conflict = self.scheduler.check_conflicts(task)
        pet.add_task(task)
        if self.save_callback:
            self.save_callback()

        msg = f"Added task '{description}' to {pet.name} (id: {task.id})."
        if conflict:
            msg += f"\n⚠️ Conflict detected: {conflict}"
        return msg

    def _complete_task(self, task_id: str) -> str:
        success = self.scheduler.mark_task_complete(task_id)
        if self.save_callback:
            self.save_callback()
        return (
            f"Task {task_id} marked complete."
            if success
            else f"Task '{task_id}' not found."
        )

    def _find_slot(self, duration_minutes: int, start_from: str = "") -> str:
        start = datetime.fromisoformat(start_from) if start_from else datetime.now()
        slot = self.scheduler.find_next_available_slot(duration_minutes, start)
        return f"Next available slot: {slot.strftime('%b %d, %Y at %I:%M %p')}"

    # ------------------------------------------------------------------
    # Main chat entry point
    # ------------------------------------------------------------------

    def chat(self, user_message: str) -> tuple[str, list[dict]]:
        """Process *user_message* with RAG context injection and agentic tool use.

        Flow:
          1. RAG: retrieve relevant pet care knowledge for the query.
          2. Append RAG context to the user message if available.
          3. Send conversation to Gemini with tool definitions.
          4. Execute any function calls and feed results back (up to MAX_TOOL_ROUNDS).
          5. Return (Gemini's final text response, list of agentic steps).

        Each step in the returned list has the shape:
            {"round": int, "tool": str, "input": dict, "output": str}
        """
        logger.info("User: %r", user_message)

        steps: list[dict] = []

        # Step 1 — RAG retrieval
        rag_context = self.kb.retrieve(user_message)
        if rag_context:
            logger.info("RAG injected %d chars of context", len(rag_context))

        # Step 2 — enhance user message with RAG context
        enhanced_message = user_message
        if rag_context:
            enhanced_message = f"{user_message}\n\n[Context Reference: {rag_context}]"

        # Step 3 — create chat session
        chat_session = self.client.start_chat(history=self.conversation_history)

        # Step 4 — agentic loop
        for round_num in range(1, self.MAX_TOOL_ROUNDS + 1):
            logger.info("Agentic round %d/%d", round_num, self.MAX_TOOL_ROUNDS)
            response = chat_session.send_message(
                enhanced_message if round_num == 1 else user_message,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1024,
                ),
            )
            logger.info("Gemini finish_reason=%s", response.candidates[0].finish_reason)

            if response.candidates[0].finish_reason == "STOP":
                text = response.text
                self.conversation_history = chat_session.history
                return text, steps

            if response.candidates[0].finish_reason == "TOOL_CALLS":
                tool_results = []
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        result = self._run_tool(part.function_call.name, dict(part.function_call.args))
                        steps.append({
                            "round": round_num,
                            "tool": part.function_call.name,
                            "input": dict(part.function_call.args),
                            "output": result,
                        })
                        try:
                            tool_result_part = genai.types.Part.from_function_response(
                                name=part.function_call.name,
                                response={"result": result}
                            )
                            tool_results.append(tool_result_part)
                        except Exception as e:
                            logger.warning("Could not create function response part: %s", e)
                            # Fallback: send result as text
                            tool_results.append(f"Tool {part.function_call.name} result: {result}")
                
                # Send tool results back to the chat
                if tool_results:
                    chat_session.send_message(tool_results)
            else:
                logger.warning("Unexpected finish_reason: %s", response.candidates[0].finish_reason)
                break

        logger.warning("MAX_TOOL_ROUNDS (%d) reached", self.MAX_TOOL_ROUNDS)
        self.conversation_history = chat_session.history
        return (
            "I reached my complexity limit on that request. Please try breaking it into smaller steps.",
            steps,
        )

    def reset_conversation(self) -> None:
        """Clear conversation history for a fresh session."""
        self.conversation_history.clear()
        logger.info("Conversation history cleared")
