import uuid
from dataclasses import dataclass

from app.auth.roles import Role


@dataclass(frozen=True)
class CurrentUser:
    """The only thing authorization depends on, whatever the identity source (local or OIDC)."""

    id: uuid.UUID
    email: str
    display_name: str
    roles: frozenset[Role]
    must_change_password: bool = False

    def has_any(self, *roles: Role) -> bool:
        return bool(self.roles.intersection(roles))
