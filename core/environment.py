"""
core/environment.py — AxonBlade scope chain (Week 5, Phase 5.1).

Implements the Environment class per ProjectPlan.md §6.1.

Key design points:
  - define(name, value) always writes to *this* scope (for declarations).
  - get(name) walks up the parent chain.
  - set(name, value) finds the owning scope and mutates it — this is what
    makes closure variable mutation work correctly.
"""

from __future__ import annotations

from core.errors import AxonNameError


class Environment:
    """Scope chain for AxonBlade variable lookup."""

    def __init__(self, parent: "Environment | None" = None) -> None:
        self.store: dict = {}
        self.parent: "Environment | None" = parent

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def define(self, name: str, value: object) -> None:
        """Declare a new variable in *this* scope."""
        self.store[name] = value

    def get(self, name: str) -> object:
        """Look up *name* starting from this scope, walking up the chain."""
        if name in self.store:
            return self.store[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise AxonNameError(f"Undefined variable '{name}'")

    def set(self, name: str, value: object) -> None:
        """
        Re-assign *name* to *value* in the nearest scope that owns it.
        Raises AxonNameError if the variable was never declared.
        """
        if name in self.store:
            self.store[name] = value
            return
        if self.parent is not None:
            self.parent.set(name, value)
            return
        raise AxonNameError(f"Undefined variable '{name}'")

    def has_local(self, name: str) -> bool:
        """Return True if *name* is defined in *this* scope (not parents)."""
        return name in self.store

    def child(self) -> "Environment":
        """Create and return a new child scope with self as parent."""
        return Environment(parent=self)
