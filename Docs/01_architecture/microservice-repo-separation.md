# Microservice Repo Separation

This workspace started as a monorepo for backend services plus supporting apps.

To move backend services into standalone Git repositories without destabilizing the
current monorepo, use:

```powershell
./tools/bootstrap-microservice-repos.ps1 -Force
```

The script generates local standalone repos under `split-repos/` for:

- `api_execute`
- `AI_dialer`
- `callback_manual`
- `tasks`
- `canales_service`
- `open_agent`
- `evolution_api`

What each generated repo contains:

- service source (`app/`)
- service tests (`tests/`) when available
- vendored `shared/` package when required
- service `Dockerfile`
- per-repo `cloudbuild.yaml`
- per-repo `pyproject.toml`
- root `conftest.py` for standalone test bootstrap
- `MONOREPO_ORIGIN.md` with source and next steps

Important constraints:

- Git history is not preserved by this bootstrap. It is a working-tree snapshot.
- The monorepo remains the source of truth until remotes are created and CI/CD is
  switched per service.
- `frontend` already has its own Git repo and is not part of this split.
- `sudamerica-admin` is not included in this microservice split because it is an app, not
  a backend microservice.

Recommended follow-up:

1. Create remote repos in GitHub for each generated service.
2. Push each local repo to its remote.
3. Move Cloud Build triggers from the monorepo to each service repo.
4. Replace vendored `shared/` with a dedicated shared package repo when ready.
