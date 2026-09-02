"""
Technical Support Knowledge Base and Diagnostic Flow Schemas
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class TroubleshootingStep(BaseModel):
    step_number: int
    instruction: str
    rationale: Optional[str] = None
    expected_result: str
    follow_up_question: str
    positive_indicators: List[str] = Field(default_factory=list)
    negative_indicators: List[str] = Field(default_factory=list)
    on_success_action: Optional[str] = "proceed"  # "proceed", "resolved", "escalate"
    on_failure_action: Optional[str] = "next_step"  # "next_step", "escalate"
    is_terminal_resolution: bool = False


class FAQItem(BaseModel):
    question: str
    answer: str
    keywords: List[str] = Field(default_factory=list)


class KnowledgeArticle(BaseModel):
    id: str
    title: str
    category: str
    keywords: List[str] = Field(default_factory=list)
    summary: str
    common_symptoms: List[str] = Field(default_factory=list)
    diagnostic_flow: List[TroubleshootingStep] = Field(default_factory=list)
    faqs: List[FAQItem] = Field(default_factory=list)
    escalation_triggers: List[str] = Field(default_factory=list)
    fallback_resolution: str


class KnowledgeBase(BaseModel):
    articles: List[KnowledgeArticle] = Field(default_factory=list)
    general_faqs: List[FAQItem] = Field(default_factory=list)
