#!/usr/bin/env python3
"""Regenerates the live parts of the profile README.

- builds a real IPv4/TCP packet (valid checksums, TCP timestamp = now)
- writes it as assets/crypthium.pcap + a hexdump in the README
- pulls recent public activity from the GitHub API
Runs daily from .github/workflows/profile.yml
"""
import json, os, re, struct, time, urllib.request
from datetime import datetime, timezone

USER = "Crypthium123"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
PCAP = os.path.join(ROOT, "assets", "crypthium.pcap")

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


def activity(now: datetime) -> str:
    try:
        user = api(f"/users/{USER}")
        events = api(f"/users/{USER}/events/public?per_page=60")
    except Exception as exc:  # keep the old block if the API is down
        print("api error:", exc)
        return None
    rows = []
    for ev in events:
        repo = ev["repo"]["name"].split("/", 1)[-1]
        t, p = ev["type"], ev.get("payload", {})
        if t == "PushEvent":
            n = p.get("size", len(p.get("commits", [])))
            what = f"push     {n} commit{'s' if n != 1 else ''}"
        elif t == "CreateEvent":
            what = f"create   {p.get('ref_type', '')}"
        elif t == "PullRequestEvent":
            what = f"pr       {p.get('action', '')}"
        elif t == "IssuesEvent":
            what = f"issue    {p.get('action', '')}"
        elif t == "WatchEvent":
            what = "star"
        elif t == "ForkEvent":
            what = "fork"
        else:
            continue
        rows.append(f"{what:<20} {repo[:34]:<34} {ago(ev['created_at'], now)}")
        if len(rows) == 6:
            break
    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    up = (now - created).days
    head = (f"$ uptime\n up {up} days, {user['public_repos']} repos, "
            f"{user['followers']} followers\n\n$ last -n {len(rows)} crypthium\n")
    return head + ("\n".join(rows) if rows else "(no public activity yet)")


# ---------------------------------------------------------------- readme
def replace(text: str, tag: str, body: str) -> str:
    pat = re.compile(rf"(<!--{tag}:start-->\n).*?(\n<!--{tag}:end-->)", re.S)
    return pat.sub(lambda m: m.group(1) + body + m.group(2), text)


def main():
    now_dt = datetime.now(timezone.utc)
    now = int(now_dt.timestamp())
    pkt = build_packet(now)
    write_pcap(pkt, now)
    text = open(README, encoding="utf-8").read()
    text = replace(text, "packet", "```\n" + hexdump(pkt) + "\n```")
    act = activity(now_dt)
    if act is not None:
        stamp = now_dt.strftime("%Y-%m-%d %H:%M UTC")
        text = replace(text, "live", f"```\n{act}\n```\n<sub>last sync: {stamp}</sub>")
    open(README, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    main()
