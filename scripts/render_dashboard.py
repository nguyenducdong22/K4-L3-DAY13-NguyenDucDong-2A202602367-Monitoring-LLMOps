"""Ve dashboard 6 panel tu data/logs.jsonl theo config/dashboard.yaml.

Can matplotlib + pyyaml (khong nam trong requirements.txt; cai vao venv rieng):
    python scripts/render_dashboard.py [--out submission/evidence/11-dashboard-overview.png]
Timestamp `ts` trong log la UTC.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml

ROOT = Path(__file__).resolve().parents[1]


def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(q / 100 * (len(ordered) - 1))))]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="submission/evidence/11-dashboard-overview.png")
    args = parser.parse_args()

    cfg = yaml.safe_load((ROOT / "config/dashboard.yaml").read_text(encoding="utf-8"))["dashboard"]
    panels = {p["id"]: p for p in cfg["panels"]}
    rows = [json.loads(l) for l in (ROOT / "data/logs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        r["_t"] = datetime.fromisoformat(r["ts"].replace("Z", "+00:00"))
    end = max(r["_t"] for r in rows)
    start = end - timedelta(minutes=cfg["time_range_minutes"])
    rows = [r for r in rows if r["_t"] >= start]
    sent = [r for r in rows if r["event"] == "response_sent"]

    def per_min(items, value=lambda r: 1, agg=sum):
        buckets = defaultdict(list)
        for r in items:
            buckets[r["_t"].replace(second=0, microsecond=0)].append(value(r))
        xs = sorted(buckets)
        return xs, [agg(buckets[x]) for x in xs]

    def thr(ax, panel):
        t = panel["threshold"]
        ax.axhline(t["value"], color="#e45756", ls="--", lw=1.2)
        ax.text(0.99, 0.94, f"threshold {t['aggregation']} {t['operator']} {t['value']}", transform=ax.transAxes,
                ha="right", va="top", fontsize=7, color="#e45756")

    fig, axs = plt.subplots(2, 3, figsize=(16, 8.2))
    fig.suptitle(f"{cfg['title']}  |  range {cfg['time_range_minutes']} min  |  refresh {cfg['refresh_seconds']}s  |  UTC "
                 f"{start:%H:%M}-{end:%H:%M}  |  {len(sent)} response_sent", fontsize=11)

    ax = axs[0][0]; p = panels["latency"]
    xs = [r["_t"] for r in sent]; lat = [r["latency_ms"] for r in sent]
    ax.plot(xs, lat, "o-", ms=3, lw=0.8, color="#4c78a8", label="latency_ms")
    ax.plot(xs, [r["ttft_ms"] for r in sent], "s-", ms=3, lw=0.8, color="#54a24b", label="ttft_ms")
    ax.set_title(p["title"] + f"  (P50 {pct(lat,50):.0f} / P95 {pct(lat,95):.0f} / P99 {pct(lat,99):.0f} ms, TTFT P95 {pct([r['ttft_ms'] for r in sent],95):.0f} ms)", fontsize=8)
    ax.set_ylabel("ms"); thr(ax, p); ax.legend(fontsize=7, loc="upper left")

    ax = axs[0][1]; p = panels["traffic"]
    xs, ys = per_min([r for r in rows if r["event"] == "request_received"])
    ax.bar(xs, ys, width=0.0006, color="#4c78a8"); ax.set_title(p["title"] + f"  (total {sum(ys)})", fontsize=8)
    ax.set_ylabel("requests / minute"); thr(ax, p)

    ax = axs[0][2]; p = panels["errors"]
    recv = sum(r["event"] == "request_received" for r in rows); fail = sum(r["event"] == "request_failed" for r in rows)
    tools = [r for r in rows if r.get("tool_success") is not None]
    ok = sum(bool(r["tool_success"]) for r in tools) / max(1, len(tools)) * 100
    err = fail / max(1, recv) * 100
    ax.bar(["error rate %", "retrieval success %"], [err, ok], color=["#e45756", "#54a24b"])
    ax.set_ylim(0, 110); ax.set_ylabel("percent")
    ax.set_title(p["title"] + f"  (error {err:.1f}%, retrieval success {ok:.1f}%)", fontsize=8); thr(ax, p)

    ax = axs[1][0]; p = panels["cost"]
    xs, ys = per_min(sent, lambda r: r["cost_usd"])
    ax.bar(xs, ys, width=0.0006, color="#f58518"); ax.set_ylabel("usd / minute")
    total = sum(r["cost_usd"] for r in sent)
    ax.set_title(p["title"] + f"  (total ${total:.4f})", fontsize=8)
    ax.text(0.99, 0.94, f"threshold total lte {p['threshold']['value']} USD (total ${total:.4f}, nam duoi nguong nen khong ve duong)", transform=ax.transAxes,
            ha="right", va="top", fontsize=7, color="#e45756")

    ax = axs[1][1]; p = panels["tokens"]
    xs, tin = per_min(sent, lambda r: r["tokens_in"]); _, tout = per_min(sent, lambda r: r["tokens_out"])
    ax.bar(xs, tin, width=0.0006, label="tokens_in", color="#4c78a8"); ax.bar(xs, tout, width=0.0006, bottom=tin, label="tokens_out", color="#e45756")
    ax.set_ylabel("tokens / minute"); ax.legend(fontsize=7, loc="upper left")
    ax.set_title(p["title"] + f"  (sum in {sum(tin)}, out {sum(tout)})", fontsize=8)
    ax.text(0.99, 0.94, f"threshold sum lte {p['threshold']['value']} (tong {sum(tin)+sum(tout)})", transform=ax.transAxes,
            ha="right", va="top", fontsize=7, color="#e45756")

    ax = axs[1][2]; p = panels["quality"]
    q = [r["quality_score"] for r in sent]
    ax.plot([r["_t"] for r in sent], q, "o-", ms=3, lw=0.8, color="#54a24b"); ax.set_ylim(0, 1.05)
    ax.set_ylabel("score (0-1)"); ax.set_title(p["title"] + f"  (mean {sum(q)/len(q):.2f})", fontsize=8); thr(ax, p)

    for a in axs.flat:
        a.tick_params(axis="x", labelrotation=30, labelsize=7); a.tick_params(axis="y", labelsize=7); a.grid(alpha=0.25)
    plt.tight_layout(rect=(0, 0, 1, 0.96))
    out = ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=110)
    print("saved", out)


if __name__ == "__main__":
    main()
