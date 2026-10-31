# Jobee running cost analysis

Date: 31 October 2026. Everything here is an **estimate**. Token counts come from the caps and comments in the code, not from measured usage, and prices are list prices that were not all checked against the vendor's own page. Replace them with measured numbers before quoting them as facts.

## Summary

- A new learner costs about **$0.02–0.04 (RM 0.09–0.18)** to serve, at every scale from 1,000 to 1 million learners a month.
- The AI model calls are about 85–90% of the cost.
- One paid university seat at RM 10 a year covers the model and hosting cost of roughly 70 free learners at the high case.

## 1. Model cost for one learner

Token sizes come from the code: the output caps in `roadmap/planner.py` (12,000, with the note that a 50-node plan is about 4k) and `challenge/generator.py` (8,000, a challenge is about 800), and `max_tokens` in the resume, reasons and judge calls. Output tokens include the model's hidden reasoning, which is billed as output.

| Step | Input tokens | Output tokens |
|---|---|---|
| Resume skill extraction (optional) | ~3k | ~0.8k |
| Personalised skill list | ~2k | ~0.3k |
| Roadmap plan | ~3k | ~6k |
| Starter project | ~2k | ~2.3k |
| Judging 1–2 submissions | ~3k | ~1k |
| **Total** | **~13k** | **~10k** |

Price used for Gemini 3.1 Flash-Lite Preview: **$0.25 per 1M input tokens, $1.50 per 1M output tokens** (cached input $0.025). That gives about **$0.018 per learner**. A high case doubles it for retries and regenerated roadmaps: about **$0.04**.

Role-and-interest reasons are stored after the first write, so they add almost nothing.

## 2. Monthly cost as it scales

| New learners / month | AI model | Database + login | Email codes | Backend servers | Static hosting | Total | Per learner |
|---|---|---|---|---|---|---|---|
| 1,000 | $18–36 | $25 | $0 | $10 | $0 | ~$55–70 | $0.06 |
| 10,000 | $180–360 | $25 | $20 | $20 | $0 | ~$245–425 | $0.025–0.04 |
| 100,000 | $1.8k–3.6k | ~$75 | ~$50 | ~$50 | ~$20 | ~$2.0k–3.8k | $0.02–0.04 |
| 1,000,000 | $18k–36k | ~$3.1k | ~$200 | ~$300 | ~$100 | ~$22k–40k | $0.022–0.04 |

### Assumptions behind each column

- **AI model:** learners × $0.018 (low) or × $0.036 (high).
- **Database + login:** Supabase Pro at $25 a month, 100,000 monthly active users included, then about $0.00325 per extra user. At 1 million that is about $2.9k of the $3.1k, plus a larger compute add-on. Storage is about 40 KB per learner, so 100,000 learners is about 4 GB, inside the 8 GB included.
- **Email codes:** about two emails per learner. The built-in Supabase email sender is heavily rate-limited, so a custom sender (Resend, then Amazon SES at scale) is needed from launch.
- **Backend servers:** roadmap builds are mostly waiting on the model. Peak load is about 10 concurrent builds at 100,000 learners a month and about 100 at 1 million, so one or two small servers cover the first and a handful cover the second. LightGBM retraining on the Signal page takes about 2 seconds of CPU, is cached, and is limited to 2 at once.
- **Static hosting:** the frontend is a static build; cost is mainly bandwidth at the high end.
- Not included: staff time, domain, monitoring, payment fees, support, and any charge from the Grafilab gateway beyond the model price.

## 3. Biggest cost levers

1. **Reuse roadmaps** for identical role-and-skill sets. This is the largest saving; the code already has a "reused" flag, so measure how often it fires.
2. **Cut hidden reasoning on the roadmap call**, the single largest cost (up to 12,000 output tokens allowed).
3. **Cache the fixed instructions** (cached input is about a tenth of the price) and use the batch API (about half price) for anything that isn't interactive.
4. **Rate-limit the resume upload.** It runs before email verification, so a script could run up the bill. Limit per address or add a bot check.

## 4. What could change these numbers

- The Grafilab gateway may charge differently from list price, or give free credits.
- Token counts are estimates. Paste a day of gateway usage and they can be replaced with measured values.
- Supabase and email prices are from memory and need checking before they are quoted to judges.
- Exchange rate assumed: about RM 4.5 per US dollar.

## Sources

Model price (used for section 1):

- [Gemini 3.1 Flash Lite Preview pricing, pricepertoken.com](https://pricepertoken.com/pricing-page/model/google-gemini-3.1-flash-lite-preview)
- [Gemini 3.1 Flash Lite Preview, Eden AI](https://www.edenai.co/models/gemini-3-1-flash-lite-preview)
- [Gemini 3.1 Flash Lite Preview, Requesty](https://www.requesty.ai/models/vertex/gemini-3.1-flash-lite-preview)
- [Gemini 3.1 Flash Lite Preview, BazaarLink](https://bazaarlink.ai/en/models/google-gemini-3.1-flash-lite-preview)
- [Google AI pricing page](https://ai.google.dev/pricing) (official; its table did not load in the search, so the rate is unconfirmed against it)

Note: one listing shows $0.125 input and $0.75 output, but that is for the non-preview "Gemini 3.1 Flash Lite", not the preview model used here.

Figures from memory, not looked up this session (check before use):

- Supabase Pro plan, included monthly active users and per-user overage: https://supabase.com/pricing
- Resend and Amazon SES email pricing: https://resend.com/pricing and https://aws.amazon.com/ses/pricing/
- Container hosting prices for the backend servers (depends on where it is deployed).

Code the token sizes come from:

- `src/backend/app/roadmap/planner.py`
- `src/backend/app/challenge/generator.py`, `src/backend/app/challenge/judge.py`
- `src/backend/app/resume/gateway.py`
- `src/backend/app/jobs/reasons.py`
- `src/backend/app/llm/service.py`
