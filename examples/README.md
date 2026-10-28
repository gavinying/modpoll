# Runnable 2.x examples

- `modsim.tm.json`: unbound simulator model; four block reads and 37 properties.
- `modsim.td.json`: the same mapping with concrete TCP Forms.
- `modsim2.tm.json`: a second device for multi-file/Unit ID testing.
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
loopback. The broker is for local demonstration; use an authenticated broker for
a deployed application.

The previous separate remote/local Compose examples and CSV template were
removed from v2. Existing 1.x examples remain on `main`; see the
[CSV migration guide](../docs/csv-migration.rst) for upgrading a configuration.
