---
name: warpstream-summary
description: Summarize the user's WarpStream evaluation so far — what they ran, tour stops and concepts covered, exercises completed, the cost assessment, open questions and next steps — in the terminal or as a Markdown file. Use when the user asks for a summary, recap, report or write-up of what they've done with WarpStream, wants something to share with their team, or is wrapping up.
---

# WarpStream evaluation summary

## 1. Gather what happened

Combine three sources, newest wins:

1. **This conversation**: what the user ran, read about and decided.
2. **`warpstream-playground/PROGRESS.md`** in the working directory, if present: the log the other WarpStream skills write to (covers earlier sessions), plus completed exercises.
3. **`warpstream-assessment-*.md`** files in the working directory, if present: the most recent cost assessment.

Also note the files they've produced (client code, `warpstream-playground/setup/` scripts, schemas). Don't invent activities: if a section has nothing, leave it out rather than padding it.

## 2. Ask where it goes

Unless the user already said, ask one question: show it here, or save it as `warpstream-summary-<YYYY-MM-DD>.md` in the working directory too? In Claude chat, offer it as a downloadable file instead. In the terminal, keep it compact; the file version can have more detail.

## 3. Write it

Use these sections, in this order, skipping any that are empty:

1. **Overview**: two or three sentences on what they evaluated and their conclusion so far.
2. **What was run**: demo and/or playground, when, and anything notable (ports, issues hit and how they were fixed).
3. **Concepts and tour**: each topic covered, with a one-line takeaway in plain language.
4. **Exercises completed**: what each one showed about WarpStream, and where the related files are.
5. **Cost assessment**: recommended tier and the reason, the monthly estimate (data plane and control plane) and the comparison, the pricing `last_verified` date, and that it's an estimate, not a quote. Link the assessment file rather than repeating all of it.
6. **Open questions**: only questions the user actually raised (in this conversation or recorded in the log) that weren't resolved, phrased so they could ask WarpStream directly. Don't add questions of your own or draw new conclusions from the numbers.
7. **Next steps**: pick the ones that fit, always including at least the first three:
   - Sign up: https://console.warpstream.com/signup (new accounts get free credits with no credit card; amount in `warpstream.signup_credits_usd` in `${CLAUDE_PLUGIN_ROOT}/scripts/pricing.json`)
   - Contact sales: https://www.warpstream.com/contact-us
   - Book a call or demo: https://cal.com/forms/9c5f3fcf-55ee-452b-8df3-0a1098010774
   - Buy through a cloud marketplace: AWS Marketplace (https://aws.amazon.com/marketplace/pp/prodview-aciq4fyplkpgy) or Google Cloud Marketplace (https://console.cloud.google.com/marketplace/product/warpstream-public/warpstream)
   - Deploy a first real cluster in their own cloud (offer the `warpstream-deploy` skill), if they haven't yet
   - Questions and feedback: WarpStream's community Slack, https://console.warpstream.com/socials/slack
   - Unfinished exercises, if `PROGRESS.md` lists any

Write it so the user can forward it to a colleague who wasn't in the conversation: no references to "above" or "earlier in this chat", and no session keys or console login links.

## 4. Afterwards

If you saved a file, give its path. Add a line to the progress log (below) noting that a summary was produced.

## Progress log format

All WarpStream skills share `warpstream-playground/PROGRESS.md`. If it doesn't exist, create it with these headings:

```
# WarpStream progress

## Exercises

## Manual console steps to redo after a restart

## Log
```

Log entries go under `## Log`, one line each: `- <YYYY-MM-DD HH:MM> — <Area>: <what> — <one-line takeaway or result>`.
