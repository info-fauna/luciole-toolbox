# One-time repo/account setup for the workflows

This step happens outside this repo and can't be scripted from here — do
it once before the `release.yml` workflow can succeed.

## PyPI Trusted Publishing (needed for `release.yml`)

Trusted Publishing lets GitHub Actions publish to PyPI via OIDC, with no
API token stored as a repo secret.

1. Create the `luciole-toolbox` project on PyPI if it doesn't exist yet
   (first publish can also be done manually once to reserve the name —
   trusted publishing can be configured before or after that).
2. Go to <https://pypi.org/manage/project/luciole-toolbox/settings/publishing/>
   (or, for a not-yet-existing project, <https://pypi.org/manage/account/publishing/>
   to pre-register a "pending" publisher).
3. Add a new trusted publisher with:
   - **Owner**: `info-fauna`
   - **Repository name**: `luciole-toolbox`
   - **Workflow name**: `release.yml`
   - **Environment name**: `pypi`
4. In the GitHub repo, go to **Settings → Environments → New environment**,
   name it `pypi` (must match exactly). Optionally add required reviewers
   here if you want a manual approval gate before every publish.

No secrets to add — `id-token: write` permission in `release.yml` handles
the OIDC handshake.

## Triggering a release

Once the trusted publisher above is configured:

```bash
git tag v0.1.0
git push origin v0.1.0
```

This triggers `release.yml`, which builds the package (version comes from
the tag via `hatch-vcs`), publishes to PyPI, and creates a GitHub Release
with auto-generated notes and the built artifacts attached.
