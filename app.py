import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, Frequency

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# --- Session state init ---
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", email="jordan@example.com")

owner: Owner = st.session_state.owner

# --- Owner info ---
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
    owner.add_pet(new_pet)          # Owner.add_pet() keeps the Pet in memory
    st.success(f"Added {new_pet.name} the {new_pet.species}!")

# Show registered pets
if owner.pets:
    st.write("**Registered pets:**")
    for pet in owner.pets:
        st.write(f"- {pet.name} ({pet.species}, age {pet.age})  `id: {pet.id[:8]}`")
else:
    st.info("No pets yet. Add one above.")

st.divider()

# --- Add a Task to a Pet ---
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
        task_submitted = st.form_submit_button("Add Task")

    if task_submitted:
        target_pet = pet_options[selected_pet_name]
        new_task = Task(
            description=task_desc,
            duration_minutes=int(duration),
            recurrence=Frequency(recurrence),
        )
        target_pet.add_task(new_task)   # Pet.add_task() attaches the Task
        st.success(f"Task '{task_desc}' added to {target_pet.name}.")

st.divider()

# --- Schedule View ---
st.subheader("Schedule")

if st.button("Generate schedule"):
    scheduler = Scheduler(owner)
    summary = scheduler.summary()
    upcoming = scheduler.get_upcoming_tasks()

    col1, col2, col3 = st.columns(3)
    col1.metric("Pets", summary["total_pets"])
    col2.metric("Pending tasks", summary["pending"])
    col3.metric("Completed", summary["completed"])

    if upcoming:
        st.write("**Upcoming tasks:**")
        for task in upcoming:
            due = task.due_time.strftime("%Y-%m-%d %H:%M") if task.due_time else "No due time"
            st.write(f"- **{task.description}** — {task.duration_minutes} min | due: {due} | `{task.recurrence.value}`")
    else:
        st.info("No pending tasks. Add some tasks to see them here.")
