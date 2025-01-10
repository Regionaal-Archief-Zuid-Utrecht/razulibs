"""Decorators used across the RAZU package."""

from functools import wraps


def unless_locked(func):
    """Decorator that allows the method to execute only if the object is not locked.
    
    The decorated class must have an is_locked property.
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.is_locked:
            raise AssertionError(f"{self.__class__.__name__} is locked. Cannot execute {func.__name__}.")
        return func(self, *args, **kwargs)
    return wrapper
