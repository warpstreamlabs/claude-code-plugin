// Runs the cost calculator embedded in warpstream.com/pricing against a stub
// DOM and records what it displays, so estimate.py can be checked against the
// real website logic.
//
// Usage:
//   node tests/website_harness.mjs [pricing-page.html] > tests/fixtures/website_reference.json
//
// With no argument it downloads https://www.warpstream.com/pricing.

import { readFileSync } from "node:fs";
import vm from "node:vm";

const PRICING_URL = "https://www.warpstream.com/pricing";

async function loadPage(path) {
  if (path) return readFileSync(path, "utf8");
  const res = await fetch(PRICING_URL);
  if (!res.ok) throw new Error(`GET ${PRICING_URL}: ${res.status}`);
  return res.text();
}

function extractCalculatorScript(page) {
  const marker = page.indexOf("kafkaBrokerInstanceTypesByVolume");
  if (marker < 0) throw new Error("calculator script not found in page");
  const start = page.lastIndexOf("<script>", marker) + "<script>".length;
  const end = page.indexOf("</script>", marker);
  return page.slice(start, end);
}

function makeElement() {
  const classes = new Set();
  return {
    value: "",
    checked: false,
    disabled: false,
    innerText: "",
    textContent: "",
    innerHTML: "",
    style: {},
    options: [],
    classList: {
      add: (c) => classes.add(c),
      remove: (c) => classes.delete(c),
      contains: (c) => classes.has(c),
    },
    addEventListener() {},
    appendChild() {},
  };
}

function makeContext() {
  const elements = new Map();
  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, makeElement());
      return elements.get(id);
    },
    getElementsByClassName: () => [],
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: makeElement,
    addEventListener() {},
  };
  const context = vm.createContext({ document, window: { dataLayer: [] }, Intl, Math });
  return { context, text: (id) => document.getElementById(id).innerText, el: (id) => document.getElementById(id) };
}

// Inputs are kept on the calculator's slider grid (partitions in multiples of
// 4,096 or 256, retention >= 1) and partitions within the tier's limit, since
// the website snaps or clamps anything else.
const COMPARISONS = [
  "kafka-3-az",
  "kafka-1-az",
  "kafka-msk",
  "kafka-msk-express",
  "kafka-msk-serverless",
  "kafka-kinesis",
  "gcp-msk",
];

const BASE = {
  write_mibs: 100,
  retention_days: 7,
  partitions: 4096,
  tier: "dev",
  low_latency: false,
  fetch_from_follower: false,
  tiered_storage: false,
};

function scenarios() {
  const out = [];
  for (const write_mibs of [1, 10, 100, 500, 1024, 5120]) out.push({ write_mibs });
  for (const retention_days of [1, 3, 30, 90]) out.push({ retention_days });
  out.push({ partitions: 256 });
  out.push({ partitions: 16384, tier: "fundamentals" });
  out.push({ partitions: 49152, tier: "pro" });
  out.push({ partitions: 49152, tier: "pro", write_mibs: 5120, retention_days: 30 });
  out.push({ tier: "fundamentals" });
  out.push({ tier: "pro" });
  out.push({ low_latency: true });
  out.push({ low_latency: true, write_mibs: 1024 });
  out.push({ fetch_from_follower: true });
  out.push({ fetch_from_follower: true, write_mibs: 500, retention_days: 30 });
  out.push({ tiered_storage: true, retention_days: 30 });
  out.push({ tiered_storage: true, fetch_from_follower: true, retention_days: 90, write_mibs: 500 });
  // PLAN.md §6.1 sanity check.
  out.push({ write_mibs: 10, retention_days: 7, tier: "fundamentals" });
  return out.map((s) => ({ ...BASE, ...s }));
}

const OUTPUT_IDS = [
  "warpstream-cumulative-cost",
  "data-plane-cost",
  "control-plane-cost",
  "num-agents",
  "agent-instance-type",
  "agents-cost",
  "object-storage-api-cost",
  "storage-cost",
  "s3-express-bandwidth-cost-cost",
  "warpstream-cluster-minutes-cost",
  "uncompressed-writes-cost",
  "uncompressed-warpstream-storage-cost",
  "warpstream-savings-percent",
  "kafka-total-cost",
  "num-kafka-brokers",
  "kafka-broker-instance-type",
  "kafka-brokers-cost",
  "kafka-interzone-networking",
  "kafka-ebs-storage-cost",
  "kafka-tiered-storage-cost",
  "kafka-write-throughput-cost",
  "node-count-limiting-factor",
  "serverless-cluster-hours-cost",
  "serverless-partition-hours-cost",
  "serverless-write-throughput-cost",
  "serverless-read-throughput-cost",
  "serverless-storage-cost",
  "serverless-total-cost",
];

function run(script, scenario, comparison) {
  const { context, text, el } = makeContext();
  vm.runInContext(script, context);
  el("write-volume-selector").value = String(scenario.write_mibs);
  el("retention-selector").value = String(scenario.retention_days);
  el("partitions-selector").value = String(scenario.partitions);
  el("cluster-tier-selector").value = scenario.tier;
  context.__state = { ...scenario, comparison };
  vm.runInContext(
    `selectedComparison = comparisonSelectorsForToggle.find(function (c) { return c.name === __state.comparison; });
     s3ExpressEnabled = __state.low_latency;
     isFetchFromFollowerEnabled = __state.fetch_from_follower;
     isTieredStorageEnabled = __state.tiered_storage && selectedComparison.supportsTieredStorage;
     updateView();`,
    context
  );
  const outputs = {};
  for (const id of OUTPUT_IDS) outputs[id] = text(id);
  return outputs;
}

const page = await loadPage(process.argv[2]);
const script = extractCalculatorScript(page);
const cases = [];
for (const scenario of scenarios()) {
  for (const comparison of COMPARISONS) {
    cases.push({ inputs: { ...scenario, comparison }, website: run(script, scenario, comparison) });
  }
}
console.log(
  JSON.stringify(
    {
      source: process.argv[2] ? "local file" : PRICING_URL,
      generated: new Date().toISOString().slice(0, 10),
      cases,
    },
    null,
    1
  )
);
