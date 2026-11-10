---
name: warpstream-demo
description: Install the WarpStream CLI and run a local WarpStream cluster with `warpstream demo` (synthetic data flowing) or `warpstream playground` (empty cluster to build against); orient the user, troubleshoot startup problems and stop it cleanly. Use when the user wants to try, run, start, install or stop WarpStream locally, or hits errors starting the demo or playground.
---

# Run WarpStream locally

`warpstream demo` and `warpstream playground` both sign up for a temporary WarpStream account, start local Kafka, Schema Registry and Tableflow Agents, switch on Events, and connect to the hosted WarpStream control plane so the console works. The difference:

- **demo**: also produces and consumes synthetic JSON records on a demo topic, materializes that topic as an Iceberg table with Tableflow, and opens the console and its data directory in the browser. It stores data in a temporary directory on local disk (deleted on exit), so the Iceberg table can be queried locally. Best first look.
- **playground**: an empty cluster with data in memory, best for building against with your own code.

Both are rate-limited, ephemeral and unsuitable for benchmarks. For CI, the docs recommend `warpstream local` instead (no control plane, no account).

## 1. Pre-flight (always, before running anything)

1. Detect the OS and architecture (`uname -sm`). The documented builds are Linux and macOS, amd64 and arm64. On Windows, say that native Windows isn't documented; offer the Docker route, and say WSL may work but isn't confirmed.
2. Check for an existing install: `command -v warpstream || ls ~/.warpstream/warpstream`. If present, run `warpstream version` and skip to step 3.
3. If it isn't installed, explain what will happen and **ask before running anything**:
   - The install script downloads the WarpStream Agent/CLI binary into `~/.warpstream` and prints a line to add to your shell profile:
     `curl https://console.warpstream.com/install.sh | bash`
   - Alternatives if they'd rather not pipe a script to a shell: Homebrew (`brew tap warpstreamlabs/homebrew-tap && brew install warpstreamlabs/homebrew-tap/warpstream`), a direct binary download, or Docker. Look up the current commands with the docs MCP (`getPage` on https://docs.warpstream.com/warpstream/getting-started/install-the-warpstream-agent) rather than guessing.
   - If they decline, don't push. Offer Docker, or point them to the install page and continue with concepts or an assessment.
4. Check the ports are free. Run `warpstream demo -h` (or `playground -h`) to see the port flags and defaults: Kafka (default 9092), Schema Registry (default 9094), and three internal HTTP ports. Check **every** one with `lsof -nP -iTCP:<port> -sTCP:LISTEN` (Linux: `ss -ltnp`); a clash on any of them stops startup. If one is taken (often a local Kafka, Redpanda or an earlier WarpStream run), offer to stop that process (only if the user confirms) or move WarpStream to free ports with the matching override flags.

## 2. Run it

- Ask which mode they want if it isn't clear; default to `demo` for a first look and `playground` when they want to write code.
- In Claude Code, run the command **in the background** (it runs until its timeout or until stopped) and read its output: `warpstream demo` or `warpstream playground`. Add flags only when needed (`-kafkaPort`, `-timeout`). Check `-h` for the default timeout and tell the user when it will stop.
- Without a shell (for example in Claude chat), give the user the exact command to run in their terminal and ask them to paste the output.
- Wait for the startup output, then confirm the cluster is reachable:
  `warpstream kcmd -type diagnose-connection -bootstrap-host localhost -bootstrap-port 9092`

## 3. Orient the user

Always do this once the cluster is up, before moving on (even if the user asked you to stop it straight afterwards). Use what the CLI actually printed (console link, ports, topic name, Tableflow table) rather than assuming. Explain briefly:

- A temporary account was created; the console link in the output logs into it. That link contains a session key: tell the user to open it but not share it. If the printed link starts with `https:/` (one slash), give it with `https://`.
- A Kafka-compatible endpoint is at `localhost:<Kafka port>` (default `localhost:9092`). Any Kafka client or tool can use it as the bootstrap server.
- A Schema Registry (Confluent API-compatible, default port 9094) and a Tableflow cluster run alongside it; `warpstream-tour` covers them.
- Data disappears when the process stops (playground: in memory; demo: a temporary directory that is deleted).
- For demo mode: name the topic the demo produces to (the CLI prints it), show a few records with `warpstream kcmd --type fetch --topic <topic> --offset 0`, and mention that the CLI printed a DuckDB query for the Iceberg table it created (the table becomes queryable after its first snapshot, which can take a few minutes; the CLI says when).

Then offer one next step: the guided tour (`/warpstream-tour`), writing a client (`warpstream-clients`), or the exercises.

## 4. Troubleshoot

| Symptom | What to do |
|---|---|
| `panic: ... listen tcp :<port>: bind: address already in use` | The message names the port. Find its owner (`lsof -nP -iTCP:<port> -sTCP:LISTEN`); stop it if the user agrees, or rerun with that port's override flag from `-h` (and update client settings if it's the Kafka or Schema Registry port) |
| `warpstream: command not found` right after install | The shell profile hasn't been reloaded. Run `~/.warpstream/warpstream` directly or source the profile line the installer printed |
| Corporate machine blocks downloaded binaries or `curl \| bash` | Use Docker; the docs have `docker run` commands and a Docker Compose examples repo (https://github.com/warpstreamlabs/warpstream-docker-compose-example) |
| Client can't connect from inside Docker / to Docker | Follow "Diagnosing Connection Issues" on the docs page "Run the Agents Locally" |
| Signup or control-plane errors | Check outbound HTTPS access to `*.warpstream.com`; corporate proxies are the usual cause. `warpstream local` works offline but has no console |
| Anything else | Search the docs MCP with the exact error message |

## 5. Stop cleanly

When the user is done (or runs `/warpstream-stop`):

1. Stop the demo or playground process you started: stop the background task, or send SIGINT (Ctrl-C). Processes started in the background may ignore SIGINT; if it's still running a few seconds later, send SIGTERM (it shuts down cleanly and deletes its temporary session). If you didn't start it, find it with `pgrep -lf '^(.*/)?warpstream (demo|playground|local)'` (anchored, so it doesn't match the shell that launched it) and confirm with the user before stopping it.
2. Confirm the ports are free again (they free up within seconds of SIGINT).
3. Remind them that in-memory data is gone and the temporary account will expire. If they want to keep going, the next step is a real account: https://console.warpstream.com/signup

## Rules

- Never install software, stop processes you didn't start, or change shell profiles without asking.
