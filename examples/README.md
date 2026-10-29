# Examples

- `modsim.tm.json`: the runnable 0.1 model used by the CLI examples; four blocks,
  37 properties.
- `modsim.td.json`: the same mapping with concrete local TCP Forms.
- `modsim-standard.tm.json`: the shared package's 0.2 profile candidate, kept
  separate because it demonstrates standard property Forms and is not yet the
  CLI's default model.
- `modsim.csv`: v1 migration and compatibility-test input. v2 does not load it.

From the repository root, run the self-contained TCP/MQTT demonstration:

```sh
mise exec -- docker compose up --build
# In another terminal:
mise exec -- docker compose exec mosquitto mosquitto_sub -t 'modpoll/#' -C 1
# Stop and remove this demonstration:
mise exec -- docker compose down
```

Compose builds the current modpoll checkout, mounts its TM, and starts a local
modsim and disposable anonymous Mosquitto. Host ports 5020 and 18883 bind only to
loopback. The broker configuration is in `docker/mosquitto.conf`; it is for local
demonstration only. Use an authenticated broker for a deployed application.

The previous separate remote/local Compose examples and CSV template were
removed from v2. Existing 1.x examples remain on `main`; see the
[CSV migration guide](../docs/csv-migration.rst) for upgrading a configuration.
