"""Tests for concomplyai.core.container module.

Covers register/resolve, KeyError on unregistered names, singleton
behaviour, and registration overriding.
"""

import pytest

from concomplyai.core.container import Container


class TestContainer:
    """Tests for the dependency-injection Container."""

    @pytest.fixture
    def container(self):
        return Container()

    def test_register_and_resolve(self, container):
        """Registering a factory and resolving should return the factory product."""
        container.register("service", lambda: {"key": "value"})
        result = container.resolve("service")
        assert result == {"key": "value"}

    def test_resolve_unregistered_raises_key_error(self, container):
        """Resolving an unregistered name must raise KeyError."""
        with pytest.raises(KeyError, match="not registered"):
            container.resolve("missing_service")

    def test_singleton_behavior(self, container):
        """Repeated resolves must return the same cached instance."""
        container.register("singleton", lambda: object())
        first = container.resolve("singleton")
        second = container.resolve("singleton")
        assert first is second

    def test_override_registration(self, container):
        """Re-registering evicts the old singleton and uses the new factory."""
        container.register("svc", lambda: "original")
        assert container.resolve("svc") == "original"

        container.register("svc", lambda: "overridden")
        assert container.resolve("svc") == "overridden"

    def test_override_creates_new_instance(self, container):
        """After override the new resolve must return a fresh object."""
        container.register("svc", lambda: object())
        old = container.resolve("svc")

        container.register("svc", lambda: object())
        new = container.resolve("svc")

        assert old is not new

    def test_multiple_services(self, container):
        """Multiple independent services can coexist."""
        container.register("a", lambda: "alpha")
        container.register("b", lambda: "beta")

        assert container.resolve("a") == "alpha"
        assert container.resolve("b") == "beta"
