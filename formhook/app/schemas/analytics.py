"""
Pydantic schema for analytics response.
"""
from pydantic import BaseModel
from typing import List, Literal

class FormAnalyticsEntry(BaseModel):
    date: str  # ISO date string
    submissions: int
    failed_webhooks: int
    emails_sent: int
    unique_ips: int

from pydantic import RootModel

class FormAnalyticsResponse(RootModel[List[FormAnalyticsEntry]]):
    pass
