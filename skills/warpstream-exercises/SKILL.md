---
name: warpstream-exercises
description: Hands-on exercises against a local WarpStream demo or playground — produce and consume, register schemas and see Schema Validation reject a bad record, materialize a topic as an Iceberg table with Tableflow and evolve its schema, build an Orbit replication pipeline as a migration rehearsal, and use Diagnostics and Events to find a deliberately caused problem. Use when the user wants to practice, try a feature hands-on, or asks "what can I do next" with a cluster running.
---

# WarpStream hands-on exercises

Each exercise is self-contained, takes roughly 5–15 minutes, and runs against the local demo or playground. Before starting, check a cluster is running; if not, start one with the `warpstream-demo` skill (playground mode is best for exercises).

**How to run them:**
- Offer the list and let the user pick, or suggest one that fits their persona (data engineers: schemas and Tableflow; platform engineers: Orbit and Operate).
- Before each step, look up the current configuration names, YAML shapes and console paths with the `warpstream-docs` MCP. Don't write config keys from memory; they change between Agent versions. The pages to start from are listed with each exercise.
- Do the work in the terminal where you can (Claude Code), and tell the user exactly where to click in the console when a step happens there.
- End each exercise with what it shows about running WarpStream in production, in one or two sentences.

## Save as you go

The demo and playground stop after their timeout, and a restart starts from an empty cluster in a new temporary account. So that a restart takes a minute rather than redoing every exercise, save the cluster-side setup as you go, in a `warpstream-playground/` folder in the user's working directory. Tell the user once, the first time you create it, what it's for.

```
warpstream-playground/
├── start.sh            # the exact command, flags and environment variables used to start the cluster
├── setup/
│   ├── 01-produce-consume.sh
│   ├── 02-schemas.sh
│   └── ...             # one script per exercise, run in filename order
├── tableflow.yaml      # console-only configuration, to paste back in after a restart
├── orbit.yaml
└── PROGRESS.md         # exercises done, manual console steps to redo, and the log warpstream-summary reads
```

- Write each `setup/` script **as you do the exercise**, containing only the steps that change the cluster: creating topics (with their configs), registering schemas, seeding records, creating consumer groups. Leave out one-off checks such as fetching records or showing a rejection.
- Make scripts safe to rerun: tolerate "already exists" errors, and read ports from environment variables with the defaults (`KAFKA_PORT=${KAFKA_PORT:-9092}`, `SR_PORT=${SR_PORT:-9094}`). Use `warpstream kcmd` and `curl` where they're enough; where they aren't (for example, creating a topic with configs), use a small script in the language of the user's client code.
- Steps that happen in the console (Tableflow tables, Orbit configuration) can't be scripted from here. Save the configuration you used to a file, and list the manual step in `PROGRESS.md`.
- Update `start.sh` whenever the start command changes, for example when exercise 2 adds `WARPSTREAM_SCHEMA_REGISTRY_URL`.
- `PROGRESS.md` has the headings `# WarpStream progress`, `## Exercises`, `## Manual console steps to redo after a restart` and `## Log` (create them if the file doesn't exist; other WarpStream skills write to it too). After each exercise, tick it off under `## Exercises`, and add a line under `## Log`: `- <YYYY-MM-DD HH:MM> — Exercise <n>: <name> — <what it showed>`.

## Restore after a restart

When the `warpstream-demo` skill restarts the cluster:

1. Start it with `warpstream-playground/start.sh` (in the background, as the demo skill describes).
2. Run each script in `warpstream-playground/setup/` in order, and stop to report if one fails.
3. Walk the user through the manual console steps listed in `PROGRESS.md`, using the saved configuration files.
4. Confirm the state is back (topics listed, schemas registered) and pick up at the next unfinished exercise in `PROGRESS.md`.

## 1. Produce and consume

Use the `warpstream-clients` skill to write a producer and consumer in the user's language, or point their own project at `localhost:9092`. Success: their code produces records and reads them back, and they can see the topic in the console.

Save: `setup/01-produce-consume.sh` creates the topic. The client code itself stays where the user keeps it.

## 2. Schemas and Schema Validation

Docs: "Setup" (BYOC Schema Registry) and "Enforce Schemas" (schema validation). Check the Setup page for which schema formats the BYOC Schema Registry supports before offering a choice; at the time of writing it was Avro and Protobuf, with JSON Schema listed as coming soon.

1. **Agent setup.** For the Agent to validate against the local registry it needs the registry's URL. Start (or restart) the playground with the environment variable from the "Enforce Schemas" page, e.g. `WARPSTREAM_SCHEMA_REGISTRY_URL=http://localhost:9094 warpstream playground` (use the Schema Registry port the CLI printed). Without it, validated topics reject every record, including valid ones.
2. Register a schema with the local Schema Registry, e.g. `curl -X POST localhost:9094/subjects/<topic>-value/versions -H 'Content-Type: application/vnd.schemaregistry.v1+json' -d '{"schema": "<escaped Avro schema>"}'`.
3. Create the topic with validation on. Per the "Enforce Schemas" page, set `warpstream.value.schema.validation=true` **and** `warpstream.schema.validation.warning.only=false`. The warning-only setting defaults to true, which only flags bad records instead of rejecting them. Confirm with `warpstream kcmd -type describe-topic-configs -topic <topic>`.
4. Produce a valid record serialized in Confluent wire format (magic byte, schema ID, payload) with a Schema Registry-aware serializer, and show it's accepted.
5. Produce a bad record (wrong payload, unknown schema ID, or plain JSON without the wire format) and show the client receives `INVALID_RECORD` ("Broker failed to validate record").

Save: add `WARPSTREAM_SCHEMA_REGISTRY_URL` to `start.sh`, keep the schema file in `warpstream-playground/`, and have `setup/02-schemas.sh` register it and create the validated topic with both configs.

Point out that the pricing page lists broker-level Schema Validation from the Fundamentals tier up (`${CLAUDE_PLUGIN_ROOT}/scripts/pricing.json` has the tier features), and that the playground lets them try it anyway.

## 3. Tableflow: topic to Iceberg table

Docs: "Tableflow Setup" and the catalog/query-engine pages.

**Quick version (demo mode):** `warpstream demo` already creates a table from its demo topic, prints the table configuration, and prints a DuckDB query once the first snapshot exists (it can take a few minutes; the CLI says when). Run that query (DuckDB with the iceberg extension; ask before installing) and walk through the printed configuration, including the transform. Because demo mode writes to a local directory, the table is a real Iceberg table on disk.

**Full version:**
1. Open the Tableflow cluster in the console and its configuration.
2. Add the local Kafka cluster as a source and define a table for a topic (the demo topic or the one from exercise 1), with its schema. Use the demo's printed configuration as a template.
3. Watch ingestion start (table status in the console, or `tableflow_logs` in Events).
4. Evolve the schema (add an optional field), produce records with the new field, and show the table schema update.
5. To query from outside: in demo mode, use the local data directory as above. The playground keeps data in memory, so there it's enough to see ingestion in the console but not to query the files.

Save: the table configuration in `warpstream-playground/tableflow.yaml` (the source topic is recreated by an earlier setup script), and the console step in `PROGRESS.md`.

## 4. Orbit: migration rehearsal

Docs: "Orbit (Cluster Linking)".

Frame this as rehearsing a migration from an existing Kafka cluster.

1. Pick a source cluster: a Kafka cluster the user already runs locally, or a second throwaway cluster with `warpstream local`. It needs **all** its ports moved off the playground's, e.g. `warpstream local -kafkaPort 9192 -httpPort 8180 -schemaRegistryPort 9194 -schemaRegistryHTTPPort 8170 -tableflowInternalHTTPPort 8181` (check `warpstream local -h` for the current flags). Seed it with a topic and records (`warpstream kcmd -type produce -topic orders -records "a,,b,,c" -bootstrap-port 9192`) and a consumer group.
2. Configure Orbit on the playground cluster in the console, pointing at the source brokers, with a topic mapping and consumer group sync.
3. Show that records arrive with the same offsets and that consumer group offsets are synced, so consumers can switch over and resume where they left off.
4. Walk through the cut-over order from the docs' Migration section (replication, then consumers, then producers).

If the second cluster can't be reached from the playground Agent, say so plainly and walk through the configuration and migration steps from the docs instead.

Save: `setup/04-orbit-source.sh` starts the source cluster in the background (if it isn't already running) and seeds it. Put the Orbit configuration in `warpstream-playground/orbit.yaml`, and the console step in `PROGRESS.md`.

## 5. Operate: Diagnostics and Events

Docs: "Diagnostics" and "Events".

1. Open Diagnostics in the console and explain one or two of the checks shown.
2. Open the cluster's Events tab (the demo and playground switch Events on for you; on other clusters, toggle it on there) and run a preset query over `agent_logs`.
3. Cause a problem on purpose, then find it. Good options:
   - Produce invalid records to a schema-validated topic (from exercise 2) and find the rejections.
   - Start a consumer group, stop it, keep producing, and find the growing lag.
   - Configure a pipeline or Tableflow table with a wrong field and find the error in `pipeline_logs` or `tableflow_logs`.
4. Show how they would have found it without knowing the cause in advance: Diagnostics first, then narrow down in Events.
