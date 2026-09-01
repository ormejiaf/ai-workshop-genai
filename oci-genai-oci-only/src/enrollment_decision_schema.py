from typing import Literal

from pydantic import BaseModel, Field


class ReservationDecision(BaseModel):
    decision: Literal["RESERVATION_APPROVED", "RESERVATION_REJECTED", "HUMAN_REVIEW"]
    rationale: str
    blocking_issues: list[str] = Field(default_factory=list)
    policy_sources: list[str] = Field(default_factory=list)
    external_validation_considered: bool
