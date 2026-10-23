---
name: warpstream-clients
description: Write or configure Kafka producer and consumer code for WarpStream in Python, Java, Go or Node.js with WarpStream's recommended client settings, or point an existing project at a local WarpStream cluster. Use when the user wants sample code, asks how to connect a Kafka client or app to WarpStream, or asks about client settings, throughput tuning, idempotence or client IDs for WarpStream.
---

# Kafka clients for WarpStream

WarpStream speaks the Kafka protocol, so standard Kafka clients work unchanged: set the bootstrap server and go. A few settings matter more than with Apache Kafka because WarpStream writes to object storage (higher per-request latency, so throughput depends on concurrency and batch size).

## 1. Get the current recommended settings

The recommended values change over time, so don't write them from memory. Fetch the page with the `warpstream-docs` MCP:

- `getPage` https://docs.warpstream.com/warpstream/kafka/configure-kafka-client/tuning-for-performance (per-client settings tables)
- `getPage` https://docs.warpstream.com/warpstream/kafka/configure-kafka-client/known-issues when idempotence, transactions or a specific client's behavior comes up
- `getPage` https://docs.warpstream.com/warpstream/kafka/configure-kafka-client/configure-clients-to-eliminate-az-networking-costs for zone-aware client IDs in production

If the docs can't be reached, use plain client defaults with the bootstrap server set, say that the code isn't tuned, and link the tuning page.

## 2. Pick the client

| Language | Default library | Notes |
|---|---|---|
| Python | `confluent-kafka` (librdkafka) | Use the librdkafka settings table |
| Java | `org.apache.kafka:kafka-clients` | Use the Java table; don't set `client.rack` or rack-aware assignment (the docs explain why) |
| Go | `github.com/twmb/franz-go` | Use the franz-go table |
| Node.js | `@confluentinc/kafka-javascript` (librdkafka) or `kafkajs` | Ask which they prefer if they don't already use one; each has its own table |

If the user already has a project, use the library it already depends on and change only connection settings and the recommended tuning.

## 3. Write the code

Produce a small, runnable producer and consumer pair:

- Bootstrap server `localhost:9092` for the local demo or playground (or the `-kafkaPort` they chose), read from an environment variable such as `KAFKA_BOOTSTRAP_SERVERS` so the same code works against a real cluster later.
- Apply the recommended settings from step 1, with a short comment linking the tuning page. Follow the docs on idempotence: the recommended producer configs disable it for throughput, and the docs explain the trade-off. Mention it in one sentence if the user's use case needs exactly-once.
- Prefer null keys unless the user needs ordering per key (the docs explain why this helps batching with librdkafka).
- Create the topic first (`warpstream kcmd --type create-topic --topic <name>`) or rely on auto-creation if the cluster allows it; check `warpstream kcmd -h`.
- Include install instructions (`pip install`, Maven/Gradle coordinates, `go get`, `npm install`) and the command to run each part.

Then run it (in Claude Code) or give the commands, and confirm records arrive: the consumer output, `warpstream kcmd --type fetch --topic <name> --offset 0`, or the topic page in the console.

## 4. Pointing an existing app at WarpStream

1. Find where the app configures Kafka (bootstrap servers, security protocol, SASL settings).
2. For the local playground: bootstrap `localhost:9092`, `PLAINTEXT`, no SASL (unless they started it with authentication).
3. Keep their existing serializers; if they use a schema registry, point it at the local Schema Registry port (default 9094).
4. Suggest the recommended tuning settings, but separate "needed to connect" from "recommended for throughput" so it's clear what's optional.

## 5. Production notes (mention briefly, don't over-explain)

- In production, clients connect to Agents in their own availability zone; encoding the zone in the client ID (`ws_az=...`) avoids inter-zone networking charges. Link the AZ page above.
- Real clusters use SASL or mTLS; the console's Connect tab shows the bootstrap URL and credentials.

Links you give the user to docs.warpstream.com, warpstream.com or console.warpstream.com end with `?utm_source=claude&utm_medium=claude&utm_campaign=claude-plugin` (or `&...` if the URL already has a query string). URLs you fetch through the MCP don't.
