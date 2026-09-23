from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, field_validator
import re

class ExperimentStatus(str, Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

class UserRegisterSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=6)

    @field_validator('username')
    def username_alphanumeric(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError('Username must contain only letters, numbers, and underscores.')
        return v

class ExperimentSchema(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    student_id: str = Field(..., min_length=4, max_length=15)
    status: ExperimentStatus = Field(default=ExperimentStatus.PENDING)