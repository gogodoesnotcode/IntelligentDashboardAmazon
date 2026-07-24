# agent/graph.py
# Defines the AgentState and wires nodes into a LangGraph StateGraph.
# One graph run = one brand. The runner (run_analysis.py) loops over brands.

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, START, END

from nodes import (
    loader_node,
    sentiment_node,
    theme_node,
    aspect_node,
    insights_node,
    writer_node,
)


# ── State ──────────────────────────────────────────────────────────────────────

class AnalysisState(TypedDict):
    # Input
    brand:       str
    data_dir:    str          # path to raw CSVs
    output_dir:  str          # path to write analyzed JSONs
    is_last_brand: bool       # signals insights_node to run

    # Loaded data
    products: list[dict]
    reviews:  list[dict]

    # Sentiment node output
    sentiment_score:   float
    sentiment_label:   str
    sentiment_summary: str

    # Theme node output
    praise_themes:    list[str]
    complaint_themes: list[str]

    # Aspect node output
    aspect_scores:   dict     # {wheels, handle, zipper, material, size, durability}
    value_for_money: dict     # {score, price_band, verdict, avg_price}

    # Cross-brand accumulator (passed through every brand run)
    all_brands_summary: dict  # {brand_name: brand_result_dict}

    # Insights node output (only populated on last brand)
    insights: list[dict]      # [{headline, explanation}, ...]

    # Non-fatal error log
    errors: list[str]


# ── Skip condition ─────────────────────────────────────────────────────────────

def _has_reviews(state: AnalysisState) -> str:
    """Route past analysis nodes if loader found no usable reviews."""
    return "sentiment" if state.get("reviews") else "writer"


# ── Graph factory ──────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AnalysisState)

    graph.add_node("loader",   loader_node)
    graph.add_node("sentiment", sentiment_node)
    graph.add_node("themes",   theme_node)
    graph.add_node("aspects",  aspect_node)
    graph.add_node("insights", insights_node)
    graph.add_node("writer",   writer_node)

    # Entry
    graph.add_edge(START, "loader")

    # Skip analysis if no reviews were loaded
    graph.add_conditional_edges("loader", _has_reviews, {
        "sentiment": "sentiment",
        "writer":    "writer",
    })

    # Linear analysis pipeline
    graph.add_edge("sentiment", "themes")
    graph.add_edge("themes",    "aspects")
    graph.add_edge("aspects",   "insights")
    graph.add_edge("insights",  "writer")

    graph.add_edge("writer", END)

    return graph.compile()
