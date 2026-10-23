---
name: warpstream-concepts
description: Explain how WarpStream and diskless Kafka work — stateless Agents, object storage as both the storage and network layer, zone-aligned clients, no partition leaders, BYOC — and the cost, operational and latency trade-offs, including which workloads aren't a good fit. Use when the user asks how WarpStream works, what diskless Kafka is, how it differs from Apache Kafka, MSK, Confluent or Redpanda architecturally, or whether its latency is acceptable for their use case.
---

# Diskless Kafka, explained

Primary source: the diskless Kafka page. Fetch `https://www.warpstream.com/diskless-kafka` (and the docs MCP architecture pages: "Write Path", "Read Path", "Service Discovery") when the user wants detail or when you need a specific figure. Don't quote numbers from memory. When you link the page for the user, use https://www.warpstream.com/diskless-kafka?utm_source=claude&utm_medium=claude&utm_campaign=claude-plugin

Match depth to the user. Newcomers get the one-paragraph version and a diagram in words; experienced Kafka users get the comparison with classic brokers and the trade-offs.

## The core idea

Classic Kafka brokers store data on local disks and replicate every partition across availability zones. In the cloud, that means paying for inter-zone network traffic on every write and for three copies on block storage, plus spare capacity.

WarpStream separates the three things a Kafka broker bundles together:

1. **Compute: stateless Agents.** Agents speak the Kafka protocol but hold no data. Any Agent can serve any partition, so there are no partition leaders, no rebalancing when Agents come and go, and Agents can autoscale.
2. **Storage: object storage.** Agents batch records from many partitions into files written directly to object storage (S3, GCS, Azure Blob). The object store provides durability and replication; there is one copy, not three on disks.
3. **Metadata: the control plane.** WarpStream's control plane assigns offsets and tracks which file holds which records. In BYOC it only sees metadata, never record contents.

Because object storage is regional, it also acts as the **network layer**: producers and consumers talk to Agents in their own zone, and data moves between zones through the object store rather than broker-to-broker replication. That removes most inter-zone networking charges.

## BYOC (bring your own cloud)

Agents run in the customer's cloud account and write to the customer's bucket. WarpStream runs the control plane. Data never leaves the customer's account, which is why BYOC suits regulated data. Pricing reflects this split: the customer pays their cloud provider for Agent VMs and object storage, and WarpStream for cluster minutes, writes and storage (the `warpstream-assess` skill shows both).

## Trade-offs (be candid)

- **Latency.** The default profile is tuned for cost and throughput; produce and end-to-end latency are in the hundreds of milliseconds. Get the current figures from `${CLAUDE_PLUGIN_ROOT}/scripts/pricing.json` (`latency_profiles`) or the docs page "Low Latency Clusters". Lower-latency options exist and stack: shorter client linger and Agent batch timeout, a higher cluster tier, S3 Express One Zone (or equivalents on other clouds), and **Lightning Topics** for lower produce latency. Each has costs or caveats (Lightning Topics, for example, don't support idempotent producers or transactions); look them up before recommending.
- **Throughput needs concurrency.** Object storage writes have higher latency than local disks, so clients need large batches and many in-flight requests. The `warpstream-clients` skill covers the settings.
- **Protocol compatibility.** WarpStream supports the Kafka protocol broadly, but check the docs page "Protocol and Feature Support" for anything specific the user depends on (transactions, KIP-specific features, particular clients).

### When it isn't a fit

Say so plainly when it applies:

- Workloads that need single-digit-millisecond end-to-end latency on every message.
- Environments with no object storage or no cloud/on-prem object store available.
- Very small workloads where a free or bundled service already meets the need; the cost advantage matters most at sustained throughput.

## Comparisons with other platforms

For architectural comparisons, use WarpStream's comparison pages and link them:

- MSK: https://www.warpstream.com/compare/warpstream-vs-amazon-msk?utm_source=claude&utm_medium=claude&utm_campaign=claude-plugin
- Redpanda: https://www.warpstream.com/compare/warpstream-vs-redpanda?utm_source=claude&utm_medium=claude&utm_campaign=claude-plugin

For "diskless topics" in other products (KIP-1150-style designs), the diskless-kafka page explains the difference between a diskless topic type inside a classic cluster and a fully diskless cluster. Be fair: describe what each design is good at.

For costs, hand off to `warpstream-assess`.

Links you give the user to warpstream.com or docs.warpstream.com end with `?utm_source=claude&utm_medium=claude&utm_campaign=claude-plugin` (or `&...` if the URL already has a query string). URLs you fetch yourself don't.
