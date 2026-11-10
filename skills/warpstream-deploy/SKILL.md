---
name: warpstream-deploy
description: Guide a user from a new WarpStream account to their first real BYOC cluster in their own cloud (AWS, GCP or Azure) — create the cluster in the console, set up the object storage bucket and permissions, deploy the Agents with Helm, Terraform, Docker or ECS, and verify produce and consume. Use when the user has signed up (or is about to) and wants to run WarpStream for real, deploy Agents, set up a bucket for WarpStream, or move from the playground to their own cloud.
---

# Deploy a first real WarpStream cluster (BYOC)

In BYOC, the WarpStream **Agents** run in the user's cloud account and write to the user's own object storage bucket; WarpStream runs the control plane, which only sees metadata. This skill walks through the first cluster. Look up every command, flag, policy and region with the `warpstream-docs` MCP as you go; deployment details change, so don't write them from memory. The pages to start from:

- "Deploy the Agents": https://docs.warpstream.com/warpstream/agent-setup/deploy (required arguments, supported control-plane regions, ports, instance sizing, auto-scaling)
- "Object Storage Configuration": https://docs.warpstream.com/warpstream/agent-setup/different-object-stores (bucket URL format, bucket settings, permissions)
- "Infrastructure as Code": https://docs.warpstream.com/warpstream/agent-setup/infrastructure-as-code (Terraform provider, Helm chart)

## Ground rules

- **Real resources cost money.** Say so before creating anything, and offer a cost estimate with the `warpstream-assess` skill if they haven't had one.
- **Never change their cloud without asking.** Prefer writing files the user reviews (Terraform, Helm values, IAM policies). Before any command that creates or changes resources (`terraform apply`, `helm install`, `aws`, `gcloud`, `az`, `kubectl apply`), show what it will do and ask. Run read-only checks freely.
- **Keep secrets out of the chat and out of files.** The Agent key is a secret. Ask the user to put it in their secret store (Kubernetes Secret, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault) or an environment variable themselves; reference it by name in the files you write. Never ask them to paste it into the conversation, and never commit it.

## 1. Gather what you need

Ask only what isn't already known (the assessment or summary may have answered some):

1. **Cloud and region** where their applications run: AWS, GCP or Azure.
2. **How they run containers**: Kubernetes (use the Helm chart), ECS, plain VMs, or something else.
3. **Infrastructure as code**: Terraform, other, or none (console and CLI).
4. **Tier**: from their assessment if they had one; otherwise ask about production needs and use the tier guidance in the `warpstream-assess` skill.

## 2. Create the cluster

1. If they don't have an account yet: https://console.warpstream.com/signup
2. In the console (or with the Terraform provider), create a **BYOC** Kafka cluster. Choose the control-plane region closest to their infrastructure from the supported list on the "Deploy the Agents" page, and the tier from step 1.
3. From the console, they'll need three values for the Agents: the **virtual cluster ID**, the **region**, and an **Agent key**. The ID and region aren't secret; the key is (see Ground rules).

## 3. Object storage bucket

1. Create a **dedicated** bucket in the same cloud and region as the Agents.
2. Apply the bucket settings and lifecycle guidance from "Object Storage Configuration".
3. Give the Agents' identity (IAM role, service account or managed identity) the bucket permissions listed there, and nothing broader. For Kubernetes, use workload identity as the docs describe rather than static keys.
4. Build the `bucketURL` in the format that page gives for their object store.

Write these as Terraform (or a policy file plus CLI commands) for the user to review and apply.

## 4. Deploy the Agents

The Agent needs four values (flags or environment variables, per "Deploy the Agents"): bucket URL, Agent key, default virtual cluster ID and region.

- **Kubernetes**: use the official Helm chart (https://github.com/warpstreamlabs/charts/tree/main/charts/warpstream-agent). Write a `values.yaml` that references the Agent key from a Secret.
- **ECS, VMs or other container platforms**: run the official image with the `agent` subcommand and the four values as environment variables.
- **Terraform**: the WarpStream Terraform provider can manage the cluster itself; the Agents are deployed with their usual tooling.

Follow the docs for the rest: spread Agents across availability zones, size instances using "Instance Selection", allow the Kafka and HTTP ports and outbound access to the control-plane URL for their region, and set up auto-scaling.

## 5. Verify

1. In the console, confirm the Agents appear and are healthy, and check Diagnostics.
2. From a machine that can reach the Agents, run `warpstream kcmd -type diagnose-connection` against the cluster's bootstrap address (the console's Connect tab shows it), and fix anything it reports.
3. Produce and consume with the `warpstream-clients` skill, pointed at the real bootstrap URL. Mention zone-aware client IDs (`ws_az`) to avoid inter-zone networking charges.

## 6. Before production

Point them to the docs for what to add next, and offer to help with any of it:

- Authentication (SASL or mTLS) and ACLs.
- Monitoring: the Agents' Prometheus metrics or the Datadog integration, plus Diagnostics alerts.
- Migration: Orbit and Schema Linking (the `warpstream-assess` skill has the outline).
- Help: WarpStream's community Slack, https://console.warpstream.com/socials/slack

## Progress log

**Progress log:** if `warpstream-playground/PROGRESS.md` exists in the working directory, or a demo or playground was started in this session, add a line under its `## Log` heading: `- <YYYY-MM-DD HH:MM> — <Area>: <what> — <one-line takeaway or result>`. If the file doesn't exist yet, create it with the headings `# WarpStream progress`, `## Exercises`, `## Manual console steps to redo after a restart` and `## Log`. Don't create it just for a one-off question. `warpstream-summary` reads this log.

Log: each deployment step completed (cluster created, bucket set up, Agents deployed, first produce and consume), with the cloud, region and deployment method. Never log secrets.
