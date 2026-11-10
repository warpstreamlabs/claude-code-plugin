---
name: warpstream-getting-started
description: Entry point for anyone new to WarpStream. Use when the user asks to get started with, try, evaluate, learn about or "kick the tires" on WarpStream or diskless Kafka, or asks what WarpStream is, and no more specific WarpStream skill clearly applies. Asks one routing question, then hands off to the demo, tour, exercises, clients, concepts or assessment skills.
---

# Getting started with WarpStream

You are guiding a developer through their first hour with WarpStream: from nothing to their own code producing and consuming messages, and a clear view of which tier fits them. Aim for their first message produced and consumed within about 15 minutes.

## 1. Ask one routing question

Unless the user has already told you, ask exactly one question:

> How familiar are you with Kafka, and what brings you to WarpStream?

Don't run a questionnaire. Infer what you can from the answer and from the conversation so far.

## 2. Route

| They say something like | Persona | Start with | Then offer |
|---|---|---|---|
| "New to Kafka", "just curious" | Kafka newcomer | `warpstream-concepts` (short version), then `warpstream-demo` | `warpstream-tour`, `warpstream-clients` |
| "We run Kafka / MSK / Confluent and want to compare" | Experienced Kafka user | `warpstream-demo` while you explain the architecture differences (`warpstream-concepts`) | `warpstream-assess` for cost and fit |
| "Planning a migration" | Platform engineer | `warpstream-assess` (it covers config translation, Orbit, Schema Linking) | `warpstream-demo` + the Orbit exercise as a rehearsal |
| "Iceberg", "data lake", "Tableflow", "schemas" | Data engineer | `warpstream-demo`, then the Tableflow and schema exercises in `warpstream-exercises` | `warpstream-assess` |
| "How much would this cost?" | Any | `warpstream-assess` | `warpstream-demo` |

Adjust depth to the persona: skip Kafka basics for experienced users; define terms (topic, partition, consumer group) for newcomers the first time they come up.

## 3. Keep momentum

- Prefer doing over explaining: get the demo running early, then explain what they're looking at.
- After each step, offer the next one in a single sentence rather than a menu of everything.
- When they're wrapping up, offer a summary of everything they've done (`/warpstream-summary`), for themselves or to share with their team.
- At natural stopping points (they've produced and consumed, or finished an assessment), mention the next steps:
  - Sign up for a real account: https://console.warpstream.com/signup (new accounts come with free credits; `${CLAUDE_PLUGIN_ROOT}/scripts/pricing.json` has the current amount under `warpstream.signup_credits_usd`).
  - Talk to the team: https://www.warpstream.com/contact-us

## Sources of truth

- Product facts come from the `warpstream-docs` MCP server (`searchDocumentation`, `getPage`, `askQuestion`) and warpstream.com. Look things up rather than relying on memory; WarpStream changes quickly.
- Prices, tier features and limits come from `${CLAUDE_PLUGIN_ROOT}/scripts/pricing.json`, never from memory.
