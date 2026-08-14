"""Translate Cognito claims into retrieval and source-access decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    subject: str
    groups: frozenset[str]

    @property
    def is_admin(self) -> bool:
        return "admin" in self.groups

    def retrieval_filter(self) -> dict[str, Any] | None:
        if self.is_admin:
            return None
        public = {"equals": {"key": "confidentiality", "value": "public"}}
        departments = sorted(self.groups - {"admin"})
        if not departments:
            return public
        department_filters = [
            {"listContains": {"key": "departments", "value": department}}
            for department in departments
        ]
        department_filter = (
            department_filters[0] if len(department_filters) == 1 else {"orAll": department_filters}
        )
        internal = {
            "andAll": [
                {"equals": {"key": "confidentiality", "value": "internal"}},
                department_filter,
            ]
        }
        return {"orAll": [public, internal]}

    def can_read(self, *, confidentiality: str, departments: list[str]) -> bool:
        if confidentiality == "public" or self.is_admin:
            return True
        if confidentiality != "internal":
            return False
        return bool(self.groups.intersection(departments))


def authorization_from_event(event: dict[str, Any]) -> AuthorizationContext:
    authorizer = event.get("requestContext", {}).get("authorizer", {}).get("jwt", {})
    claims = authorizer.get("claims", {}) if isinstance(authorizer, dict) else {}
    subject = claims.get("sub") if isinstance(claims, dict) else None
    if not isinstance(subject, str) or not subject:
        raise PermissionError("missing authenticated Cognito subject")
    raw_groups = claims.get("cognito:groups", "")
    if isinstance(raw_groups, list):
        groups = {str(group).strip().lower() for group in raw_groups if str(group).strip()}
    else:
        groups = {
            group.strip().lower()
            for group in str(raw_groups).strip("[]").split(",")
            if group.strip()
        }
    return AuthorizationContext(subject=subject, groups=frozenset(groups))
