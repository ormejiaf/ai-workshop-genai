from typing import Literal

from pydantic import BaseModel, Field


class SubmittedDocument(BaseModel):
    filename: str
    document_type: Literal[
        "identity_document", "academic_record", "payment_receipt", "other"
    ]
    status: Literal["valid", "invalid", "unreadable", "not_detected"]
    summary: str
    issuing_country_code: str | None = None
    visible_student_name: str | None = None
    visible_student_identifier: str | None = None
    issues: list[str] = Field(default_factory=list)


class EnrollmentReservationReview(BaseModel):
    submission_id: str
    documents: list[SubmittedDocument] = Field(default_factory=list)
    missing_required_documents: list[str] = Field(default_factory=list)
    inconsistencies: list[str] = Field(default_factory=list)
    decision: Literal["RESERVATION_APPROVED", "RESERVATION_REJECTED", "HUMAN_REVIEW"]
    decision_reason: str
    human_review_required: bool
