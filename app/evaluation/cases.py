"""Strict, versioned golden cases. No service or network imports."""

import json
import re
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]*$")]
Category = Literal["retrieval", "supported_answer", "unsupported", "guardrail", "conversation"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Expectations(StrictModel):
    expected_section: Text | None = None
    expected_topic: Text | None = None
    required_terms: list[Text] = Field(default_factory=list)
    required_any_of: list[Annotated[list[Text], Field(min_length=1)]] = Field(default_factory=list)
    forbidden_terms: list[Text] = Field(default_factory=list)
    expected_grounded: bool
    expected_model: bool
    expected_sources: bool
    expected_answer: Text | None = None
    expected_contextualized: bool | None = None

    @model_validator(mode="after")
    def consistent(self):
        terms = self.required_terms + self.forbidden_terms + [
            term for group in self.required_any_of for term in group]
        if any(not re.search(r"\w", term) for term in terms):
            raise ValueError("Terms need at least one word character")
        forbidden = {term.casefold() for term in self.forbidden_terms}
        if any(term.casefold() in forbidden for term in self.required_terms):
            raise ValueError("A required term cannot also be forbidden")
        if any(all(term.casefold() in forbidden for term in group)
               for group in self.required_any_of):
            raise ValueError("An any-of group cannot be entirely forbidden")
        if self.expected_section and not self.expected_sources:
            raise ValueError("An expected source section requires sources")
        return self


class AnswerCase(Expectations):
    id: Identifier
    category: Literal["supported_answer", "unsupported", "guardrail"]
    query: Text

    @model_validator(mode="after")
    def category_expectations(self):
        if self.category == "supported_answer":
            if not (self.expected_grounded and self.expected_model and self.expected_sources
                    and self.expected_section and self.expected_topic):
                raise ValueError("Supported cases require grounding, model, sources and topic/section")
            if not (self.required_terms or self.required_any_of):
                raise ValueError("Supported cases need content assertions")
            if self.expected_answer is not None:
                raise ValueError("Supported answers must not exact-match generated prose")
        else:
            if self.expected_grounded or self.expected_model or self.expected_sources:
                raise ValueError("Deterministic bypass cases cannot expect grounding/model/sources")
            if not self.expected_answer:
                raise ValueError("Deterministic cases require the fixed expected answer")
        if self.category == "guardrail" and self.expected_contextualized:
            raise ValueError("Guardrails must bypass conversation context")
        return self


class RetrievalCase(StrictModel):
    id: Identifier
    category: Literal["retrieval"]
    query: Text
    expected_section: Text
    expected_topic: Text
    k: int = Field(ge=1)
    max_rank: int = Field(default=1, ge=1)
    ambiguity_reason: Text | None = None

    @model_validator(mode="after")
    def ranking(self):
        if self.max_rank > self.k:
            raise ValueError("Expected rank cannot exceed K")
        if self.max_rank != 1 and not self.ambiguity_reason:
            raise ValueError("Relaxed rank needs an explicit corpus ambiguity explanation")
        return self


class ConversationCase(StrictModel):
    id: Identifier
    category: Literal["conversation"]
    steps: list[AnswerCase] = Field(min_length=2)

    @model_validator(mode="after")
    def sequence(self):
        ids = [step.id for step in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate step IDs")
        if any(step.expected_contextualized is None for step in self.steps):
            raise ValueError("Every conversation step needs a context expectation")
        if self.steps[0].expected_contextualized:
            raise ValueError("A new conversation cannot start contextualized")
        return self


Case = Annotated[RetrievalCase | AnswerCase | ConversationCase, Field(discriminator="category")]
REQUIRED_CATEGORIES = {"retrieval", "supported_answer", "unsupported", "guardrail", "conversation"}


class CaseSuite(StrictModel):
    schema_version: Literal[1]
    name: Text
    cases: list[Case] = Field(min_length=1)

    @model_validator(mode="after")
    def complete(self):
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate case IDs")
        if {case.category for case in self.cases} != REQUIRED_CATEGORIES:
            raise ValueError("All five quality categories are mandatory")
        if any(isinstance(case, AnswerCase) and case.expected_contextualized is not None
               for case in self.cases):
            raise ValueError("Context assertions belong in conversation steps")
        return self


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def load_cases(path: Path) -> CaseSuite:
    return CaseSuite.model_validate(json.loads(path.read_text(encoding="utf-8"),
                                              object_pairs_hook=_unique_object))
