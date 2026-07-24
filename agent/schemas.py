# agent/schemas.py
# Pydantic models for structured LLM output at each node.
# Each model maps to one node's expected JSON response.

from pydantic import BaseModel, Field
from typing import Literal


class SentimentOutput(BaseModel):
    score: float = Field(
        description="Overall sentiment score from 0.0 (extremely negative) to 10.0 (extremely positive)."
    )
    label: Literal["positive", "mixed", "negative"] = Field(
        description="Human-readable sentiment label. positive=score>=7, negative=score<=4, mixed=in between."
    )
    summary: str = Field(
        description="2-3 sentence summary of the overall customer sentiment for this brand."
    )


class ThemeOutput(BaseModel):
    praise_themes: list[str] = Field(
        description="Top 5 recurring things customers praise. Each theme is a short phrase (3-6 words)."
    )
    complaint_themes: list[str] = Field(
        description="Top 5 recurring things customers complain about. Each theme is a short phrase (3-6 words)."
    )


class AspectScore(BaseModel):
    score: float = Field(description="Score from 0.0 to 10.0 for this aspect.")
    summary: str = Field(description="One sentence explaining the score, ideally quoting or paraphrasing a real review.")


class ValueForMoneyOutput(BaseModel):
    score: float = Field(description="Value-for-money score from 0.0 to 10.0.")
    price_band: Literal["budget", "mid-range", "premium"] = Field(
        description="Which price band this brand falls into based on average product price."
    )
    verdict: str = Field(
        description="2-3 sentence verdict: does the quality justify the price? Cite specific review evidence."
    )


class AspectOutput(BaseModel):
    wheels: AspectScore
    handle: AspectScore
    zipper: AspectScore
    material: AspectScore
    size: AspectScore
    durability: AspectScore
    value_for_money: ValueForMoneyOutput


class SingleInsight(BaseModel):
    headline: str = Field(description="Short punchy headline for the insight (max 10 words).")
    explanation: str = Field(description="2-3 sentence explanation with specific evidence from the data.")


class InsightsOutput(BaseModel):
    insights: list[SingleInsight] = Field(
        description="Exactly 5 non-obvious competitive intelligence insights across all brands."
    )
