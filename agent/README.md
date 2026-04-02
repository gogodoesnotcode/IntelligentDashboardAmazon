# LangGraph Analysis Agent

This directory will contain the LangGraph pipeline for analyzing scraped Amazon data.

## Planned Nodes
- sentiment_node: Sentiment scoring of reviews
- theme_node: Theme extraction (praise/complaints)
- aspect_node: Aspect-based scoring (wheels, handle, etc.)
- insights_node: Brand-level insights

Each node will read/write to a shared AgentState dict. See whatToDo.md for details.

## Next Steps
- Implement agent pipeline after scraper phase is complete.
