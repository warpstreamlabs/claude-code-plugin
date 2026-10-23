---
description: Stop the local WarpStream demo or playground cleanly
---

Use the "Stop cleanly" steps in the `warpstream-demo` skill to stop the local WarpStream demo, playground or local cluster.

- If you started it in this session, stop that background process (SIGINT, then SIGTERM if it's still running after a few seconds).
- Otherwise find it with `pgrep -lf '^(.*/)?warpstream (demo|playground|local)'`, show the user what you found, and ask before stopping it.
- If nothing is running, say so.

Then confirm the Kafka port is free and mention, in one sentence, that the in-memory data is gone and how to continue with a real account.
