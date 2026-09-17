#!/usr/bin/env python3
"""Generate manifest.json for the dharma Bridgething OTA host.

Usage: make-manifest.py <bridgething.zst> <daemon_version> <image_version> <out_dir>
Writes <out_dir>/manifest.json. The .zst must already be staged at
<out_dir>/daemon/<channel>/<daemon_version>/bridgething.zst (channel=stable).
"""
import hashlib, json, os, sys
from datetime import datetime, timezone

zst_path, daemon_version, image_version, out_dir = sys.argv[1:5]
channel = "stable"
composite = f"{daemon_version}+image.{image_version}"

size = os.path.getsize(zst_path)
sha256 = hashlib.sha256(open(zst_path, "rb").read()).hexdigest()

manifest = {
    "manifestVersion": 1,
    "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "channels": {
        channel: {
            "name": channel,
            "stability": "stable",
            "default": True,
            "latest": composite,
            "releases": [composite],
        }
    },
    "releases": {
        composite: {
            "version": composite,
            "channel": channel,
            "yanked": None,
            "deprecated": False,
            "builtinWebapps": {},
            "wakeword": None,
            "artifacts": {
                "daemon": None,
                "daemonZst": {"size": size, "sha256": sha256},
                "imageSwu": None,
                "imageZck": None,
                "imageBootZck": None,
                "webapps": {},
                "wakeword": None,
                "daemonPatches": {},
            },
        }
    },
}

# Sanity: the artifact URL the daemon will construct must exist on disk.
expected = os.path.join(out_dir, "daemon", channel, daemon_version, "bridgething.zst")
assert os.path.isfile(expected), f"missing staged artifact: {expected}"
assert os.path.abspath(zst_path) == os.path.abspath(expected), "zst path != staged path"

with open(os.path.join(out_dir, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)
    f.write("\n")
print(f"wrote manifest.json: {composite}  daemon_zst sha256={sha256[:16]}... size={size}")
