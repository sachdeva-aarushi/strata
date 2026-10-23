"""
Waste-prevention recommendation schemas for STRATA.

These schemas are deliberately separate from qualification schemas:
  - Qualification = can this lot be processed by route X? (deterministic)
  - Prevention = what actions should the operator take to reduce waste? (advisory)

All recommendations must:
  - State their evidence basis explicitly
  - Identify missing information that limits confidence
  - Never claim environmental savings figures that are not derived from verified data
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class RecommendationConfidence(str, Enum):
    """
    Confidence level of a waste-prevention recommendation.
    Determined by the quality and completeness of supporting evidence.
    """
    HIGH = "high"        # All supporting evidence is verified; no missing critical facts
    MEDIUM = "medium"    # Some evidence present but one or more facts are missing or unverified
    LOW = "low"          # Minimal evidence; recommendation is advisory only


class RecommendationCategory(str, Enum):
    """Category of waste-prevention action."""
    ROUTE_OPTIMIZATION = "route_optimization"      # Improve processing pathway selection
    EVIDENCE_ACQUISITION = "evidence_acquisition"  # Obtain missing qualification facts
    LOT_PREPARATION = "lot_preparation"            # Pre-treatment, sorting, or packaging steps
    EXCHANGE_LISTING = "exchange_listing"           # List lot on STRATA Circular Exchange
    DEFERRED = "deferred"                           # No actionable recommendation at this time


class MissingInformationItem(BaseModel):
    """Describes a specific piece of missing information limiting recommendation quality."""
    item_id: str
    description: str
    acquisition_method: str = Field(
        default="document",
        description="lab_test, document, user_confirmation, external_source",
    )


class PreventionRecommendation(BaseModel):
    """
    A single waste-prevention recommendation for a material lot.

    All recommendations are advisory. Confidence reflects evidence completeness.
    Environmental impact statements are intentionally omitted: STRATA does not
    generate unsupported environmental savings claims.
    """
    recommendation_id: str
    lot_id: str
    category: RecommendationCategory
    summary: str = Field(..., description="One-sentence headline recommendation")
    rationale: str = Field(
        ...,
        description="Evidence-grounded explanation of why this recommendation applies",
    )
    confidence: RecommendationConfidence
    evidence_basis: List[str] = Field(
        default_factory=list,
        description="Evidence record IDs or route IDs supporting this recommendation",
    )
    missing_information: List[MissingInformationItem] = Field(
        default_factory=list,
        description="Information gaps that limit recommendation confidence",
    )
    next_steps: List[str] = Field(
        default_factory=list,
        description="Ordered list of concrete actionable steps",
    )
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class PreventionRecommendationsResponse(BaseModel):
    """Response envelope for prevention recommendations on a material lot."""
    lot_id: str
    material_type: str
    recommendations: List[PreventionRecommendation] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_provider: str = Field(
        default="fake",
        description="Which discovery provider was used: 'tinyfish' or 'fake'",
    )
    llm_provider: str = Field(
        default="fake",
        description="Which LLM provider was used: 'openai' or 'fake'",
    )

    model_config = ConfigDict(from_attributes=True)
