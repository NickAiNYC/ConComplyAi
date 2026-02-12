"""Lightweight dependency-injection container with thread-safe singleton support.

Usage::

    container = Container()
    container.register("event_bus", lambda: EventBus())
    bus = container.resolve("event_bus")   # created once, cached thereafter
"""

from __future__ import annotations

import threading
from typing import Any, Callable


class Container:
    """Thread-safe service locator / DI container.

    Factories are registered by name and resolved lazily.  Once a factory
    has been invoked its return value is cached so that every subsequent
    ``resolve`` call returns the same singleton instance.
    """

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], Any]] = {}
        self._singletons: dict[str, Any] = {}
        self._lock = threading.Lock()

    def register(self, name: str, factory: Callable[[], Any]) -> None:
        """Bind *name* to *factory*.

        If a singleton for *name* was previously resolved it is evicted so
        the next ``resolve`` call will invoke the new factory.

        Args:
            name: Unique service identifier.
            factory: Zero-argument callable that produces the service instance.
        """
        with self._lock:
            self._factories[name] = factory
            self._singletons.pop(name, None)

    def resolve(self, name: str) -> Any:
        """Return the singleton instance for *name*, creating it if necessary.

        Args:
            name: Service identifier previously passed to ``register``.

        Returns:
            The cached service instance.

        Raises:
            KeyError: If *name* has not been registered.
        """
        with self._lock:
            if name in self._singletons:
                return self._singletons[name]

            if name not in self._factories:
                raise KeyError(
                    f"Service '{name}' is not registered. "
                    f"Available: {', '.join(sorted(self._factories)) or '(none)'}"
                )

            instance = self._factories[name]()
            self._singletons[name] = instance
            return instance
