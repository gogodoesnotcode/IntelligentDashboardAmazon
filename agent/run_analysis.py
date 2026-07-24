# agent/run_analysis.py
# Entry point for Phase 2.
# Loops over every brand, runs one graph execution per brand,
# then writes a combined all_brands_summary.json at the end.
#
# Usage:
#   cd agent
#   python run_analysis.py
#
# Output:
#   data/analyzed/{brand}_analysis.json   — per-brand results
#   data/analyzed/all_brands_summary.json — combined file for FastAPI

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # loads GROQ_API_KEY from .env at project root

from graph import build_graph

# ── Config ─────────────────────────────────────────────────────────────────────

BRANDS = [
    "Safari",
    "American Tourister",
    "VIP",
    "Skybags",
    "Aristocrat",
    "Nasher Miles",
]

# scraper/raw/ is the single source of truth for raw data — agent/ no longer
# keeps its own copy. Resolved relative to this file so it works regardless
# of cwd.
DATA_DIR   = str(Path(__file__).resolve().parent.parent / "scraper" / "raw")
OUTPUT_DIR = str(Path(__file__).resolve().parent / "data" / "analyzed")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Runner ─────────────────────────────────────────────────────────────────────

def run():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    graph = build_graph()

    # all_brands_summary accumulates across brand runs so insights_node
    # can see every brand's results when it executes on the last brand.
    all_brands_summary: dict = {}

    log.info("=" * 55)
    log.info("Phase 2 — LangGraph Analysis Pipeline")
    log.info(f"Brands: {', '.join(BRANDS)}")
    log.info("=" * 55)

    for i, brand in enumerate(BRANDS):
        is_last = i == len(BRANDS) - 1
        log.info(f"\n{'─'*50}")
        log.info(f"Analysing: {brand}  ({'last — insights will run' if is_last else f'{i+1}/{len(BRANDS)}'})")
        log.info(f"{'─'*50}")

        initial_state = {
            "brand":              brand,
            "data_dir":           DATA_DIR,
            "output_dir":         OUTPUT_DIR,
            "is_last_brand":      is_last,
            "products":           [],
            "reviews":            [],
            "sentiment_score":    0.0,
            "sentiment_label":    "mixed",
            "sentiment_summary":  "",
            "praise_themes":      [],
            "complaint_themes":   [],
            "aspect_scores":      {},
            "value_for_money":    {},
            "all_brands_summary": all_brands_summary,  # pass accumulated data through
            "insights":           [],
            "errors":             [],
        }

        try:
            result = graph.invoke(initial_state)

            # Carry forward the updated summary for the next brand
            all_brands_summary = result.get("all_brands_summary", all_brands_summary)

            errors = result.get("errors", [])
            if errors:
                log.warning(f"  Non-fatal errors for {brand}:")
                for err in errors:
                    log.warning(f"    • {err}")

            log.info(
                f"  Done: sentiment={result.get('sentiment_score')} "
                f"({result.get('sentiment_label')}) | "
                f"{len(result.get('reviews', []))} reviews | "
                f"{len(result.get('praise_themes', []))} praise themes | "
                f"VFM={result.get('value_for_money', {}).get('score', 'N/A')}"
            )

        except Exception as e:
            log.error(f"  Graph execution failed for {brand}: {e}")
            all_brands_summary[brand] = {"brand": brand, "error": str(e)}

    # Write the combined summary file that FastAPI will load
    insights = []
    for brand_data in all_brands_summary.values():
        if brand_data.get("insights"):
            insights = brand_data["insights"]
            break

    combined = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "brands":        all_brands_summary,
        "insights":      insights,
    }

    summary_path = os.path.join(OUTPUT_DIR, "all_brands_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    log.info(f"\n{'='*55}")
    log.info("ANALYSIS COMPLETE")
    log.info(f"{'='*55}")
    log.info(f"  Per-brand files : {OUTPUT_DIR}/{{brand}}_analysis.json")
    log.info(f"  Combined file   : {summary_path}")
    log.info(f"  Brands processed: {len(all_brands_summary)}")
    log.info(f"  Insights generated: {len(insights)}")


if __name__ == "__main__":
    run()
