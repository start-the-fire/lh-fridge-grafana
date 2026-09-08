# TempVerity

TempVerity is a standalone monitoring application created from the project handover in
`TempVerity/TempVerity_Project_Handover_for_Codex.docx`.

This directory contains the new app in the dedicated `TempVerity/` location
requested in the handover. The existing documentation assets are preserved
alongside the app source for traceability.

## Layout

- `backend/` FastAPI application, SQLite persistence, adapter/service layer
- `frontend/` React + TypeScript + Vite dashboard
- `Dockerfile` single-container build that serves the built frontend from the
  backend

## Current state

The application includes:

- a FastAPI API surface for devices, alerts, events, settings, and health
- SQLite models and optional demonstration device fixtures
- a React dashboard shell with a TempVerity-style layout
- a multi-device, multi-zone UI connected to the Liebherr adapter layer

The implementation is intentionally vendor-neutral and keeps the existing
historical InfluxDB/Grafana stack untouched.

## Development

The backend and frontend are separated cleanly so they can be extended in
parallel. The backend serves the frontend build in production mode.

## Dependency updates

Check current Python and frontend dependency versions without changing files:

```sh
./update_versions.sh
```

Apply Python lower-bound updates and frontend updates within the declared npm
version ranges:

```sh
./update_versions.sh --update
```

Use `--python-only` when Node/npm is not installed locally. Rebuild the Docker
image after applying updates.

## Full-capability demo device

Create a local two-zone demo appliance containing the API capabilities and
parameters used to exercise the device detail view:

```sh
docker exec tempverity python -m backend.app.cli create-demo-device
```

The fixture uses the demo adapter and never contacts a Liebherr appliance.

## Password reset

If authentication is enabled and an administrator or viewer password is
forgotten, reset it from the running container. The command prompts twice and
does not echo the password:

```sh
docker exec -it tempverity python -m backend.app.cli reset-password --username administrator
docker exec -it tempverity python -m backend.app.cli reset-password --username viewer
```

The command invalidates existing sessions for that account. A `--password`
argument is available for automation, but the interactive prompt is safer.
