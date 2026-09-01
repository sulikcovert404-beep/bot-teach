from typing import Literal

from pydantic import BaseModel

Role = Literal[
    "STUDENT",
    "TEACHER",
    "PARENT",
    "SCHOOL_ADMIN",
    "CONTENT_ADMIN",
    "SUPER_ADMIN",
]


class PlatformInfo(BaseModel):
    name: str
    api_version: str

