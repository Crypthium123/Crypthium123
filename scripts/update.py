#!/usr/bin/env python3
"""Regenerates the live parts of the profile README.

- builds a real IPv4/TCP packet (valid checksums, TCP timestamp = now)
- writes it as assets/crypthium.pcap + assets/packet.svg (wireshark-style)
- pulls recent public activity from the GitHub API -> assets/live.svg
Runs daily from .github/workflows/profile.yml
"""
import json, os, re, struct, time, urllib.request
from datetime import datetime, timezone
from theme import *

USER = "Crypthium123"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
PCAP = os.path.join(ROOT, "assets", "crypthium.pcap")
PKT_SVG = os.path.join(ROOT, "assets", "packet.svg")
LIVE_SVG = os.path.join(ROOT, "assets", "live.svg")

PAYLOAD = (b"hi, I'm Crypthium. BUT R&T student, France.\n"
           b"linux / C / python / bash / html+css\n"
           b"break it. fix it. understand it.\n")


# ---------------------------------------------------------------- packet
def csum(data: bytes) -> int:
    if len(data) % 2:
        data += b"\0"
    s = sum(struct.unpack(f"!{len(data)//2}H", data))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return ~s & 0xFFFF


def build_packet(now: int) -> bytes:
    src, dst = bytes([10, 13, 37, 1]), bytes([192, 168, 1, 42])
    sport, dport = 1337, 80
    seq = int.from_bytes(b"VERI", "big") ^ 0x13371337
    ack = int.from_bytes(b"DIAN", "big") ^ 0x13371337
    opts = b"\x01\x01" + struct.pack("!BBII", 8, 10, now & 0xFFFFFFFF, 0)  # NOP NOP TS
    doff = (20 + len(opts)) // 4
    flags = 0x18  # PSH, ACK
    tcp = struct.pack("!HHIIBBHHH", sport, dport, seq, ack, doff << 4, flags, 0xFAF0, 0, 0) + opts + PAYLOAD
    pseudo = src + dst + struct.pack("!BBH", 0, 6, len(tcp))
    tcp = tcp[:16] + struct.pack("!H", csum(pseudo + tcp)) + tcp[18:]
    total = 20 + len(tcp)
    ip = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total, 0x1337, 0x4000, 64, 6, 0, src, dst)
    ip = ip[:10] + struct.pack("!H", csum(ip)) + ip[12:]
    return ip + tcp


def write_pcap(pkt: bytes, now: int):
    hdr = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 101)  # LINKTYPE_RAW
    rec = struct.pack("<IIII", now, 0, len(pkt), len(pkt))
    with open(PCAP, "wb") as f:
        f.write(hdr + rec + pkt)


def hexdump(pkt: bytes) -> str:
    out = []
    for off in range(0, len(pkt), 16):
        chunk = pkt[off:off + 16]
        hx = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"{off:04x}  {hx:<47}  {asc}")
    return "\n".join(out)


# ---------------------------------------------------------------- activity
def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}",
                                 headers={"Accept": "application/vnd.github+json",
                                          "User-Agent": USER})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def ago(ts: str, now: datetime) -> str:
    d = now - datetime.fromisoformat(ts.replace("Z", "+00:00"))
    s = int(d.total_seconds())
    for unit, n in (("d", 86400), ("h", 3600), ("m", 60)):
        if s >= n:
            return f"{s // n}{unit} ago"
    return "just now"


def fetch(now: datetime):
    try:
        user = api(f"/users/{USER}")
        events = api(f"/users/{USER}/events/public?per_page=60")
    except Exception as exc:  # keep the previous card if the API is down
        print("api error:", exc)
        return None
    rows = []
    for ev in events:
        repo = ev["repo"]["name"]
        if repo.startswith(USER + "/"):
            repo = repo.split("/", 1)[1]
        t, p = ev["type"], ev.get("payload", {})
        if t == "PushEvent":
            n = p.get("size", len(p.get("commits", [])))
            row = ("push", GREEN, f"{n} commit{'s' if n != 1 else ''}")
        elif t == "CreateEvent":
            row = ("create", BLUE, p.get("ref_type", ""))
        elif t == "PullRequestEvent":
            row = ("pr", PURPLE, p.get("action", ""))
        elif t == "IssuesEvent":
            row = ("issue", ORANGE, p.get("action", ""))
        elif t == "WatchEvent":
            row = ("star", YELLOW, "starred")
        elif t == "ForkEvent":
            row = ("fork", CYAN, "forked")
        else:
            continue
        rows.append(row + (repo, ago(ev["created_at"], now)))
        if len(rows) == 6:
            break
    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    return {"uptime": (now - created).days, "repos": user["public_repos"],
            "followers": user["followers"], "rows": rows}


# ---------------------------------------------------------------- svg cards
def packet_svg(pkt: bytes, now: datetime) -> str:
    W = 940
    region = lambda i: BLUE if i < 20 else PURPLE if i < 52 else GREEN
    p = []
    p.append(label(24, 34, "crypthium.pcap", FG, 13, weight=700))
    p.append(label(150, 34, f"1 packet · {len(pkt)} bytes · rebuilt {now:%Y-%m-%d %H:%M} UTC", DIM, 12))
    x = 916
    for name, c in (("payload", GREEN), ("tcp", PURPLE), ("ipv4", BLUE)):
        w = len(name) * 7.4 + 18
        x -= w
        p.append(f'<rect x="{x:.1f}" y="21" width="{w:.1f}" height="19" rx="9.5" fill="{c}" fill-opacity=".15" stroke="{c}" stroke-opacity=".5"/>')
        p.append(label(x + w / 2, 34.5, name, c, 11, "middle"))
        x -= 8
    p.append(f'<line x1="24" y1="52" x2="916" y2="52" stroke="{LINE}"/>')
    y0, lh = 78, 19
    rows = (len(pkt) + 15) // 16
    for r in range(rows):
        chunk = pkt[r * 16:(r + 1) * 16]
        segs = [(f"{r*16:04x}  ", DIM)]
        for i, b in enumerate(chunk):
            segs.append((f"{b:02x}" + (" " if i < 15 else ""), region(r * 16 + i)))
        segs.append(("   " * (16 - len(chunk)) + "  ", None))
        for i, b in enumerate(chunk):
            segs.append((chr(b) if 32 <= b < 127 else "·", region(r * 16 + i)))
        segs.append((" " * (16 - len(chunk)), None))
        p.append(f'<text x="24" y="{y0 + r*lh}" font-size="12.5" textLength="540" lengthAdjust="spacing">{runs(segs)}</text>')
    ipck = int.from_bytes(pkt[10:12], "big"); tck = int.from_bytes(pkt[36:38], "big")
    tsval = int.from_bytes(pkt[44:48], "big")
    tree = [("▾ Frame 1", FG, f"{len(pkt)} bytes on wire"),
            ("▾ Internet Protocol Version 4", BLUE, ""),
            ("    10.13.37.1 → 192.168.1.42", FG, ""),
            ("    id 0x1337 · ttl 64 · DF", FG, ""),
            ("    checksum", DIM, f"0x{ipck:04x} [correct]"),
            ("▾ Transmission Control Protocol", PURPLE, ""),
            ("    1337 → 80  [PSH, ACK]", FG, ""),
            ("    seq 1 · ack 1", FG, "(relative)"),
            ("    TSval", DIM, str(tsval)),
            ("    checksum", DIM, f"0x{tck:04x} [correct]"),
            (f"▾ Data", GREEN, f"{len(pkt) - 52} bytes")]
    tx = 600
    p.append(f'<rect x="{tx-16}" y="62" width="{916-tx+16}" height="{len(tree)*19+12}" rx="8" fill="{PANEL}" stroke="{LINE}"/>')
    for i, (a, c, b) in enumerate(tree):
        segs = [(a, c)] + ([("  " + b, DIM if c != DIM else GREEN)] if b else [])
        p.append(f'<text x="{tx}" y="{80 + i*19}" font-size="12">{runs(segs)}</text>')
    h = max(y0 + rows * lh, 80 + len(tree) * 19) + 14
    return frame(W, h, "".join(p))


def live_svg(d: dict, now: datetime) -> str:
    W = 940
    p = []
    stats = [("uptime", f"{d['uptime']}", "days", BLUE), ("repos", str(d["repos"]), "public", PURPLE),
             ("followers", str(d["followers"]), "humans", PINK),
             ("last event", d["rows"][0][4] if d["rows"] else "—", "", GREEN)]
    bw = (W - 48 - 3 * 14) / 4
    for i, (k, v, unit, c) in enumerate(stats):
        x = 24 + i * (bw + 14)
        p.append(f'<rect x="{x:.1f}" y="20" width="{bw:.1f}" height="74" rx="8" fill="{PANEL}" stroke="{LINE}"/>')
        p.append(f'<rect x="{x:.1f}" y="20" width="4" height="74" rx="2" fill="{c}"/>')
        p.append(label(x + 18, 42, k.upper(), DIM, 10.5))
        p.append(f'<text x="{x+18:.1f}" y="78" font-size="26" font-weight="700" fill="{FG}">{esc(v)}<tspan fill="{DIM}" font-size="14" font-weight="400">  {esc(unit)}</tspan></text>')
    y = 128
    p.append(label(24, y - 8, "$ last -n 6 crypthium", DIM, 12))
    for i, (kind, c, detail, repo, when) in enumerate(d["rows"] or [("idle", DIM, "", "no public activity yet", "")]):
        ry = y + i * 32
        if i % 2 == 0:
            p.append(f'<rect x="16" y="{ry}" width="{W-32}" height="30" rx="6" fill="{PANEL}"/>')
        p.append(f'<rect x="28" y="{ry+6}" width="64" height="18" rx="9" fill="{c}" fill-opacity=".15" stroke="{c}" stroke-opacity=".55"/>')
        p.append(label(60, ry + 19, kind, c, 11, "middle", 700))
        p.append(label(108, ry + 20, repo[:48], FG, 13))
        p.append(label(560, ry + 20, detail, DIM, 12))
        p.append(label(W - 28, ry + 20, when, DIM, 12, "end"))
    n = max(1, len(d["rows"]))
    p.append(label(W - 24, y + n * 32 + 18, f"synced {now:%Y-%m-%d %H:%M} UTC by .github/workflows/profile.yml", "#484f58", 10.5, "end"))
    return frame(W, y + n * 32 + 30, "".join(p))


def main():
    now_dt = datetime.now(timezone.utc)
    now = int(now_dt.timestamp())
    pkt = build_packet(now)
    write_pcap(pkt, now)
    open(PKT_SVG, "w", encoding="utf-8").write(packet_svg(pkt, now_dt))
    d = fetch(now_dt)
    if d is not None:
        open(LIVE_SVG, "w", encoding="utf-8").write(live_svg(d, now_dt))


if __name__ == "__main__":
    main()
