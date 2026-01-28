from typing import Any, List, Optional

from pydantic import BaseModel, Field


class PortfolioSuggestion(BaseModel):
    id: str
    field: str
    currentValue: str
    suggestedValue: str
    reasoning: str
    confidence: float = Field(ge=0, le=1)


class PortfolioSuggestionList(BaseModel):
    suggestions: List[PortfolioSuggestion] = Field(default_factory=list)


class ApplySuggestionItem(BaseModel):
    field: str
    value: Any
    expectedCurrent: Optional[Any] = None


class ApplySuggestionsRequest(BaseModel):
    updates: List[ApplySuggestionItem]


class AnalyzePortfolioResponse(BaseModel):
    fileUrl: str
    suggestions: List[PortfolioSuggestion] = Field(default_factory=list)
