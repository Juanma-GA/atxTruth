from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"  # everything, including settings and users
    EDITOR = "editor"  # creates and edits data
    VIEWER = "viewer"  # reads and generates
