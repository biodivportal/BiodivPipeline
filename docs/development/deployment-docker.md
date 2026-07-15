# Publishing Module Images to GHCR

A short, copy-paste guide for WP teams to publish their module Docker image to the
**GitHub Container Registry (`ghcr.io`)** so the BiodivPipeline can pull it.

Publishing to GHCR is **free for public images** (no storage or bandwidth limits).
Please keep your image **public** so others can pull it without authentication.

---

## 1. Naming convention

Tag every image as:

```
ghcr.io/biodivportal/<module-name>:<semver>
```

- `<module-name>` — your module, e.g. `column-standardizer`, `taxonomy-classify`,
  `outlier-detect`, `rdf-transform`.
- `<semver>` — a real version like `1.0.0`. **Always tag a version**, not just
  `latest`, so pipeline runs are reproducible.

Example: `ghcr.io/biodivportal/column-standardizer:1.0.0`

---

## 2. Prerequisites

- A working `Dockerfile` at your repo root that builds and runs your module.
- Add this label so GitHub automatically links the image to your repository
  (enables the "Connect repository" UI and inherits its visibility):

  ```dockerfile
  LABEL org.opencontainers.image.source="https://github.com/<owner>/<repo>"
  ```

- **Do not bake secrets into the image.** API keys, tokens, or a populated `.env`
  must never be `COPY`'d or `ENV`'d in. Published layers are inspectable, and public
  images are world-readable. Pass secrets at runtime instead.

---

## 3. Option A — One-off manual push

Use a [Personal Access Token (classic)](https://github.com/settings/tokens) with the
`write:packages` scope as the password.

```bash
# 1. Log in (use your PAT (personal access token) as the password when prompted)
docker login ghcr.io -u <your-github-username> --password-stdin

# 2. Build with the target tag
docker build -t ghcr.io/biodivportal/<module-name>:1.0.0 .

# 3. Push
docker push ghcr.io/biodivportal/<module-name>:1.0.0
```

---

## 4. Make the package public (one-time)

By default a new package may be **private**, which forces others to authenticate.
After the first publish:

1. Go to your repo → **Packages** (right sidebar) → click the package.
2. **Package settings** → **Danger Zone** → **Change visibility** → **Public**.

(If you added the `org.opencontainers.image.source` label and the repo is public,
the package usually inherits public visibility automatically.)

---

## 5. Verify it works

Anyone should be able to pull a public image with no login:

```bash
docker pull ghcr.io/biodivportal/<module-name>:1.0.0
docker run --rm ghcr.io/biodivportal/<module-name>:1.0.0 --help
```

---

## 6. Hand-off to WP1 (pipeline)

Once published, send WP1:

- the full image reference, e.g. `ghcr.io/biodivportal/column-standardizer:1.0.0`;
- the exact command/entrypoint your container expects (inputs → outputs);
- confirmation the package is **public**.

We then set `container 'ghcr.io/biodivportal/<module-name>:1.0.0'` in the module's
`main.nf` and wire it into the pipeline.

---

## Checklist

- [ ] `Dockerfile` builds and runs the module
- [ ] No secrets baked into the image
- [ ] `org.opencontainers.image.source` label added
- [ ] Image tagged `ghcr.io/biodivportal/<module-name>:<semver>`
- [ ] manual push done
- [ ] Package visibility set to **Public**
- [ ] `docker pull` works without authentication
- [ ] Image reference + run command sent to WP1
