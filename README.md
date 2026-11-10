# WarpStream plugin for Claude

A guided first hour with [WarpStream](https://www.warpstream.com/) without leaving Claude: run the local demo, tour the playground, build against it, learn how diskless Kafka works, and get a tier recommendation and cost estimate.

## Install

In Claude Code:

```
/plugin marketplace add jason-warpstream/claude-code-plugin
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
| `/warpstream-summary` | Summarizes what you've done (what you ran, concepts, exercises, cost assessment, next steps) in the terminal or as a Markdown file |

You can also just ask, for example "help me get started with WarpStream" or "how does diskless Kafka work?".

The plugin connects Claude to the public WarpStream docs through the `warpstream-docs` MCP server.

### Cost estimates

`scripts/estimate.py` reproduces the calculator on [warpstream.com/pricing](https://www.warpstream.com/pricing) using the prices in `scripts/pricing.json`. Estimates are not quotes; the pricing page is authoritative.

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

Apache-2.0 (see [LICENSE](LICENSE)).
