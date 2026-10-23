#!/usr/bin/env python3
"""Estimate the monthly cost of a WarpStream BYOC cluster and compare it with
other streaming platforms.

Reproduces the calculator on https://www.warpstream.com/pricing using the
prices and assumptions in pricing.json (next to this script). Standard library
only; Python 3.8+.

Examples:
  python3 estimate.py --write-mibs 10 --retention-days 7 --tier fundamentals
  python3 estimate.py --write-mibs 500 --partitions 16384 --tier fundamentals \
      --compare kafka-3-az,kafka-msk --format json
  python3 estimate.py --write-mibs 100 --format html --output report.html
"""

import argparse
import html
import json
import math
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PRICING = os.path.join(HERE, "pricing.json")
SECONDS_PER_DAY = 60 * 60 * 24
PRICED_TIERS = ("dev", "fundamentals", "pro")


def load_pricing(path=DEFAULT_PRICING):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def round_half_up(x):
    """Round to whole dollars the way the website displays them."""
    return math.floor(x + 0.5)


def tiered_cost(quantity, tiers, price_key):
    """Charge `quantity` across consecutive bands; a band of None is the remainder."""
    remaining = quantity
    cost = 0.0
    for tier in tiers:
        if remaining <= 0:
            break
        take = remaining if tier["band_gib"] is None else min(tier["band_gib"], remaining)
        cost += take * tier[price_key]
        remaining -= take
    return cost


def pick_instance(instances, required_cores, headroom):
    """Smallest instance whose cores * headroom exceed the requirement, else the largest."""
    chosen = instances[0]
    for instance in instances:
        chosen = instance
        if required_cores < instance["cores"] * headroom:
            break
    return chosen


def validate_inputs(write_mibs, retention_days, partitions, tier):
    if write_mibs <= 0:
        raise ValueError("write throughput must be greater than 0 MiB/s")
    if retention_days < 1:
        raise ValueError("retention must be at least 1 day")
    if partitions < 1:
        raise ValueError("partitions must be at least 1")
    if tier == "enterprise":
        raise ValueError("Enterprise pricing isn't published; contact WarpStream sales for a quote")
    if tier not in PRICED_TIERS:
        raise ValueError("tier must be one of: " + ", ".join(PRICED_TIERS))


def estimate(
    write_mibs=100,
    retention_days=7,
    partitions=4096,
    tier="dev",
    low_latency=False,
    fetch_from_follower=False,
    tiered_storage=False,
    compare=None,
    schema_registry=False,
    tableflow_mibs=0,
    tableflow_retention_days=None,
    pricing=None,
):
    """Return a dict describing the WarpStream estimate and each comparison."""
    pricing = pricing or load_pricing()
    validate_inputs(write_mibs, retention_days, partitions, tier)
    m = pricing["model"]
    aws = pricing["aws"]
    ws = pricing["warpstream"]
    days = m["days_per_month"]
    ratio = m["compression_ratio"]
    fanout = m["consumer_fanout"]
    headroom = m["instance_headroom_factor"]
    zones = m["warpstream_agent_zones"]
    notes = []

    # Partitions: the calculator requires at least one partition per 10 MiB/s
    # of compressed writes, rounded up to a multiple of 4,096.
    requested_partitions = partitions
    required = write_mibs / ratio * m["partitions_per_compressed_mibs"]
    if required > partitions:
        step = m["partition_rounding"]
        partitions = max(step, math.ceil(required / step) * step)
        notes.append(
            "Partitions raised from {:,} to {:,}: the model needs at least one partition "
            "per 10 MiB/s of compressed writes.".format(requested_partitions, partitions)
        )
    tier_info = ws["tiers"][tier]
    if partitions > tier_info["default_max_partitions"]:
        notes.append(
            "{:,} partitions is above the {} default limit of {:,}. Limits can be raised on request, "
            "or a higher tier includes more.".format(
                partitions, tier_info["label"], tier_info["default_max_partitions"]
            )
        )
    if low_latency and tier == "dev":
        notes.append("The pricing page lists Lower Latency from the Fundamentals tier up.")

    # Volumes.
    gib_written_month = (write_mibs * SECONDS_PER_DAY * days) / 1024
    compressed_gib_written_month = gib_written_month / ratio
    gib_per_day = write_mibs * SECONDS_PER_DAY / 1024
    gib_at_rest = gib_per_day * retention_days
    compressed_gib_per_day = gib_per_day / ratio
    compressed_gib_at_rest = compressed_gib_per_day * retention_days

    # WarpStream data plane (runs in the customer's cloud account).
    required_cores = write_mibs / ratio / m["compressed_mibs_per_core"]
    agent = pick_instance(aws["warpstream_agent_instances"], required_cores, headroom)
    num_agents = math.floor(max(required_cores / agent["cores"], m["warpstream_min_agents"]))
    agents_cost = math.floor(num_agents * agent["hourly_price"] * 24 * days)

    flushes = m["agent_flushes_per_second"]["low_latency" if low_latency else "regular"]
    puts_by_time = SECONDS_PER_DAY * days * flushes * num_agents
    mib_per_put = m["uncompressed_mib_per_put"]["at_or_above_500_mibs" if write_mibs >= 500 else "below_500_mibs"]
    puts_by_volume = (write_mibs * SECONDS_PER_DAY * days) / mib_per_put
    puts = max(puts_by_time, puts_by_volume)
    gets = puts * zones
    put_price = aws["s3"]["put_per_request"]
    compaction_put_price = put_price
    get_price = aws["s3"]["get_per_request"]
    if low_latency:
        put_price = aws["s3_express"]["put_per_request"]
        get_price = aws["s3_express"]["get_per_request"]
    put_cost = put_price * puts + m["compaction_put_ratio"] * compaction_put_price * puts
    get_cost = get_price * gets + m["compaction_get_ratio"] * get_price * gets
    object_api_cost = math.floor(put_cost + get_cost)

    s3_express_bandwidth = 0.0
    if low_latency:
        express = aws["s3_express"]
        compressed_written = (write_mibs * SECONDS_PER_DAY * days) / ratio / 1024
        s3_express_bandwidth = compressed_written * 2 * express["upload_per_gib"] + (
            compressed_written * (zones + 1) * express["retrieval_per_gib"]
        )

    object_storage_cost = math.floor(compressed_gib_at_rest * aws["s3"]["storage_per_gib_month"])
    data_plane_total = agents_cost + object_api_cost + s3_express_bandwidth + object_storage_cost

    # WarpStream control plane (billed by WarpStream).
    cluster_cost = tier_info["monthly_cluster_price"]
    writes_cost = math.floor(tiered_cost(gib_written_month, ws["kafka"]["write_tiers"], "price_per_gib"))
    ws_storage_cost = math.floor(tiered_cost(gib_at_rest, ws["kafka"]["storage_tiers"], "price_per_gib_month"))
    control_plane_total = cluster_cost + writes_cost + ws_storage_cost
    warpstream_total = (
        cluster_cost + agents_cost + object_api_cost + s3_express_bandwidth
        + object_storage_cost + writes_cost + ws_storage_cost
    )

    warpstream = {
        "tier": tier,
        "tier_label": tier_info["label"],
        "total": warpstream_total,
        "data_plane": {
            "agents": {"count": num_agents, "instance_type": agent["instance_type"], "cost": agents_cost},
            "object_storage_api": object_api_cost,
            "object_storage": {"compressed_gib": compressed_gib_at_rest, "cost": object_storage_cost},
            "s3_express_bandwidth": s3_express_bandwidth,
            "total": data_plane_total,
        },
        "control_plane": {
            "cluster_minutes": cluster_cost,
            "writes": {"uncompressed_gib": gib_written_month, "cost": writes_cost},
            "storage": {"uncompressed_gib": gib_at_rest, "cost": ws_storage_cost},
            "total": control_plane_total,
        },
    }

    ctx = {
        "write_mibs": write_mibs,
        "retention_days": retention_days,
        "partitions": partitions,
        "fetch_from_follower": fetch_from_follower,
        "tiered_storage": tiered_storage,
        "num_agents": num_agents,
        "required_cores": required_cores,
        "gib_written_month": gib_written_month,
        "compressed_gib_written_month": compressed_gib_written_month,
        "gib_at_rest": gib_at_rest,
        "compressed_gib_per_day": compressed_gib_per_day,
        "compressed_gib_at_rest": compressed_gib_at_rest,
    }
    ids = compare if compare is not None else pricing["comparison_order"]
    comparisons = []
    for cid in ids:
        if cid not in pricing["comparisons"]:
            raise ValueError("unknown comparison: " + cid)
        spec = pricing["comparisons"][cid]
        if spec["kind"] == "no-public-pricing":
            comparisons.append({"id": cid, "label": spec["label"], "total": None, "note": spec["note"],
                                "compare_url": spec.get("compare_url"), "last_verified": spec["last_verified"]})
            continue
        result = _compare(cid, spec, pricing, ctx)
        savings = result["total"] - warpstream_total
        result["savings_percent"] = math.floor(savings / result["total"] * 100) if result["total"] > 0 else 0
        result["last_verified"] = spec["last_verified"]
        result["source_url"] = spec["source_url"]
        comparisons.append(result)

    extras = _extras(tier_info, ws, schema_registry, tableflow_mibs, tableflow_retention_days or retention_days, days)

    profile = pricing["latency_profiles"]["low_latency" if low_latency else "regular"]
    return {
        "inputs": {
            "write_mibs": write_mibs,
            "retention_days": retention_days,
            "partitions": requested_partitions,
            "partitions_used": partitions,
            "tier": tier,
            "low_latency": low_latency,
            "fetch_from_follower": fetch_from_follower,
            "tiered_storage": tiered_storage,
            "schema_registry": schema_registry,
            "tableflow_mibs": tableflow_mibs,
        },
        "warpstream": warpstream,
        "comparisons": comparisons,
        "extras": extras,
        "latency_ms": profile,
        "notes": notes,
        "assumptions": m["assumptions"],
        "last_verified": ws["last_verified"],
        "pricing_page_url": pricing["pricing_page_url"],
        "disclaimer": pricing["disclaimer"],
        "generated": date.today().isoformat(),
    }


def _compare(cid, spec, pricing, c):
    if spec["kind"] == "brokers":
        return _brokers(cid, spec, pricing, c)
    if spec["kind"] == "msk-serverless":
        return _msk_serverless(cid, spec, pricing, c)
    if spec["kind"] == "kinesis":
        return _kinesis(cid, spec, pricing, c)
    raise ValueError("unsupported comparison kind: " + spec["kind"])


def _brokers(cid, spec, pricing, c):
    m = pricing["model"]
    aws = pricing["aws"]
    days = m["days_per_month"]
    fanout = m["consumer_fanout"]
    zones = m["warpstream_agent_zones"]
    rf = m["kafka_replication_factor"]
    is_express = cid == "kafka-msk-express"
    is_gcp = cid == "gcp-msk"
    notes = []

    tiered = spec.get("requires_tiered_storage", False) or (c["tiered_storage"] and spec["supports_tiered_storage"])
    if c["tiered_storage"] and not spec["supports_tiered_storage"]:
        notes.append("Tiered storage isn't modelled for " + spec["label"] + ".")
    if spec.get("requires_tiered_storage") and not c["tiered_storage"]:
        notes.append(spec["label"] + " always tiers storage.")

    # Hot (local) vs tiered storage.
    compressed_hot = c["compressed_gib_at_rest"]
    compressed_tiered = 0.0
    retention_hours = c["retention_days"] * 24
    hot_hours = max(m["kafka_tiered_hot_retention_min_hours"],
                    round_half_up(retention_hours * m["kafka_tiered_hot_retention_fraction"]))
    if tiered and retention_hours > hot_hours:
        per_hour = c["compressed_gib_per_day"] / 24
        compressed_hot = per_hour * hot_hours
        compressed_tiered = per_hour * (retention_hours - hot_hours)

    brokers = spec["brokers"] if "brokers" in spec else pricing["comparisons"][spec["brokers_from"]]["brokers"]
    if is_gcp:
        broker = brokers[0]
    else:
        broker = pick_instance(brokers, c["required_cores"], m["instance_headroom_factor"])

    # Broker count: start from the CPU requirement and take the largest of the limits.
    count = c["num_agents"]
    limit = "CPU"
    local_gib = compressed_hot * m["kafka_ebs_overprovision_factor"] * rf
    if is_express:
        local_gib = c["compressed_gib_at_rest"]
    if not is_express and not is_gcp:
        for_storage = math.floor(local_gib / 1024 / (m["kafka_max_ebs_gib_per_broker"] / 1024))
        if for_storage > count:
            count, limit = for_storage, "storage"

    compressed_mibs = c["write_mibs"] / m["compression_ratio"]
    network_fanout = fanout
    if is_express or (tiered and compressed_tiered > 0):
        network_fanout = fanout + (zones if c["fetch_from_follower"] else 1)
    network_needed = (compressed_mibs * rf + compressed_mibs * network_fanout) * m["kafka_network_headroom_factor"]
    per_core = m["msk_express_network_mibs_per_core"] if is_express else m["kafka_network_mibs_per_core"]
    for_network = math.ceil(network_needed / (per_core * broker["cores"]))
    if for_network > count:
        count, limit = for_network, "networking"

    for_partitions = math.ceil(c["partitions"] * rf / broker["max_replicated_partitions"])
    if for_partitions > count:
        count, limit = for_partitions, "partitions"

    repl_zones = spec["replication_zones"]
    if repl_zones > 1:
        count = math.ceil(count / repl_zones) * repl_zones

    brokers_cost = math.floor(count * 24 * days * broker["hourly_price"])

    inter_zone = spec.get("inter_zone_per_gib", aws["inter_zone_per_gib"])
    produce_cross = (inter_zone * 2) / 3
    consume_cross = produce_cross
    if spec.get("single_zone_producers"):
        produce_cross = 0
    replication_cross = inter_zone * (repl_zones - 1)
    network_cost = c["compressed_gib_written_month"] * (produce_cross + replication_cross)
    if not c["fetch_from_follower"]:
        network_cost += consume_cross * fanout * c["compressed_gib_written_month"]
    network_cost = math.floor(network_cost)

    local_price = spec.get("local_storage_per_gib_month", aws["ebs_per_gib_month"])
    if is_gcp:
        # GCP bills a fixed amount of local storage per vCPU; everything else is tiered.
        local_gib = count * broker["cores"] * spec["local_storage_gib_per_core"]
        compressed_tiered = max(0.0, c["compressed_gib_at_rest"] - local_gib)
    local_cost = math.floor(local_gib * local_price)
    tiered_price = spec.get("tiered_storage_per_gib_month", aws["s3"]["storage_per_gib_month"])
    tiered_cost_ = math.floor(compressed_tiered * tiered_price)

    data_in_cost = 0.0
    if is_express:
        data_in_cost = c["write_mibs"] / m["compression_ratio"] / 1024 * SECONDS_PER_DAY * days * spec["data_in_per_compressed_gib"]

    total = math.floor(brokers_cost + network_cost + local_cost + tiered_cost_ + data_in_cost)
    if c["fetch_from_follower"]:
        notes.append(spec["fetch_from_follower_label"] + " enabled.")

    breakdown = [
        ("Brokers ({} x {})".format(count, broker["instance_type"]), brokers_cost),
        ("Inter-zone networking", network_cost),
        ("Local storage ({:,.0f} GiB)".format(local_gib), local_cost),
    ]
    if compressed_tiered > 0 or tiered:
        breakdown.append(("Tiered storage ({:,.0f} GiB)".format(compressed_tiered), tiered_cost_))
    if is_express:
        breakdown.append(("Data in", data_in_cost))
    return {
        "id": cid,
        "label": spec["label"],
        "description": spec["description"],
        "total": total,
        "brokers": {"count": count, "instance_type": broker["instance_type"], "limited_by": limit},
        "costs": {"brokers": brokers_cost, "inter_zone": network_cost, "local_storage": local_cost,
                  "tiered_storage": tiered_cost_, "data_in": data_in_cost},
        "breakdown": [{"item": k, "cost": v} for k, v in breakdown],
        "notes": notes,
    }


def _msk_serverless(cid, spec, pricing, c):
    days = pricing["model"]["days_per_month"]
    fanout = pricing["model"]["consumer_fanout"]
    costs = {
        "cluster_hours": spec["cluster_hourly"] * 24 * days,
        "partition_hours": spec["partition_hourly"] * c["partitions"] * 24 * days,
        "write_throughput": c["compressed_gib_written_month"] * spec["write_per_compressed_gib"],
        "read_throughput": c["compressed_gib_written_month"] * spec["read_per_compressed_gib"] * fanout,
        "storage": c["compressed_gib_at_rest"] * spec["storage_per_compressed_gib_month"],
    }
    labels = ["Cluster hours", "Partition hours", "Write throughput", "Read throughput", "Storage"]
    return _serverless_result(cid, spec, costs, labels, [])


def _kinesis(cid, spec, pricing, c):
    days = pricing["model"]["days_per_month"]
    shards = max(c["write_mibs"] * spec["shards_per_uncompressed_mibs"], c["partitions"])
    shard_hours = shards * 24 * days
    put_units = (c["gib_written_month"] * 1024 * 1024) / spec["put_payload_unit_kib"]
    read = spec["enhanced_fanout_per_gib"] * c["gib_written_month"] * spec["enhanced_fanout_consumers"]
    read += spec["enhanced_fanout_shard_hourly"] * shards * 24 * days
    storage = 0.0
    if c["retention_days"] > spec["extended_retention_after_days"]:
        storage += spec["extended_retention_shard_hourly"] * shards * 24 * days
    if c["retention_days"] > spec["long_term_retention_after_days"]:
        storage += spec["long_term_retention_per_gib_month"] * c["gib_at_rest"]
    costs = {
        "cluster_hours": 0,
        "partition_hours": spec["shard_hourly"] * shard_hours,
        "write_throughput": put_units * (spec["put_per_million_units"] / 1000000),
        "read_throughput": read,
        "storage": storage,
    }
    labels = [None, "Shard hours ({:,} shards)".format(int(shards)), "PUT payload units",
              "Enhanced fan-out", "Extended data retention"]
    return _serverless_result(cid, spec, costs, labels, [spec["migration_note"]])


def _serverless_result(cid, spec, costs, labels, notes):
    values = [costs["cluster_hours"], costs["partition_hours"], costs["write_throughput"],
              costs["read_throughput"], costs["storage"]]
    return {
        "id": cid,
        "label": spec["label"],
        "description": spec["description"],
        "total": math.floor(sum(values)),
        "costs": costs,
        "breakdown": [{"item": k, "cost": v} for k, v in zip(labels, values) if k is not None],
        "notes": notes,
    }


def _extras(tier_info, ws, schema_registry, tableflow_mibs, tableflow_retention_days, days):
    """Charges outside the website calculator, from published unit prices."""
    extras = []
    if schema_registry:
        extras.append({
            "item": "Schema Registry cluster ({})".format(tier_info["label"]),
            "cost": tier_info["monthly_cluster_price"],
            "note": ws["schema_registry"]["note"],
        })
    if tableflow_mibs:
        tf = ws["tableflow"]
        written = (tableflow_mibs * SECONDS_PER_DAY * days) / 1024
        at_rest = tableflow_mibs * SECONDS_PER_DAY / 1024 * tableflow_retention_days
        extras.append({
            "item": "Tableflow cluster ({})".format(tier_info["label"]),
            "cost": tier_info["monthly_cluster_price"],
            "note": tf["note"],
        })
        extras.append({
            "item": "Tableflow writes ({:,.0f} uncompressed GiB)".format(written),
            "cost": math.floor(tiered_cost(written, tf["write_tiers"], "price_per_gib")),
            "note": tf["note"],
        })
        extras.append({
            "item": "Tableflow storage ({:,.0f} uncompressed GiB)".format(at_rest),
            "cost": math.floor(tiered_cost(at_rest, tf["storage_tiers"], "price_per_gib_month")),
            "note": tf["note"],
        })
    return extras


# --- Rendering ---------------------------------------------------------------

def dollars(x):
    return "${:,}".format(round_half_up(x))


def _bar(value, maximum, width=30):
    if maximum <= 0:
        return ""
    eighths = int(round(value / maximum * width * 8))
    full, part = divmod(eighths, 8)
    return "█" * full + ("" if part == 0 else " ▏▎▍▌▋▊▉"[part])


def _savings_text(c):
    if c["savings_percent"] >= 0:
        return "WarpStream {}% cheaper".format(c["savings_percent"])
    return "WarpStream {}% more expensive".format(abs(c["savings_percent"]))


def _input_summary(i):
    parts = [
        "{:,} MiB/s uncompressed writes".format(i["write_mibs"]),
        "{} days retention".format(i["retention_days"]),
        "{:,} partitions".format(i["partitions_used"]),
        "{} tier".format(i["tier"].capitalize()),
    ]
    if i["low_latency"]:
        parts.append("low latency")
    if i["fetch_from_follower"]:
        parts.append("Fetch From Follower")
    if i["tiered_storage"]:
        parts.append("tiered storage")
    return ", ".join(parts)


def _bar_scale(totals):
    """Bar maximum; a single outlier more than 5x the next-highest is drawn off the scale."""
    ordered = sorted(totals, reverse=True)
    if len(ordered) > 1 and ordered[1] > 0 and ordered[0] > 5 * ordered[1]:
        return ordered[1]
    return ordered[0]


def render_text(r):
    w = r["warpstream"]
    dp, cp = w["data_plane"], w["control_plane"]

    def row(label, value, indent=0):
        return "{:<38}{:>12}".format(" " * indent + label, dollars(value))

    lines = [
        "WarpStream cost estimate (per month)",
        _input_summary(r["inputs"]),
        "",
        row("WarpStream ({} tier)".format(w["tier_label"]), w["total"]),
        row("Data plane (your cloud account)", dp["total"], 2),
        row("Agents ({} x {})".format(dp["agents"]["count"], dp["agents"]["instance_type"]), dp["agents"]["cost"], 4),
        row("Object storage API calls", dp["object_storage_api"], 4),
        row("Object storage", dp["object_storage"]["cost"], 4),
    ]
    if r["inputs"]["low_latency"]:
        lines.append(row("S3 Express bandwidth", dp["s3_express_bandwidth"], 4))
    lines += [
        row("Control plane (billed by WarpStream)", cp["total"], 2),
        row("Cluster minutes", cp["cluster_minutes"], 4),
        row("Writes", cp["writes"]["cost"], 4),
        row("Storage", cp["storage"]["cost"], 4),
    ]
    priced = [c for c in r["comparisons"] if c["total"] is not None]
    if priced:
        top = _bar_scale([w["total"]] + [c["total"] for c in priced])
        lines += ["", "Comparison"]
        rows = [("WarpStream", w["total"], "")] + [(c["label"], c["total"], _savings_text(c)) for c in priced]
        for label, total, savings in rows:
            bar = _bar(min(total, top), top) + ("▶" if total > top else "")
            lines.append("  {:<15} {:>11}  {:<31} {}".format(label, dollars(total), bar, savings))
    for c in r["comparisons"]:
        if c["total"] is None:
            lines += ["", "{}: {}".format(c["label"], c["note"])]
    if r["extras"]:
        lines += ["", "Not in the website calculator (published unit prices):"]
        for e in r["extras"]:
            lines.append("  {:<45} {:>10}".format(e["item"], dollars(e["cost"])))
    if r["notes"]:
        lines += ["", "Notes:"] + ["  - " + n for n in r["notes"]]
    lines += [
        "",
        "Prices last verified {}. {}".format(r["last_verified"], r["disclaimer"]),
        "Pricing: " + r["pricing_page_url"],
    ]
    return "\n".join(lines)


def render_markdown(r):
    w = r["warpstream"]
    dp, cp = w["data_plane"], w["control_plane"]
    out = [
        "**Inputs:** " + _input_summary(r["inputs"]),
        "",
        "| WarpStream ({} tier) | Monthly |".format(w["tier_label"]),
        "|---|---:|",
        "| Agents ({} x {}) | {} |".format(dp["agents"]["count"], dp["agents"]["instance_type"], dollars(dp["agents"]["cost"])),
        "| Object storage API calls | {} |".format(dollars(dp["object_storage_api"])),
        "| Object storage | {} |".format(dollars(dp["object_storage"]["cost"])),
    ]
    if r["inputs"]["low_latency"]:
        out.append("| S3 Express bandwidth | {} |".format(dollars(dp["s3_express_bandwidth"])))
    out += [
        "| **Data plane (your cloud account)** | **{}** |".format(dollars(dp["total"])),
        "| Cluster minutes | {} |".format(dollars(cp["cluster_minutes"])),
        "| Writes | {} |".format(dollars(cp["writes"]["cost"])),
        "| Storage | {} |".format(dollars(cp["storage"]["cost"])),
        "| **Control plane (billed by WarpStream)** | **{}** |".format(dollars(cp["total"])),
        "| **Total** | **{}** |".format(dollars(w["total"])),
    ]
    priced = [c for c in r["comparisons"] if c["total"] is not None]
    if priced:
        out += ["", "| Platform | Monthly | vs WarpStream |", "|---|---:|---|"]
        for c in priced:
            out.append("| {} | {} | {} |".format(c["description"], dollars(c["total"]), _savings_text(c)))
    for c in r["comparisons"]:
        if c["total"] is None:
            out += ["", "**{}:** {}".format(c["label"], c["note"])]
    if r["extras"]:
        out += ["", "Not in the website calculator (from published unit prices):", ""]
        out += ["- {}: {}".format(e["item"], dollars(e["cost"])) for e in r["extras"]]
    if r["notes"]:
        out += ["", "Notes:", ""] + ["- " + n for n in r["notes"]]
    out += ["", "Assumptions:", ""] + ["- " + a for a in r["assumptions"]]
    out += [
        "",
        "_Prices last verified {}. {} See [warpstream.com/pricing]({})._".format(
            r["last_verified"], r["disclaimer"], r["pricing_page_url"]),
    ]
    return "\n".join(out)


def render_html(r):
    e = html.escape
    w = r["warpstream"]
    dp, cp = w["data_plane"], w["control_plane"]
    priced = [c for c in r["comparisons"] if c["total"] is not None]
    top = _bar_scale([w["total"]] + [c["total"] for c in priced]) or 1

    def row(label, value, cls=""):
        return '<tr class="{}"><td>{}</td><td class="num">{}</td></tr>'.format(cls, e(label), e(dollars(value)))

    ws_rows = [
        row("Agents ({} x {})".format(dp["agents"]["count"], dp["agents"]["instance_type"]), dp["agents"]["cost"]),
        row("Object storage API calls", dp["object_storage_api"]),
        row("Object storage", dp["object_storage"]["cost"]),
    ]
    if r["inputs"]["low_latency"]:
        ws_rows.append(row("S3 Express bandwidth", dp["s3_express_bandwidth"]))
    ws_rows += [
        row("Data plane (your cloud account)", dp["total"], "sub"),
        row("Cluster minutes", cp["cluster_minutes"]),
        row("Writes", cp["writes"]["cost"]),
        row("Storage", cp["storage"]["cost"]),
        row("Control plane (billed by WarpStream)", cp["total"], "sub"),
        row("Total", w["total"], "total"),
    ]
    bars = []
    for label, total, savings, cls in [("WarpStream", w["total"], "", "ws")] + [
        (c["label"], c["total"], _savings_text(c), "") for c in priced
    ]:
        bars.append(
            '<div class="bar-row"><div class="bar-label">{}</div><div class="bar-track">'
            '<div class="bar {}" style="width:{:.1f}%"></div></div><div class="num">{}</div>'
            '<div class="savings">{}</div></div>'.format(
                e(label), cls + (" off-scale" if total > top else ""), min(total, top) / top * 100,
                e(dollars(total)), e(savings + (" (bar not to scale)" if total > top else "")))
        )
    lists = ""
    for title, items in (("Notes", r["notes"]), ("Assumptions", r["assumptions"])):
        if items:
            lists += "<h2>{}</h2><ul>{}</ul>".format(title, "".join("<li>{}</li>".format(e(i)) for i in items))
    extras = ""
    if r["extras"]:
        extras = "<h2>Not in the website calculator</h2><table>{}</table>".format(
            "".join(row(x["item"], x["cost"]) for x in r["extras"]))
    for c in r["comparisons"]:
        if c["total"] is None:
            extras += "<p><strong>{}:</strong> {}</p>".format(e(c["label"]), e(c["note"]))
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>WarpStream cost estimate</title>
<style>
:root {{ --bg:#fff; --fg:#1a1a1a; --muted:#666; --line:#e5e5e5; --bar:#9aa0a6; --ws:#e52a45; --link:#0b57d0; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#141414; --fg:#eee; --muted:#aaa; --line:#333; --bar:#6b7075; --ws:#ff5a70; --link:#8ab4f8; }} }}
body {{ background:var(--bg); color:var(--fg); font:15px/1.5 system-ui, sans-serif; max-width:820px; margin:0 auto; padding:24px 16px; overflow-wrap:anywhere; }}
a {{ color:var(--link); }}
h1 {{ font-size:22px; margin:0 0 4px; }} h2 {{ font-size:17px; margin:28px 0 8px; }}
.muted {{ color:var(--muted); }} table {{ border-collapse:collapse; width:100%; }}
td {{ padding:6px 4px; border-bottom:1px solid var(--line); }} .num {{ text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap; }}
tr.sub td {{ font-weight:600; }} tr.total td {{ font-weight:700; border-top:2px solid var(--fg); }}
.bar-row {{ display:grid; grid-template-columns:120px 1fr 90px; gap:8px; align-items:center; margin:6px 0; }}
.bar-track {{ background:var(--line); height:14px; border-radius:3px; }} .bar {{ background:var(--bar); height:100%; border-radius:3px; }}
.bar.ws {{ background:var(--ws); }} .savings {{ grid-column:2 / 4; color:var(--muted); font-size:13px; margin-top:-4px; }}
@media (max-width:520px) {{ .bar-row {{ grid-template-columns:90px 1fr 80px; }} }}
</style></head><body>
<h1>WarpStream cost estimate</h1>
<p class="muted">{inputs}. Monthly, generated {generated}.</p>
<h2>WarpStream ({tier} tier)</h2><table>{ws_rows}</table>
<h2>Comparison</h2>{bars}
{extras}{lists}
<p class="muted">Prices last verified {verified}. {disclaimer} <a href="{url}">warpstream.com/pricing</a></p>
</body></html>
""".format(
        inputs=e(_input_summary(r["inputs"])), generated=e(r["generated"]), tier=e(w["tier_label"]),
        ws_rows="".join(ws_rows), bars="".join(bars), extras=extras, lists=lists,
        verified=e(r["last_verified"]), disclaimer=e(r["disclaimer"]), url=e(r["pricing_page_url"]),
    )


def main(argv=None):
    p = argparse.ArgumentParser(description="Estimate WarpStream BYOC cost and compare with other platforms.")
    p.add_argument("--write-mibs", type=float, default=100, help="uncompressed write throughput, MiB/s (default 100)")
    p.add_argument("--retention-days", type=int, default=7, help="retention in days (default 7)")
    p.add_argument("--partitions", type=int, default=4096, help="partition count (default 4096)")
    p.add_argument("--tier", default="dev", help="dev, fundamentals or pro (default dev)")
    p.add_argument("--low-latency", action="store_true", help="use the low-latency profile (S3 Express One Zone)")
    p.add_argument("--fetch-from-follower", action="store_true",
                   help="Kafka comparisons use Fetch From Follower (Single Zone Consumers for Kafka 1 AZ)")
    p.add_argument("--tiered-storage", action="store_true", help="Kafka comparisons use tiered storage where supported")
    p.add_argument("--compare", default="all",
                   help="comma-separated comparison ids, 'all' (default) or 'none'. Ids: kafka-3-az, kafka-1-az, "
                        "kafka-msk, kafka-msk-express, kafka-msk-serverless, kafka-kinesis, gcp-msk, redpanda")
    p.add_argument("--schema-registry", action="store_true", help="add a Schema Registry cluster at the same tier")
    p.add_argument("--tableflow-mibs", type=float, default=0, help="add Tableflow for this many uncompressed MiB/s")
    p.add_argument("--tableflow-retention-days", type=int, help="Tableflow retention (default: --retention-days)")
    p.add_argument("--format", choices=["text", "json", "markdown", "html"], default="text")
    p.add_argument("--output", help="write to this file instead of stdout")
    p.add_argument("--pricing", default=DEFAULT_PRICING, help=argparse.SUPPRESS)
    a = p.parse_args(argv)

    write_mibs = int(a.write_mibs) if float(a.write_mibs).is_integer() else a.write_mibs
    compare = []
    pricing = load_pricing(a.pricing)
    for cid in (x.strip() for x in a.compare.split(",")):
        if cid == "all":
            compare += [x for x in pricing["comparison_order"] if x not in compare]
        elif cid and cid != "none" and cid not in compare:
            compare.append(cid)
    try:
        result = estimate(
            write_mibs=write_mibs, retention_days=a.retention_days, partitions=a.partitions,
            tier=a.tier.lower(), low_latency=a.low_latency, fetch_from_follower=a.fetch_from_follower,
            tiered_storage=a.tiered_storage, compare=compare, schema_registry=a.schema_registry,
            tableflow_mibs=a.tableflow_mibs, tableflow_retention_days=a.tableflow_retention_days,
            pricing=pricing,
        )
    except ValueError as err:
        print("error: " + str(err), file=sys.stderr)
        return 2

    renderers = {"text": render_text, "markdown": render_markdown, "html": render_html,
                 "json": lambda r: json.dumps(r, indent=2)}
    output = renderers[a.format](result)
    if a.output:
        with open(a.output, "w", encoding="utf-8") as f:
            f.write(output + "\n")
        print("wrote " + a.output, file=sys.stderr)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
