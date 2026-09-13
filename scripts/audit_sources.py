"""Fetch public evidence only. No authentication, no assumption of usable hydrology."""

import csv
import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence"
OUT.mkdir(parents=True, exist_ok=True)


def fetch(url, limit=25_000_000):
    try:
        with urlopen(Request(url, headers={"User-Agent": "DamSafe feasibility audit"}), timeout=30) as r:
            body = r.read(limit + 1)
            if len(body) > limit:
                return {"url": url, "error": "Response exceeded audit limit"}, None
            return {
                "url": url,
                "final_url": r.url,
                "status": r.status,
                "content_type": r.headers.get("Content-Type"),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }, body
    except (HTTPError, URLError, TimeoutError) as e:
        return {"url": url, "error": str(e)}, None


if __name__ == "__main__":
    report = {"retrieved_at": datetime.now(UTC).isoformat(), "resources": [], "engines": {}}
    catalogue = json.loads((OUT / "nwic-catalogue.json").read_text(encoding="utf-8-sig"))["result"]
    for resource in catalogue["resources"]:
        info, body = fetch(resource["url"])
        info.update(resource_id=resource["id"], catalogue_name=resource["name"])
        if body:
            sample = body[:1000].decode("utf-8-sig", errors="replace")
            info["preview"] = sample
            if "<html" not in sample.lower() and "<!doctype" not in sample.lower():
                raw = ROOT / "data/raw"
                raw.mkdir(parents=True, exist_ok=True)
                (raw / f"{resource['id']}.csv").write_bytes(body)
                rows = list(csv.reader(io.StringIO(body.decode("utf-8-sig"))))
                info["header"] = rows[0] if rows else []
                info["rows"] = max(0, len(rows) - 1)
        report["resources"].append(info)
    for repo, branch in [("Deltares/Delft3D", "main"), ("DualSPHysics/DualSPHysics", "master")]:
        info, body = fetch(f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1")
        if body:
            tree = json.loads(body)
            info["commit"] = tree.get("sha")
            info["candidates"] = [
                {"path": t["path"], "size": t.get("size")}
                for t in tree.get("tree", [])
                if (
                    (t["path"].endswith((".exe", ".dll")) and "bin/" in t["path"])
                    or ("01_DamBreak" in t["path"])
                    or t["path"] in ["LICENSE", "doc/compiling_Windows.md"]
                )
            ]
        report["engines"][repo] = info
    (OUT / "source-audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
