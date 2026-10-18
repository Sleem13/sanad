"""Token auth + role/org-scope authorization. DEV-grade: replace with institutional IdP (OIDC/LDAP/AD) behind the same interface."""
from __future__ import annotations
from dataclasses import dataclass

PERMISSIONS = {
    "super_admin": {"ingest", "read_content", "edit", "approve", "reopen", "export", "assign", "read_audit", "admin_ops"},
    "operator":   {"ingest", "read_content"},
    "reviewer":   {"read_content", "edit", "approve"},
    "supervisor": {"read_content", "edit", "approve", "reopen", "export", "assign"},
    "viewer":     {"read_content"},
    "auditor":    {"read_audit"},
    "admin":      {"admin_ops", "read_audit"},       # deliberately NO content permissions
}


class Forbidden(Exception):
    pass


@dataclass(frozen=True)
class Principal:
    user: str
    roles: frozenset
    orgs: frozenset

    def has(self, perm: str) -> bool:
        return any(perm in PERMISSIONS.get(r, ()) for r in self.roles)

    def can_see_org(self, org: str) -> bool:
        return "*" in self.orgs or org in self.orgs

    def require(self, perm: str, org: str | None = None) -> None:
        if not self.has(perm):
            raise Forbidden(f"missing permission {perm}")
        if org is not None and not self.can_see_org(org):
            raise Forbidden("outside organizational scope")


def principal_from_token(users: dict, token: str | None) -> Principal | None:
    u = users.get(token or "")
    return Principal(u["user"], frozenset(u["roles"]), frozenset(u["orgs"])) if u else None
