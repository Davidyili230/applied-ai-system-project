import streamlit as st
from datetime import datetime, date, time
import os
from pawpal_system import Owner, Pet, Task, Scheduler, Frequency, Priority

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

try:
    from ai_assistant import PawPalAI
    _AI_AVAILABLE = True
except ImportError:
    _AI_AVAILABLE = False

DATA_FILE = "data.json"

_PRIORITY_EMOJI = {
    Priority.HIGH: "🔴",
    Priority.MEDIUM: "🟡",
    Priority.LOW: "🟢",
}
_PRIORITY_LABEL = {
    Priority.HIGH: "🔴 High",
    Priority.MEDIUM: "🟡 Medium",
    Priority.LOW: "🟢 Low",
}

_TASK_EMOJIS = [
    ({"walk", "jog", "run", "hike", "stroll"}, "🦮"),
    ({"feed", "feeding", "meal", "food", "dinner", "breakfast", "lunch", "treat"}, "🍽️"),
    ({"medication", "medicine", "pill", "dose", "med", "inject"}, "💊"),
    ({"groom", "grooming", "bath", "brush", "trim", "nail", "clip"}, "✂️"),
    ({"vet", "checkup", "vaccine", "shot", "appointment"}, "🏥"),
    ({"play", "playtime", "fetch", "toy", "enrichment", "game"}, "🎾"),
    ({"train", "training", "sit", "stay", "command", "obedience"}, "🎓"),
    ({"water", "hydrate", "drink"}, "💧"),
    ({"clean", "litter", "scoop", "cage", "tank"}, "🧹"),
]


def _task_emoji(description: str) -> str:
    lower = description.lower()
    for keywords, emoji in _TASK_EMOJIS:
        if any(kw in lower for kw in keywords):
            return emoji
    return "🐾"


# --- Session state: owner ---
if "owner" not in st.session_state:
    if os.path.exists(DATA_FILE):
        try:
            st.session_state.owner = Owner.load_from_json(DATA_FILE)
        except Exception:
            st.session_state.owner = Owner(name="Jordan", email="jordan@example.com")
    else:
        st.session_state.owner = Owner(name="Jordan", email="jordan@example.com")

owner: Owner = st.session_state.owner


def _save():
    owner.save_to_json(DATA_FILE)


# --- Tabs ---
tab_labels = ["Manual Management", "AI Assistant"] if _AI_AVAILABLE else ["Manual Management"]
tabs = st.tabs(tab_labels)

# ===========================================================================
# TAB 1: Manual Management (all original functionality)
# ===========================================================================
with tabs[0]:
    st.subheader("Owner")
    st.write(f"**{owner.name}** — {len(owner.pets)} pet(s) registered")

    st.divider()

    # --- Add a Pet ---
    st.subheader("Add a Pet")

    with st.form("add_pet_form"):
        pet_name = st.text_input("Pet name", value="Mochi")
        species = st.selectbox("Species", ["dog", "cat", "other"])
        age = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
        submitted = st.form_submit_button("Add Pet")

    if submitted:
        new_pet = Pet(name=pet_name, species=species, age=age)
        owner.add_pet(new_pet)
        _save()
        st.success(f"Added {new_pet.name} the {new_pet.species}!")

    if owner.pets:
        st.write("**Registered pets:**")
        for pet in owner.pets:
            st.write(f"- {pet.name} ({pet.species}, age {pet.age})  `id: {pet.id[:8]}`")
    else:
        st.info("No pets yet. Add one above.")

    st.divider()

    # --- Add a Task ---
    st.subheader("Add a Task")

    if not owner.pets:
        st.warning("Add a pet first before creating tasks.")
    else:
        pet_options = {p.name: p for p in owner.pets}

        with st.form("add_task_form"):
            selected_pet_name = st.selectbox("Assign to pet", list(pet_options.keys()))
            task_desc = st.text_input("Task description", value="Morning walk")
            duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
            recurrence = st.selectbox("Recurrence", [f.value for f in Frequency])
            priority = st.selectbox(
                "Priority",
                [p.value for p in Priority],
                index=1,
                format_func=lambda v: _PRIORITY_LABEL[Priority(v)],
            )

            col_date, col_time = st.columns(2)
            with col_date:
                due_date = st.date_input("Due date (optional)", value=None)
            with col_time:
                due_time_val = st.time_input("Due time", value=time(8, 0))

            task_submitted = st.form_submit_button("Add Task")

        if task_submitted:
            target_pet = pet_options[selected_pet_name]

            due_datetime = None
            if due_date is not None:
                due_datetime = datetime.combine(due_date, due_time_val)

            new_task = Task(
                description=task_desc,
                duration_minutes=int(duration),
                due_time=due_datetime,
                recurrence=Frequency(recurrence),
                priority=Priority(priority),
            )

            scheduler = Scheduler(owner)
            conflict = scheduler.check_conflicts(new_task)

            target_pet.add_task(new_task)
            _save()
            st.success(f"Task **'{task_desc}'** added to {target_pet.name}.")

            if conflict:
                friendly = conflict.replace("WARNING: ", "")
                st.warning(
                    f"**Schedule conflict detected!** {friendly}\n\n"
                    "Consider adjusting the time or duration so your pet's care doesn't overlap."
                )

        st.write("**Find next available slot**")
        with st.form("slot_finder_form"):
            slot_duration = st.number_input(
                "Task duration to fit (minutes)", min_value=1, max_value=480, value=30
            )
            slot_submitted = st.form_submit_button("Find slot")

        if slot_submitted:
            scheduler = Scheduler(owner)
            next_slot = scheduler.find_next_available_slot(slot_duration)
            st.info(
                f"Next conflict-free slot for a **{slot_duration}-minute** task: "
                f"**{next_slot.strftime('%b %d, %Y at %I:%M %p')}**"
            )

    st.divider()

    # --- Schedule View ---
    st.subheader("Schedule")

    scheduler = Scheduler(owner)
    summary = scheduler.summary()

    col1, col2, col3 = st.columns(3)
    col1.metric("Pets", summary["total_pets"])
    col2.metric("Pending tasks", summary["pending"])
    col3.metric("Completed", summary["completed"])

    all_tasks = scheduler.get_all_tasks()

    if not all_tasks:
        st.info("No tasks yet. Add some tasks to see them here.")
    else:
        st.write("**Filter & sort**")
        fcol1, fcol2 = st.columns(2)

        with fcol1:
            pet_filter_options = ["All pets"] + [p.name for p in owner.pets]
            pet_filter = st.selectbox("Filter by pet", pet_filter_options, key="pet_filter")

        with fcol2:
            status_filter = st.selectbox(
                "Filter by status",
                ["All", "Pending", "Completed"],
                key="status_filter",
            )

        if pet_filter == "All pets":
            filtered_tasks = all_tasks
            pet_lookup = {
                task.id: pet.name
                for pet in owner.pets
                for task in pet.tasks
            }
        else:
            filtered_tasks = scheduler.filter_by_pet(pet_filter)
            pet_lookup = {task.id: pet_filter for task in filtered_tasks}

        if status_filter == "Pending":
            filtered_tasks = [t for t in filtered_tasks if not t.is_complete]
        elif status_filter == "Completed":
            filtered_tasks = [t for t in filtered_tasks if t.is_complete]

        sorted_tasks = scheduler.sort_by_time(filtered_tasks)

        if not sorted_tasks:
            st.info("No tasks match your current filter.")
        else:
            table_rows = []
            for task in sorted_tasks:
                due_str = task.due_time.strftime("%b %d, %Y  %I:%M %p") if task.due_time else "No due time"
                emoji = _task_emoji(task.description)
                status_icon = "✅ Done" if task.is_complete else "⏳ Pending"
                table_rows.append({
                    "Priority": _PRIORITY_LABEL[task.priority],
                    "Pet": pet_lookup.get(task.id, "—"),
                    "Task": f"{emoji} {task.description}",
                    "Duration": f"{task.duration_minutes} min",
                    "Due": due_str,
                    "Recurrence": task.recurrence.value,
                    "Status": status_icon,
                })

            st.table(table_rows)

            pending_tasks = [t for t in sorted_tasks if not t.is_complete]
            if pending_tasks:
                st.write("**Mark a task complete:**")
                for task in pending_tasks:
                    pet_name_lbl = pet_lookup.get(task.id, "")
                    emoji = _task_emoji(task.description)
                    priority_icon = _PRIORITY_EMOJI[task.priority]
                    label = f"{priority_icon} {emoji} Complete: {task.description}"
                    if pet_name_lbl:
                        label += f" ({pet_name_lbl})"
                    if task.due_time:
                        label += f" — {task.due_time.strftime('%b %d, %I:%M %p')}"

                    if st.button(label, key=f"complete_{task.id}"):
                        scheduler.mark_task_complete(task.id)
                        _save()
                        st.success(f"'{task.description}' marked complete!")
                        if task.recurrence in (Frequency.DAILY, Frequency.WEEKLY):
                            st.info(f"Next {task.recurrence.value} occurrence has been scheduled automatically.")
                        st.rerun()

# ===========================================================================
# TAB 2: AI Assistant (RAG + agentic tool use)
# ===========================================================================
if _AI_AVAILABLE:
    with tabs[1]:
        st.subheader("AI Assistant")
        st.caption(
            "Chat with PawPal AI to manage your pets and schedule using natural language. "
            "The AI uses pet care knowledge (RAG) and can add pets, create tasks, and find "
            "available slots autonomously."
        )

        # Init AI and chat history in session state
        if "pawpal_ai" not in st.session_state:
            st.session_state.pawpal_ai = PawPalAI(owner, save_callback=_save)
        if "chat_messages" not in st.session_state:
            st.session_state.chat_messages = []

        ai: PawPalAI = st.session_state.pawpal_ai
        # Keep the AI's owner reference in sync (e.g. after manual-tab changes)
        ai.owner = owner
        ai.scheduler.__init__(owner)

        # Display chat history
        for msg in st.session_state.chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat input
        if prompt := st.chat_input("Ask PawPal AI anything about your pets…"):
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking…"):
                    try:
                        reply = ai.chat(prompt)
                    except Exception as exc:
                        reply = f"Sorry, I encountered an error: {exc}"
                st.markdown(reply)

            st.session_state.chat_messages.append({"role": "assistant", "content": reply})
            # Persist any mutations the AI made
            _save()
            st.rerun()

        # Reset button
        if st.session_state.chat_messages:
            if st.button("Clear conversation", key="clear_chat"):
                st.session_state.chat_messages = []
                ai.reset_conversation()
                st.rerun()

        # Example prompts
        with st.expander("Example prompts"):
            st.markdown(
                "- *Add a dog named Buddy, age 3*\n"
                "- *Schedule a daily morning walk for Buddy at 7am, 30 minutes*\n"
                "- *What tasks are pending for Buddy?*\n"
                "- *Find me a free 45-minute slot today*\n"
                "- *How often should I groom a long-hair dog?*\n"
                "- *Add a high priority vet appointment for Mochi tomorrow at 10am, 90 minutes*\n"
                "- *What's my schedule summary?*"
            )
