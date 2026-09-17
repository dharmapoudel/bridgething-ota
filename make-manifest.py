#!/usr/bin/env python3
"""Generate manifest.json for the dharma Bridgething OTA host.

Usage: make-manifest.py <bridgething.zst> <bridgething-plain> <daemon_version> <image_version> <out_dir>
       [--webapp <slug>:<version>:<zip_path> ...]
Writes <out_dir>/manifest.json. The .zst must already be staged at
<out_dir>/daemon/<channel>/<daemon_version>/bridgething.zst (channel=stable).
Each --webapp zip must already be staged at
<out_dir>/webapps/<channel>/<slug>/<version>/<slug>.zip — the exact URL the
device constructs (OtaArtifactUrls::builtin_webapp).

Both daemon digests are required: the device downloads daemon_zst and
decompresses it, verifying the result against the daemon (uncompressed)
digest. With daemon=null the device falls back to fetching the uncompressed
`bridgething` binary, which is not staged here (daemon_piece in
crates/delivery/core/src/ota/service.rs).

WIRE FORMAT WARNING: the daemon's OtaDiscoverManifest struct applies
`rename_all(serialize = "camelCase")` — serialize ONLY. When the device
*parses* a manifest it expects the Rust field names verbatim, i.e.
snake_case: manifest_version, updated_at, daemon_zst, image_swu, ...
The official manifests (and the repo's ota_manifest.rs test samples) use
snake_case throughout. Do NOT "fix" this to camelCase.
"""
import hashlib, json, os, sys
from datetime import datetime, timezone

args = sys.argv[1:]
zst_path, plain_path, daemon_version, image_version, out_dir = args[0:5]
channel = "stable"
composite = f"{daemon_version}+image.{image_version}"

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return os.path.getsize(path), h.hexdigest()

size, sha256 = digest(zst_path)
plain_size, plain_sha256 = digest(plain_path)

builtin_webapps = {}
webapp_digests = {}
i = 5
while i < len(args):
    assert args[i] == "--webapp", f"unexpected arg: {args[i]}"
    slug, version, zip_path = args[i + 1].split(":", 2)
    wsize, wsha = digest(zip_path)
    builtin_webapps[slug] = version
    webapp_digests[slug] = {"size": wsize, "sha256": wsha}
    staged = os.path.join(out_dir, "webapps", channel, slug, version, f"{slug}.zip")
    assert os.path.isfile(staged), f"missing staged webapp: {staged}"
    assert os.path.abspath(zip_path) == os.path.abspath(staged), f"zip path != staged path: {zip_path}"
    print(f"webapp {slug} {version}: sha256={wsha[:16]}... size={wsize}")
    i += 2

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
            "builtin_webapps": builtin_webapps,
            "wakeword": None,
            "artifacts": {
                "daemon": {"size": plain_size, "sha256": plain_sha256},
                "daemon_zst": {"size": size, "sha256": sha256},
                "image_swu": None,
                "image_zck": None,
                "image_boot_zck": None,
                "webapps": webapp_digests,
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
d = rel["artifacts"]["daemon"]
assert set(d) == {"size", "sha256"}, "daemon digest must be present (else device fetches the unstaged plain binary)"
assert isinstance(ch["default"], bool), "'default' must be a bool"
for slug, wd in rel["artifacts"]["webapps"].items():
    assert set(wd) == {"size", "sha256"}, f"webapp {slug} digest shape wrong"
    assert slug in rel["builtin_webapps"], f"webapp {slug} missing from builtin_webapps map"

# Sanity: the artifact URL the daemon will construct must exist on disk.
expected = os.path.join(out_dir, "daemon", channel, daemon_version, "bridgething.zst")
assert os.path.isfile(expected), f"missing staged artifact: {expected}"
assert os.path.abspath(zst_path) == os.path.abspath(expected), "zst path != staged path"

with open(os.path.join(out_dir, "manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)
    f.write("\n")
print(f"wrote manifest.json: {composite}  daemon_zst sha256={sha256[:16]}... size={size}")
