# bridgething-ota

Self-hosted OTA update host for Bridgething on the Spotify Car Thing.

Point the companion app's **custom update host** setting at
`https://dharmapoudel.github.io/bridgething-ota` and the daemon will
check `manifest.json` here instead of the official update server.

## Layout

- `manifest.json` — the OTA discovery manifest (channels → releases → artifacts)
- `daemon/<channel>/<daemon_version>/bridgething.zst` — compressed daemon binaries
- `make-manifest.py` — regenerates `manifest.json` for a new release:
  `make-manifest.py <bridgething.zst> <daemon_version> <image_version> <out_dir>`

## Current release

- **0.12.12+image.0.2.5** (stable channel, daemon-only): upstream 0.12.11 plus
  the M-button launcher gesture (gateway input surface + UniFFI get/set API)
  and overlay-app companion config injection.
