"""
Legal Task.status transitions, enforced explicitly instead of leaving status
a free CharField any value can be written into from any other value. See
notes/skeleton_phaese1.md section 2.
"""

from .models import Task

ALLOWED_TRANSITIONS = {
    Task.Status.TODO: {Task.Status.IN_PROGRESS},
    Task.Status.IN_PROGRESS: {Task.Status.REVIEW, Task.Status.TODO},
    Task.Status.REVIEW: {Task.Status.DONE, Task.Status.IN_PROGRESS},
    Task.Status.DONE: set(),
}


def validate_transition(current: str, target: str) -> bool: 
    return target in ALLOWED_TRANSITIONS.get(current, set())

# what else to add here? maybe a function to get all allowed transitions from a given status, for use in the frontend?

def get_allowed_transitions(current: str) -> set[str]:
    return ALLOWED_TRANSITIONS.get(current, set()) # where would i add the GET endpoint to test this