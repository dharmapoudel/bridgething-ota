#!/usr/bin/env python3
"""Generate manifest.json for the dharma Bridgething OTA host.

Usage: make-manifest.py <bridgething.zst> <daemon_version> <image_version> <out_dir>
Writes <out_dir>/manifest.json. The .zst must already be staged at
<out_dir>/daemon/<channel>/<daemon_version>/bridgething.zst (channel=stable).

WIRE FORMAT WARNING: the daemon's OtaDiscoverManifest struct applies
`rename_all(serialize = "camelCase")` — serialize ONLY. When the device
*parses* a manifest it expects the Rust field names verbatim, i.e.
snake_case: manifest_version, updated_at, daemon_zst, image_swu, ...
The official manifests (and the repo's ota_manifest.rs test samples) use
snake_case throughout. Do NOT "fix" this to camelCase.
"""
import hashlib, json, os, sys
from datetime import datetime, timezone

zst_path, daemon_version, image_version, out_dir = sys.argv[1:5]
channel = "stable"
composite = f"{daemon_version}+image.{image_version}"

size = os.path.getsize(zst_path)
sha256 = hashlib.sha256(open(zst_path, "rb").read()).hexdigest()

manifest = {
    "manifest_version": 1,
    "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
            "builtin_webapps": {},
            "wakeword": None,
            "artifacts": {
                "daemon": None,
                "daemon_zst": {"size": size, "sha256": sha256},
                "image_swu": None,
                "image_zck": None,
                "image_boot_zck": None,
                "webapps": {},
                "wakeword": None,
                "daemon_patches": {},
            },
        }
    },
}

# Schema self-check: every field the daemon REQUIRES on deserialize must be
# present under its snake_case name (see OtaDiscoverManifest in
# crates/delivery/core/src/ota/manifest.rs and the ota_manifest.rs samples).
top = manifest
for f in ("manifest_version", "updated_at", "channels", "releases"):
    assert f in top, f"top-level field missing: {f}"
ch = top["channels"][channel]
for f in ("name", "stability", "default", "latest", "releases"):
    assert f in ch, f"channel field missing: {f}"
rel = top["releases"][composite]
for f in ("version", "channel", "artifacts"):
    assert f in rel, f"release field missing: {f}"
dz = rel["artifacts"]["daemon_zst"]
assert set(dz) == {"size", "sha256"}, "daemon_zst digest shape wrong"
assert isinstance(ch["default"], bool), "'default' must be a bool"

# Sanity: the artifact URL the daemon will construct must exist on disk.
expected = os.path.join(out_dir, "daemon", channel, daemon_version, "bridgething.zst")
assert os.path.isfile(expected), f"missing staged artifact: {expected}"
assert os.path.abspath(zst_path) == os.path.abspath(expected), "zst path != staged path"

with open(os.path.join(out_dir, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)
    f.write("\n")
print(f"wrote manifest.json: {composite}  daemon_zst sha256={sha256[:16]}... size={size}")
