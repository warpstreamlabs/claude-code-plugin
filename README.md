# WarpStream plugin for Claude

A guided first hour with [WarpStream](https://www.warpstream.com/) without leaving Claude: run the local demo, tour the playground, build against it, learn how diskless Kafka works, get a tier recommendation and cost estimate, and deploy your first real cluster in your own cloud.

## Install

In Claude Code:

```
/plugin marketplace add warpstreamlabs/claude-code-plugin
/plugin install warpstream@warpstream
```

To try it from a local clone instead:

```
claude --plugin-dir .
```

## What it does

| Command | What it does |
|---|---|
| `/warpstream-demo` | Checks your machine, installs the WarpStream CLI (with your permission), and runs `warpstream demo` with synthetic data |
| `/warpstream-playground` | Same, but starts an empty cluster with `warpstream playground` |
| `/warpstream-tour` | Walks through what the demo creates: Kafka cluster, Schema Registry, Tableflow, console |
| `/warpstream-assess` | Short fit assessment: tier recommendation, cost estimate and platform comparison, migration outline, exported as Markdown |
| `/warpstream-stop` | Stops the local demo or playground cleanly |
| `/warpstream-deploy` | Guides you from a new account to your first real BYOC cluster in AWS, GCP or Azure: cluster, bucket and permissions, Agents (Helm, Terraform, Docker or ECS), and a first produce and consume |
| `/warpstream-summary` | Summarizes what you've done (what you ran, concepts, exercises, cost assessment, next steps) in the terminal or as a Markdown file |

You can also just ask, for example "help me get started with WarpStream" or "how does diskless Kafka work?".

The plugin connects Claude to the public WarpStream docs through the `warpstream-docs` MCP server.

### Cost estimates

`scripts/estimate.py` reproduces the calculator on [warpstream.com/pricing](https://www.warpstream.com/pricing) using the prices in `scripts/pricing.json`. Estimates are not quotes; the pricing page is authoritative.

## Data and privacy

The plugin doesn't collect, store or send any data about you or your usage. There's no telemetry or analytics.

What does leave your machine, and only when you use the related feature:

- **Docs questions** go to WarpStream's public documentation server (`docs.warpstream.com`) through the `warpstream-docs` MCP server.
- **The local demo and playground** connect to WarpStream's control plane and create a temporary account, as the WarpStream CLI does when you run it yourself. Your records stay on your machine.
- **Deploying a real cluster** uses your WarpStream account and your own cloud account, with your approval for each change.

Cost estimates run locally with `scripts/estimate.py`, and files the plugin writes (assessments, summaries, the `warpstream-playground/` folder) stay in your working directory. Your conversations with Claude are covered by your agreement with Anthropic. WarpStream's privacy policy: https://www.warpstream.com/privacy-policy

## Getting help

Ask questions and share feedback in WarpStream's community Slack: https://console.warpstream.com/socials/slack

## Uninstall and clean up

Remove the plugin in Claude Code:

```
/plugin uninstall warpstream@warpstream
/plugin marketplace remove warpstream
```

The plugin may also have set up the following, depending on what you used. Remove whichever apply:

- **WarpStream CLI**, if you installed it with the install script: delete `~/.warpstream` and remove the line the installer added to your shell profile (`~/.zshrc`, `~/.bashrc` or similar). If you used Homebrew: `brew uninstall warpstream && brew untap warpstreamlabs/homebrew-tap`.
- **Docker image**, if you used Docker: `docker rmi public.ecr.aws/warpstream-labs/warpstream_agent:latest`.
- **Files in your project**: the `warpstream-playground/` folder and any `warpstream-assessment-*.md` or `warpstream-summary-*.md` files.
- **Temporary demo and playground accounts** expire on their own; there's nothing to delete.
- **A real cluster you deployed** keeps running and costing money until you remove it: delete the Agents and bucket with the same tool you created them with, and the cluster in the WarpStream console.

## Development

Run the estimator tests (Python 3.8+, standard library only):

```
python3 -m unittest discover -s tests
```

`tests/fixtures/website_reference.json` holds figures produced by the website's own calculator code. After a pricing change on the website, update `scripts/pricing.json` and regenerate the fixtures (Node 18+):

```
node tests/website_harness.mjs > tests/fixtures/website_reference.json
```

## Changelog

### 0.1.0
- Initial release.

## License

MIT (see [LICENSE](LICENSE)).
