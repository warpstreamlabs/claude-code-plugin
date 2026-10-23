---
name: warpstream-tour
description: Guided tour of what a local WarpStream demo or playground creates: the BYOC Kafka cluster, the BYOC Schema Registry, the Tableflow cluster and the WarpStream console. Use when the user asks what the demo created, wants a walkthrough or tour, or asks about a specific part ("show me Tableflow", "what's the schema registry for?") of a running demo or playground.
---

# Tour of the WarpStream playground

The tour can be **structured** (the user ran `/warpstream-tour`: go through the stops in order, pausing after each) or **self-paced** (the user asked about one part: go straight to that stop, then offer the next).

Before starting, check that a demo or playground is running (the background task you started, or `warpstream kcmd -type diagnose-connection -bootstrap-host localhost -bootstrap-port 9092`). If not, offer to start one with the `warpstream-demo` skill.

For each stop: say what it is in two or three sentences, show it (run a command or point to the console page), and connect it to why it matters in production. Look up specifics with the `warpstream-docs` MCP rather than relying on memory.

## Stop 1: The Kafka cluster (BYOC)

- What runs locally is a WarpStream **Agent**: a stateless process that speaks the Kafka protocol. In production, Agents run in the customer's own cloud account (BYOC, "bring your own cloud") and write to the customer's own object storage bucket; the WarpStream control plane only handles metadata.
- Show it: list topics and read a few records with the built-in client, for example `warpstream kcmd --type fetch --topic <topic> --offset 0` (check `warpstream kcmd -h` for current flags).
- In the console: the virtual cluster view, topics, consumer groups and the Agent list.
- Why it matters: no broker disks, no partition leaders, no inter-zone replication; `warpstream-concepts` goes deeper.

## Stop 2: The BYOC Schema Registry

- A Confluent API-compatible schema registry that also runs as stateless Agents in the customer's cloud, storing schemas in object storage.
- Show it: the Schema Registry port is printed at startup (default 9094). List subjects with `curl -s localhost:9094/subjects`.
- Related features to mention: **Schema Validation** (Agents reject records that don't match a schema) and **Schema Linking** (migrating schemas from an existing Confluent-compatible registry). The exercises cover validation hands-on.

## Stop 3: The Tableflow cluster

- Tableflow materializes Kafka topics as **Apache Iceberg** tables in object storage and keeps them compacted. Tableflow Agents only do Tableflow work; they don't expose the Kafka protocol, so clients never connect to them.
- It works with any Kafka-compatible source cluster, not just WarpStream.
- Show it: in demo mode, the CLI already created a table from the demo topic and printed its configuration and a DuckDB query. Once the CLI says the table is queryable, run that query (needs DuckDB with the iceberg extension; ask before installing it). Point out the `transforms` step in the printed configuration, which reshapes records on the way in. In the console, open the Tableflow cluster and its configuration (source clusters, tables, schemas).

## Stop 4: The console

Walk through the console pages that matter for evaluation, using the account link from the CLI output:

- Cluster overview and **Diagnostics** (health, cost and performance checks with suggested fixes).
- **Events** (searchable agent, pipeline, Tableflow and other logs; the demo and playground switch it on, other clusters need it enabled).
- **Pipelines** (managed data pipelines running inside the Agents) and **Orbit** (offset-preserving replication from another Kafka cluster).
- Where API keys and usage/billing live, for when they move to a real account.

## Wrap up

Offer one next step based on what they found most interesting: the hands-on exercises (`warpstream-exercises`), writing their own client (`warpstream-clients`), or a cost and fit assessment (`/warpstream-assess`).

Links you give the user to warpstream.com, docs.warpstream.com or console.warpstream.com end with `?utm_source=claude&utm_medium=claude&utm_campaign=claude-plugin` (or `&...` if the URL already has a query string).
