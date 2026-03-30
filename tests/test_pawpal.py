from pawpal_system import Task, Pet


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
