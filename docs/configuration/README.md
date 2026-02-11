# Configuration

This section is the index for LoRA Pilot configuration docs.

## Pages

- [Environment Variables](environment-variables.md)  
  Runtime variables, service-specific env knobs, and build-time `ARG` summary.

- [Models Manifest](models-manifest.md)  
  Manifest format (`name|kind|source|subdir|include|size`), seeding rules, CLI/API behavior.

- [Supervisor](supervisor.md)  
  Managed programs, autostart/log behavior, and ControlPilot service endpoints.

- [Docker Compose](docker-compose.md)  
  Compose file matrix (`standard`, `dev`, `cpu`), runtime behavior, and operational commands.

- [Custom Setup](custom-setup.md)  
  Practical override patterns for images, mounts, ports, bootstrap toggles, and update policy files.

## Source Of Truth In Repo

- Compose/runtime env templates: `.env.example`, `config/env.defaults`, `docker-compose.yml`, `docker-compose.dev.yml`, `docker-compose.cpu.yml`
- Build args: `build.env.example`, `Dockerfile`
- Bootstrapping/runtime wiring: `scripts/bootstrap.sh`, service scripts in `scripts/`
- Supervisor config: `supervisor/supervisord.conf`
- Models manifests: `config/models.manifest`, `config/models.manifest.default`

## Practical Order

1. Set container/runtime env in `.env` (copy from `.env.example`).
2. Start with `docker compose -f docker-compose.yml up -d`.
3. Validate service state in ControlPilot (`/api/services`).
4. Adjust model manifest at `/workspace/config/models.manifest` as needed.
5. Use service autostart/update controls in ControlPilot if required.

## Related

- [Documentation Home](../README.md)
- [Getting Started](../getting-started/README.md)
- [User Guide](../user-guide/README.md)

---

_Last updated: 2026-02-11_
