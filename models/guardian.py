from pydantic import BaseModel, Field
from typing import Optional, Literal


class Guardian(BaseModel):
    status: Literal["ALLOWED", "REJECTED", "ERROR"] = Field(
        description="ALLOWED if the message is safe and related to booking. REJECTED otherwise."
    )
    destination: Literal["concierge", "book", "rescheduler", "onboarding"] = Field(
        description="The target spoke node based on user intent."
    )
    extracted_consultant: Optional[str] = Field(
        None,
        description="The name of the consultant mentioned by the user (e.g., 'Alan Turing').",
    )
    extracted_date: Optional[str] = Field(
        None,
        description="Any date or relative time expression mentioned (e.g., 'next Friday').",
    )
    extracted_time: Optional[str] = Field(
        None, description="Any specific time slot mentioned (e.g., '9:00 AM', '14:00')."
    )
