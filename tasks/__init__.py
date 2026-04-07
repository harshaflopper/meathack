"""
Tasks package — exposes Task class and get_tasks() for the environment.
"""
from typing import List
from tasks.base import Task
from tasks.easy import get_easy_task
from tasks.medium import get_medium_task
from tasks.hard import get_hard_task


def get_tasks() -> List[Task]:
    """Return all tasks in order: easy, medium, hard."""
    return [
        get_easy_task(),
        get_medium_task(),
        get_hard_task(),
    ]


__all__ = ["Task", "get_tasks"]
