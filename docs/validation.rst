Configuration replacement verification
======================================

M2 exercises the complete TM/TD-to-device-to-output path. Tests use a separate
modsim process and compare against the pinned 1.x checkout; no physical device
or contributed device configuration is required.

Reading acceptance
------------------

``tools/verify_modsim_equivalence.py`` compares all 37 simulator properties,
rendered CLI tables, JSON snapshots and the four actual requests from 1.x CSV,
2.x TM and 2.x TD. The local simulator also has independent expected values.
Public remote state may have been changed, so remote runs compare successive
actual snapshots rather than asserting initial values.

``tests/test_wot_reading_interop.py`` independently encodes all supported numeric
register types with Python struct, including integers beyond JavaScript's exact
integer range, and tests all four byte/word orders. It also checks register bits,
odd string lengths, zero/negative/fractional multipliers, Unit ID 7, real local
HTTP model loading, multiple devices, timestamps and JSON precision. A request-recording proxy also
verifies per-model Unit IDs 2 and 7 in one CLI run, with explicit CLI overrides
still available. Invalid
models fail before polling; Modbus exceptions produce null samples without
hiding valid groups.

MQTT acceptance
---------------

``tests/test_mqtt_modsim_interop.py`` runs unmodified 1.x and 2.x CLIs, checking
MQTT 3.1.1 and 5.0, grouped JSON and individual topics, publication topics,
QoS 0/1, diagnostics, retained-command rejection and FC5/6/16 command round trips.
Every run subscribes and publishes only under its own UUID namespace, clears its
retained test key, and directs commands exclusively to a temporary local modsim.

For repeatable acceptance, CI starts a private local Mosquitto broker. The existing
local broker tests additionally cover authentication rejection, subscription
recovery after broker restart and a full receiving queue.

To start an isolated local broker (remove it after testing)::

    printf 'listener 1883\nallow_anonymous true\npersistence false\n' > /tmp/modpoll-mosquitto.conf
    docker run -d --name modpoll-mqtt-acceptance -p 127.0.0.1:18883:1883 -v /tmp/modpoll-mosquitto.conf:/mosquitto/config/mosquitto.conf:ro eclipse-mosquitto:2

Then run with installed mise/Poetry project environments::

    export MODSIM_SOURCE=/path/to/modsim
    export MODSIM_PYTHON=$MODSIM_SOURCE/.venv/bin/python
    export MODPOLL_1X_SOURCE=/path/to/modpoll-1x
    export MODPOLL_MQTT_HOST=127.0.0.1
    export MODPOLL_MQTT_PORT=18883
    mise exec -- poetry run pytest -q tests/test_wot_reading_interop.py tests/test_mqtt_modsim_interop.py
    docker rm -f modpoll-mqtt-acceptance

The public broker smoke test can use ``MODPOLL_MQTT_HOST=broker.emqx.io`` and
``MODPOLL_MQTT_PORT=1883`` with ``-k grouped-json``. Both protocol versions passed
that test. In a separate single-topic baseline probe, the 1.x publisher received
65 PUBACKs but the subscriber observed only 15 distinct topics, with no publisher
disconnect recorded. This public-service observation is not treated as a 2.x
regression or hidden by retries: the complete individual-topic matrix is verified
on the isolated broker, where all 1.x/TM/TD messages and values matched.

These tests validate the M2 reading/output contract and selected existing command
paths. They do not claim serial hardware validation or a release-ready application
package; those remain later milestone work.

The complete local acceptance run on 2026-10-28 passed 109 tests with all
opt-in environments enabled, including the three local authentication/reconnect/queue
tests. Public grouped JSON verification passed four cases: MQTT 3.1.1/5.0 with
QoS 0/1. The six-case local CLI matrix also covered individual-topic output.
