"""Preserve existing evidence, checking the digests returned by GitHub.

Only GitHub Actions' ordinary repository token is used, never persisted.
No PMU requests are made. The files are small (< 1 MB each).
"""
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        redirected = super().redirect_request(request, fp, code, message, headers, new_url)
        if redirected and urlparse(request.full_url).netloc != urlparse(new_url).netloc:
            redirected.remove_header("Authorization")
        return redirected

ARTIFACTS = [
    (38238010891, 11741548220, "pmu-deep-audit.zip", "b2fac86c0419d6a83b0323a18e49126762e059fa4da1b8b76bdcc9116053739e"),
    (38233770270, 11740330993, "pmu-probe.zip", "057bfef8fc6cc45d5bef921af696c5097bbfbc714c0de596c669a980f659e3f2"),
]


def main():
    out = Path("data/reference")
    out.mkdir(parents=True, exist_ok=True)
    manifest = []
    for run, artifact, name, expected in ARTIFACTS:
        path = out / name
        if not path.exists():
            url = f"https://api.github.com/repos/berangerbeato-cmd/turf-lab/actions/artifacts/{artifact}/zip"
            req = Request(url, headers={
                "Authorization": "Bearer " + os.environ["GITHUB_TOKEN"],
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            })
            with build_opener(SafeRedirect).open(req, timeout=60) as response:
                payload = response.read(5_000_001)
            if len(payload) > 5_000_000:
                raise RuntimeError("Unexpectedly large reference artifact")
            if hashlib.sha256(payload).hexdigest() != expected:
                raise RuntimeError(f"Digest mismatch: {name}")
            path.write_bytes(payload)
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"Existing file has incorrect digest: {name}")
        manifest.append(dict(run_id=run, artifact_id=artifact, file=str(path),
                             sha256=actual, bytes=path.stat().st_size,
                             source=f"https://github.com/berangerbeato-cmd/turf-lab/actions/runs/{run}"))
        print(f"VERIFIED {name} {actual}", flush=True)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
