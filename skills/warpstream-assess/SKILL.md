---
name: warpstream-assess
description: Assess whether WarpStream fits a workload — a short conversational assessment that recommends a WarpStream tier with reasons, estimates monthly cost with the bundled estimator, compares it with Apache Kafka, Amazon MSK (Standard, Express, Serverless), Kinesis and Google Cloud Managed Kafka, outlines a migration, exports a Markdown summary and offers sign-up, sales or a call. Use when the user asks about WarpStream pricing, cost, savings, TCO, which tier or plan they need, comparisons with other platforms' cost, or migrating to WarpStream.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/estimate.py *)
---

# WarpStream fit, tier and cost assessment

The bundled estimator reproduces the calculator on warpstream.com/pricing. Prices, tier features and limits live in `${CLAUDE_PLUGIN_ROOT}/scripts/pricing.json`; read it when you need a tier fact, and never state prices or features from memory.

## 1. Ask (5–6 questions, conversationally)

Skip anything the user has already told you; ask in one or two short messages, not a form. Accept rough answers and state the assumption you made.

1. **Current platform**: self-hosted Kafka (how many zones?), MSK (Standard, Express or Serverless), Confluent, Redpanda, Kinesis, Google Cloud Managed Kafka, or nothing yet. Is this a migration or a new workload?
2. **Workload**: write throughput (MiB/s, uncompressed, peak or sustained average), retention (days), partition count. If they only know messages per second, ask for an average message size and convert.
3. **Environment**: production or dev/test?
4. **Requirements**: uptime SLA, latency needs (typical and p99 end-to-end), security and compliance (private networking, audit logs, regulated data such as PHI or PCI).
5. **Features**: schema registry, Tableflow (Kafka topics as Iceberg tables), managed data pipelines, multi-region.
6. Anything that would make WarpStream a non-starter for them (only if not already clear).

## 2. Recommend a tier

Read `warpstream.tiers` and `warpstream.tier_notes` in pricing.json. Features are cumulative from Dev up. Pick the **lowest** tier that satisfies every stated need, and say which need set the floor ("you need audit logs, so Pro is the minimum").

- Production with an uptime SLA needs at least the lowest tier that has an SLA meeting their requirement; Dev has none.
- Feature needs map to the tier that `adds_features` them.
- Partition count alone shouldn't force an upgrade: tier partition limits are defaults that can be raised on request. Mention it instead.
- Recommend Enterprise, and say a conversation with sales is the next step, for: multi-region HA or the highest SLA, a dedicated control plane cell, regulated data at scale, large migrations, or the add-ons in `warpstream.add_ons_contact_sales` (private networking, self-managed control plane).
- Don't recommend a higher tier "to be safe". If you're unsure whether they need a feature, say what it's for and let them decide.

## 3. Estimate cost

Run the estimator (Enterprise isn't priced; for Enterprise, estimate at Pro and say the real price comes from sales):

```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/estimate.py --write-mibs <MiB/s> --retention-days <days> --partitions <n> --tier <dev|fundamentals|pro> --format json
```

Optional flags:
- `--compare <ids>`: comma-separated ids or `all` (the default). Lead with their current platform; include one or two alternatives, not all seven, unless they ask. Ids: `kafka-3-az`, `kafka-1-az`, `kafka-msk`, `kafka-msk-express`, `kafka-msk-serverless`, `kafka-kinesis`, `gcp-msk`, `redpanda`.
- `--low-latency` (S3 Express One Zone profile), `--fetch-from-follower` and `--tiered-storage` (affect the Kafka comparisons; use them when the user's current setup uses them).
- `--schema-registry` and `--tableflow-mibs <MiB/s>` add those products from published unit prices. They aren't part of the website calculator; say so.
- `--format text` for a terminal view, `--format markdown` for the export, `--format html --output <file>` for a shareable report.

Present the result:

- **Claude Code terminal**: show `--format text` output (Unicode bars) and a two-line summary.
- **Claude chat or Cowork**: render a clear visual (table plus bar chart) from the JSON.
- Always show: the WarpStream total split into **data plane** (paid to their cloud provider: Agent VMs, object storage) and **control plane** (paid to WarpStream), the comparison totals, the key assumptions, the `last_verified` date, that it's an estimate not a quote, and the pricing page link (`pricing_page_url` in the output).
- Pass on any `notes` from the output (for example partitions above a tier's default limit).
- For Kinesis, say migration means changing client code (it isn't Kafka-compatible).
- If the script can't run in this environment, don't calculate prices by hand. Link the calculator at https://www.warpstream.com/pricing and offer to explain the inputs.

### Competitive context

- MSK: also link https://www.warpstream.com/compare/warpstream-vs-amazon-msk
- **Redpanda**: Redpanda doesn't publish its rates (see the `redpanda` entry in pricing.json and its `last_verified` date), so a cost comparison isn't possible. Say that, link https://www.warpstream.com/compare/warpstream-vs-redpanda, and offer to estimate the WarpStream side.
- Confluent or other platforms not in the estimator: say they aren't in the calculator; don't invent prices. Offer the WarpStream estimate and suggest sales for a like-for-like comparison.

Be fair: list prices, visible assumptions, documented sources. If WarpStream comes out more expensive for their inputs, say so.

## 4. Migration outline (for migrations)

Look up each item with the `warpstream-docs` MCP and link the pages:

1. **Configuration translation**: map their broker and topic configs using the docs page "Kafka vs WarpStream Configuration Reference"; flag anything unsupported.
2. **Data and offsets**: Orbit replicates topics with offsets preserved, plus consumer group offsets, ACLs and configs, so consumers resume where they left off.
3. **Schemas**: Schema Linking copies schemas from a Confluent-compatible registry; Schema Validation can also use AWS Glue Schema Registry.
4. **Cut-over order**: replication first, then consumers, then producers (per the Orbit docs).
5. **Client changes**: bootstrap URL, zone-aware client IDs, and recommended client settings (`warpstream-clients`).

## 5. Export the summary

Offer to save the assessment as Markdown. In Claude Code or Cowork, write `warpstream-assessment-<YYYY-MM-DD>.md` in the user's working directory; in chat, provide it as a downloadable file. Contents:

1. Inputs (as given, plus any assumptions you made)
2. Recommended tier and why
3. Cost estimate (`--format markdown` output) with assumptions and the verification date
4. Migration outline (if relevant)
5. Next steps with links (below)

## 6. Next steps (always offer all three)

- **Start self-serve**: sign up at https://console.warpstream.com/signup. New accounts get free credits with no credit card required (amount and terms: `warpstream.signup_credits_usd` and `signup_credits_note` in pricing.json).
- **Contact sales**: https://www.warpstream.com/contact-us
- **Book a call or demo**: https://cal.com/forms/9c5f3fcf-55ee-452b-8df3-0a1098010774

Recommend sales specifically for Enterprise needs, multi-region, regulated data, large migrations or add-ons. Mention that WarpStream is also available through the cloud marketplaces, which suits teams that want to buy through an existing cloud agreement. Use these links as they are; don't search for others:

- AWS Marketplace: https://aws.amazon.com/marketplace/pp/prodview-aciq4fyplkpgy
- Google Cloud Marketplace: https://console.cloud.google.com/marketplace/product/warpstream-public/warpstream

For questions or feedback, point them to WarpStream's community Slack: https://console.warpstream.com/socials/slack. Once they have an account, offer to help deploy their first real cluster (`warpstream-deploy`).

## Progress log

**Progress log:** if `warpstream-playground/PROGRESS.md` exists in the working directory, or a demo or playground was started in this session, add a line under its `## Log` heading: `- <YYYY-MM-DD HH:MM> — <Area>: <what> — <one-line takeaway or result>`. If the file doesn't exist yet, create it with the headings `# WarpStream progress`, `## Exercises`, `## Manual console steps to redo after a restart` and `## Log`. Don't create it just for a one-off question. `warpstream-summary` reads this log.

Log: the result: recommended tier and why, the WarpStream monthly estimate, the main comparison, and the assessment file path if you saved one.
