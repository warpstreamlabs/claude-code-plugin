---
description: Start an empty local WarpStream cluster (warpstream playground) to build against
argument-hint: "[-kafkaPort <port>] [-timeout <duration>]"
---

Use the `warpstream-demo` skill to run WarpStream locally in **playground** mode (an empty cluster, no synthetic data), following its pre-flight, run, orient and troubleshooting steps. Ask before installing anything.

Pass these flags through to `warpstream playground` if given: $ARGUMENTS

Once it's running, offer to write a producer and consumer with the `warpstream-clients` skill or to point the user's own project at it.
