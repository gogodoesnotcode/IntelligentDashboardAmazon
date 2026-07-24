# agent/prompts.py
# All LLM prompts for the analysis pipeline.
# Each prompt uses few-shot examples and explicit output instructions
# to maximise structured output quality from llama-3.1-70b-versatile.


SENTIMENT_PROMPT = """You are a senior market research analyst specialising in e-commerce customer sentiment.

Your task: Read the customer reviews below for {brand} luggage products and return a single overall sentiment score.

SCORING SCALE:
  0.0 – 2.0  : Extremely negative. Customers are angry, products failing, many 1-star reviews.
  2.1 – 4.0  : Negative. More complaints than praise, clear quality issues.
  4.1 – 6.0  : Mixed. Roughly equal praise and complaints, inconsistent quality signals.
  6.1 – 8.0  : Positive. Customers are generally satisfied, minor complaints only.
  8.1 – 10.0 : Very positive. Strong praise, loyal customers, very few complaints.

RULES:
- Weight 1-star and 2-star reviews more heavily than 5-star reviews (complaints are more diagnostic).
- A product with 4.5 stars but 30% complaints about zipper breaking should score no higher than 6.5.
- Ignore reviews that are clearly fake (suspiciously generic praise, no specifics).
- Your score must reflect the BRAND overall, not just one product.

FEW-SHOT EXAMPLES:

Example 1 — Positive brand:
Reviews include: "Wheels are smooth after 2 years of use", "TSA lock works perfectly",
"Bought 3rd Safari bag, never disappointed", "Quality feels premium for the price".
→ score: 8.2, label: "positive", summary: "Safari customers show strong loyalty with repeated purchases.
   Build quality and wheels are consistently praised. Minor complaints about zipper stiffness on new bags."

Example 2 — Mixed brand:
Reviews include: "Good bag but zipper broke in 6 months", "Looks great but wheels wobble after 3 trips",
"Value for money is excellent", "Customer service never responded to my complaint".
→ score: 5.1, label: "mixed", summary: "Customers appreciate the price point but report inconsistent
   durability. Zipper and wheel failures appear repeatedly, suggesting manufacturing quality control issues."

Example 3 — Negative brand:
Reviews include: "Complete waste of money", "Handle broke on first trip", "Returning this immediately",
"Do not buy — wheels fell off at airport".
→ score: 2.8, label: "negative", summary: "Severe structural failures dominate the reviews. Multiple
   customers report handle and wheel failures on the very first trip, indicating a fundamental quality problem."

---

REVIEWS TO ANALYSE ({review_count} reviews for {brand}):

{reviews_text}

---

Return your analysis as a JSON object matching the SentimentOutput schema exactly.
"""


THEME_PROMPT = """You are a qualitative research analyst extracting recurring themes from customer reviews.

Your task: Identify the top 5 PRAISE themes and top 5 COMPLAINT themes from the reviews below for {brand} luggage.

WHAT MAKES A GOOD THEME:
- Specific, not vague. "Durable spinner wheels" is better than "good quality".
- Recurring across multiple reviews, not mentioned once.
- Actionable for a product manager reading this report.
- 3–6 words max. Think of it as a tag, not a sentence.

WHAT TO AVOID:
- Generic phrases like "good product" or "bad experience" — these tell us nothing.
- Repeating the same theme in different words.
- Themes mentioned by only one reviewer.

FEW-SHOT EXAMPLES:

Example praise themes (good):
  ✓ "Smooth 360-degree spinner wheels"
  ✓ "TSA lock works reliably"
  ✓ "Lightweight for cabin size"
  ✓ "Polycarbonate resists airport damage"
  ✓ "Excellent value under ₹4000"

Example praise themes (bad — too vague):
  ✗ "Good quality"
  ✗ "Nice product"
  ✗ "Happy with purchase"

Example complaint themes (good):
  ✓ "Zipper breaks within 6 months"
  ✓ "Handle wobbles after 3 trips"
  ✓ "Wheels crack on rough surfaces"
  ✓ "No customer service response"
  ✓ "Colour fades after one wash"

Example complaint themes (bad — too vague):
  ✗ "Poor quality"
  ✗ "Not worth it"
  ✗ "Disappointed"

---

REVIEWS ({review_count} reviews for {brand}):

{reviews_text}

---

Return exactly 5 praise themes and 5 complaint themes as a JSON object matching the ThemeOutput schema.
If genuine themes cannot be found (e.g., fewer than 3 reviews mention something), do not invent them —
reduce the list and note the limitation in the theme text itself (e.g., "insufficient data on handle quality").
"""


ASPECT_PROMPT = """You are a product quality analyst evaluating luggage brands for a competitive intelligence report.

Your task: Score {brand} luggage on 6 product aspects AND assess value-for-money.
Base ALL scores strictly on evidence from the customer reviews provided.
Do NOT invent scores — if an aspect is not mentioned in reviews, score it 5.0 and note "insufficient review data".

ASPECT SCORING GUIDE (0.0 – 10.0):
  0–2  : Catastrophic failures. Multiple reviewers report complete breakdown.
  3–4  : Frequent complaints. A consistent pattern of issues.
  5–6  : Average. Some praise, some complaints, no clear signal.
  7–8  : Good. Most customers satisfied, minor issues only.
  9–10 : Excellent. Near-universal praise, no meaningful complaints.

THE 6 ASPECTS:
  1. wheels    — smoothness, durability, spinner quality
  2. handle    — telescopic handle sturdiness, retraction mechanism
  3. zipper    — smoothness, durability, whether it breaks
  4. material  — shell hardness/flexibility, scratch resistance, finish quality
  5. size      — whether stated dimensions match reality, packing capacity
  6. durability — overall structural integrity after multiple trips

VALUE FOR MONEY ASSESSMENT:
  Average price for this brand's products: ₹{avg_price}
  Price band thresholds: budget = under ₹3500, mid-range = ₹3500–₹8000, premium = above ₹8000

  For value-for-money, answer: "Does the quality customers actually experience justify the price?"
  - A ₹2500 bag with wheel failures after 2 trips is POOR value even if it's cheap.
  - A ₹7000 bag where customers say "worth every rupee" is GOOD value even at mid-range price.
  - Compare sentiment quality signals against price band to reach a verdict.

FEW-SHOT EXAMPLES:

Example 1 — Strong wheels:
  Reviews say: "Wheels still smooth after 2 years", "360 spinner is buttery", "rolls perfectly on airport tiles"
  → wheels: score=8.8, summary="Spinner wheels praised across multiple reviewers for smoothness and longevity."

Example 2 — Poor zipper:
  Reviews say: "Zipper broke on third trip", "teeth came apart at airport", "had to tape my bag shut"
  → zipper: score=2.1, summary="Recurring zipper failures reported within weeks of purchase, a critical reliability concern."

Example 3 — Good value for money:
  Average price ₹3200 (budget band). Reviews say "amazing quality for the price", "feels like a ₹6000 bag".
  → value_for_money: score=8.5, price_band="budget", verdict="Customers consistently feel the build quality
     exceeds expectations for the ₹3200 price point. Multiple reviewers explicitly compare it favourably to
     more expensive brands."

Example 4 — Poor value for money:
  Average price ₹6500 (mid-range band). Reviews say "expected better at this price", "zipper broke in 2 months",
  "VIP is better for ₹2000 less".
  → value_for_money: score=3.8, price_band="mid-range", verdict="At ₹6500, customers expect premium durability
     but report the same failures seen in budget bags. Direct comparisons to cheaper alternatives are common,
     suggesting this brand is overpriced relative to quality delivered."

---

REVIEWS ({review_count} reviews for {brand}, average product price ₹{avg_price}):

{reviews_text}

---

Return your analysis as a JSON object matching the AspectOutput schema exactly.
Every aspect must have a score (float) and a summary (string citing review evidence).
"""


INSIGHTS_PROMPT = """You are a senior competitive intelligence analyst preparing a briefing for a brand manager
at an Indian luggage company. You have just analysed customer reviews across {brand_count} competing brands.

Your task: Generate exactly 5 NON-OBVIOUS insights from the data below.

WHAT MAKES AN INSIGHT NON-OBVIOUS:
  ✓ Reveals a pattern not visible from ratings alone
  ✓ Compares two brands in a surprising way
  ✓ Identifies an opportunity or threat a brand manager should act on
  ✓ Highlights a disconnect (e.g., high rating but specific failure pattern)
  ✓ Shows a value or pricing anomaly

WHAT IS NOT AN INSIGHT (do not write these):
  ✗ "{{Brand}} has the highest rating" — obvious from the data
  ✗ "{{Brand}} customers are happy" — too generic
  ✗ "Customers care about quality" — universal, not specific
  ✗ Restating a theme without connecting it to a competitive implication

FEW-SHOT EXAMPLES OF GOOD INSIGHTS:

Example 1:
  headline: "Safari wins on loyalty, not first impressions"
  explanation: "Safari reviews contain the highest frequency of repeat-purchase mentions
  ('my third Safari bag') despite not having the highest sentiment score. This suggests
  Safari builds trust over time — a retention advantage that raw ratings don't capture.
  Competitors should note that Safari's moat is habit, not hype."

Example 2:
  headline: "Skybags undercuts on price but overpromises on durability"
  explanation: "Skybags sits in the budget price band (avg ₹2800) yet its marketing
  language in listings implies premium durability. Review data shows a 4.1 durability score
  with wheel and zipper failures within 3 months. This expectation gap is driving the most
  emotionally negative reviews in the dataset — customers feel deceived, not just disappointed."

Example 3:
  headline: "Zipper failure is the silent rating killer across all brands"
  explanation: "Zipper complaints appear in the top-3 complaint themes for 4 out of 6 brands,
  yet average star ratings remain above 4.0 for all of them. This suggests customers rate
  generously overall but leave detailed negative zipper feedback that suppresses repeat
  purchases. Any brand that solves zipper durability could capture significant market share."

---

BRAND SUMMARIES TO ANALYSE:

{brand_summaries}

---

Generate exactly 5 insights. Each must have a short headline (max 10 words) and a 2-3 sentence explanation
grounded in specific data from the summaries above. Return as a JSON object matching the InsightsOutput schema.
"""
