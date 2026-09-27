# CLAUDE.md: maintenance notes for this repository

This file is the project memory. It records **why** the firmware looks the
way it does, how to verify changes, and how the repo is meant to be worked
on. Read it before editing `esphome/.soil-moisture.base.yaml`. Many lines there
look arbitrary and are not.

User-facing documentation lives in [README.md](README.md). Keep the two in
sync: README = how to use, CLAUDE.md = why and how to maintain.

## Purpose and deployment model

- Firmware for the Seeed XIAO Soil Moisture Sensor (ESP32-C6, 1× AA NiMH).
- Several identical sensors (4 as of 2026-09) run the **same** package. The
  per-device file in the Home Assistant ESPHome Device Builder only holds
  substitutions and pulls `esphome/.soil-moisture.base.yaml` plus one label file
  from GitHub. The pattern follows
  [norbertbaum/fonske_Brink-flair-modbus](https://github.com/norbertbaum/fonske_Brink-flair-modbus):
  hidden `.base.yaml`, `labels/.…-labels-<lang>.yaml`, `example.yaml`.
- **The repository is public.** No real credentials or IP addresses. The
  base package takes all credentials via substitutions (`api_encryption_key`,
  `ota_password`, `ap_password`) and `!secret wifi_ssid/wifi_password`.
  `tests/secrets.yaml` holds dummy values and is committed on purpose. The
  `.gitignore` ignores every other `secrets.yaml`. **Never** add an
  `esphome/secrets.yaml`: ESPHome resolves `!secret` relative to the
  including file first, so it would shadow the user's real secrets.
- The repo was started fresh on 2026-09-27 from a private single-device
  project. The old history was not imported because it contained plain-text keys.

## Working conventions

- Work on branches (`feature/…`, `fix/…`, `docs/…`) and open pull requests.
  Do not push to `main` directly.
- Code comments and docs are in **English**. Only the German label file is German.
- Commit messages: imperative summary line, body explains why.
- When behaviour or a default changes, update the README tables, this file, and
  `project.version` in the base package in the same PR. Release with a
  tag `vX.Y.Z` so devices can pin `ref:`.
- Keep `requirements.txt` (ESPHome pin) in sync with the ESPHome Device Builder
  add-on version in Home Assistant (2026.9.0 as of 2026-09-27).
  `esphome: min_version` in the base package is the lowest version that has been verified.

## Verify every change

```bash
pip install -r requirements.txt
python tests/check_labels.py              # label files consistent with base
esphome config  tests/soil-test-en.yaml   # both languages
esphome config  tests/soil-test-de.yaml
esphome compile tests/soil-test-en.yaml   # at least one full compile
```

CI (`.github/workflows/ci.yaml`) runs all of this for `en` and `de`.
`soil-test-de.yaml` also overrides tuning values and adds `wifi: use_address`,
which proves that device-level overrides and merges still work.

**Windows:** ESP-IDF object paths exceed `CMAKE_OBJECT_PATH_MAX` (250) when the
build directory is deep. Symptom: "Configuring incomplete, errors occurred!"
plus CMake warnings about 249-character object paths. Set
`ESPHOME_DATA_DIR` to a short path, e.g. `C:\Daten\.esph`. A second,
independent trap: PlatformIO's `tool-cmake` can be extracted incompletely
("Could not find CMAKE_ROOT"). Fix: delete `~/.platformio/packages/tool-cmake`,
and it is downloaded again.

A clean compile takes about 2 minutes. Reference sizes are in the
"Build size" section at the end.

## Substitution contract

- **Required** (no default, config fails without them): `name`,
  `friendly_name`, `stay_awake_entity`, `api_encryption_key`, `ota_password`,
  `ap_password`, and all `label_*` / `state_*` keys (from the label file).
- **Optional** tuning defaults are in the `substitutions:` block of the base package.
  Device substitutions override package substitutions.
- Label values are pasted into C++ string literals. No `"` and no `\`.
  `tests/check_labels.py` enforces this. It also checks that every label file
  has the same keys and that every key is used by the base package.
- Adding a label: add it to **both** label files and use it as `"${key}"` in
  the base package. The check script fails otherwise.

## Entity identity: do not rename casually

- ESPHome derives an entity's unique id (and its preference hash) from the
  **entity name**. Renaming a label, or switching an existing device to another
  language, creates new entities in HA. The old ones are orphaned with their history,
  and the *Disable Deep Sleep* switch loses its restored state.
- The **English labels are byte-identical to the original single-device
  firmware** ("Soil Moisture %", "Battery %", …) so the first sensor
  (`bodenfeuchte-8f63bc`) keeps its entities. Do not "clean them up".
- Globals are restored by **id** (`md5(id)`), not by name. Renaming a
  global id discards the learned calibration on every device. Changing
  `initial_value` does not affect devices that already have a stored value.
- `esphome: name` becomes the hostname. For the first sensor, use
  `name: bodenfeuchte-8f63bc` (the old `name_add_mac_suffix` result) to keep
  the same hostname and HA device.

## Hardware facts (verified on the device)

- The probe needs its **analog frontend**: GPIO21 200 kHz PWM at **68 % duty**
  (operating point of the Seeed reference design, not a brightness), GPIO14 ON
  (power), GPIO3 OFF. Without it GPIO1 reads ~0.002 V. **GPIO14 also powers the
  battery measurement**. "Battery 0 %" and "soil 0 V" had the same root cause.
- `sensor_hw_init` must run after **every** boot, including deep-sleep
  wake-ups, which lose GPIO/LEDC state. `measure_and_sleep` also calls it,
  because the 60 s timer and the button trigger it too.
- Measured voltages: air 2.384 V, pot before watering 2.240 V, right after
  watering 2.205 V. First device's learned range after a few weeks: about 2.31–2.71 V.
  **Wet = lower voltage.** The span is 0.18–0.40 V, far below the Seeed wiki values.
- An early note "air reads 0.01 V" was **wrong**. It was the dead ADC before
  the frontend init existed.

## Boot-order traps

1. **`on_boot` priority must stay 600.** `ledc`/`gpio` outputs set up at
   `HARDWARE` (800). With 800, on_boot raced the outputs it drives.
2. **No `light` component for the PWM.** The Seeed original uses a
   `monochromatic` light on GPIO21. A light restores its state with
   `RESTORE_DEFAULT_OFF` in `LightState::setup()` at priority 799, so it switches
   the PWM off again after on_boot. A plain `output` has no restore semantics.

## USB detection

- `usb_serial_jtag_is_connected()` counts SOF packets, which only a real USB host sends.
  A charger without data lines is correctly detected as "no USB".
- **ESP-IDF initialises the status to `true`** ("always assume connected until
  we are sure it is not", `usb_serial_jtag_connection_monitor.c`). It only turns false after
  a few FreeRTOS ticks without SOF. Without `usb_settle_ms` (500 ms) the device would never sleep on
  battery. The real tolerance is ~40 ms, so 500 ms is a generous margin.
- The headers come in as `includes: - <driver/usb_serial_jtag.h>`. Angle-bracket
  includes need no file. A local `includes: - bf_usb.h` (the old approach)
  is resolved relative to the **device** file (`CORE.relative_config_path`), so it
  breaks as soon as the package is pulled from GitHub. The helper functions of
  the old `bf_usb.h` are now inline in the lambda.

## Sleep decision and the wake-window mailbox

- Order: USB → local switch → HA request → sleep. See `decide_sleep`.
- A sleeping ESP32 has Wi-Fi and the API off. HA cannot push anything. The device
  subscribes to `stay_awake_entity` (a `homeassistant` binary sensor) and
  reads it after connecting.
- `api.connected` does **not** mean subscribed states have arrived. There is
  therefore a `wait_until has_state()` with a 2 s timeout, and it runs only
  when the answer can change the decision (not on USB, not with the local
  override). Measured awake time per cycle: 7.6 s with an unconditional 5 s wait,
  2.6 s now.
- The window length (`wake_budget_min`) is the hard battery guard. When it
  expires the device sleeps even if the helper is still on.
- The device acknowledges by calling `input_boolean.turn_off`. This needs "Allow
  the device to perform Home Assistant actions". Without it only the
  auto-reset is missing.
- **One helper per device.** A shared helper would be cleared by the first
  device that wakes up, and the others would miss the request.
- `wait_until: api.connected` has a 60 s timeout. Without it a missing
  Wi-Fi/HA meant the script hung forever and the battery drained.
- The `interval: 60s` condition includes `wake_window_until_ms > 0`. Otherwise
  `decide_sleep` never runs again during a requested window.

## Auto-calibration design

- **Seed, do not guess.** The first plausible reading sets dry = wet = reading
  (`cal_seeded`). The previous design started from wiki values 2.75 / 1.2 V:
  `wet_value` can only decrease, and 1.2 V is below anything the hardware
  delivers, so it was a permanent fake floor. A real 0.18 V span was squeezed
  into 11 percentage points, and "Normal Moisture" (> 60 %) was unreachable.
- There is **no fallback to factory values**. Below `min_span`, the device reports
  `NAN` plus the status "Calibrating (x/y V)".
- New extremes need a **second confirming reading** within `confirm_tol`.
  Candidates (`pend_dry`/`pend_wet`) are stored in NVS, because each measurement is its own boot.
- Decay is **relative** to the span (`decay_frac_per_day`). An absolute V/day
  value tuned for 1.5 V destroys a 0.18 V span. Simulated over 6 watering cycles
  with the measured span: `min_span 0.05` + 2 %/day gave a final span of 0.194 V
  against a real 0.195 V, using the full 0–100 % scale.
- Decay needs wall-clock time (`time: homeassistant`). Without sync it is skipped.
- Readings outside `v_min_plausible … v_max_plausible` are rejected (`NAN`,
  status "Sensor Error", 15 min sleep). The top end cannot detect air (see README).
- Reset (3× button or HA button) clears `cal_seeded`. It does not restore factory values.

## History: bugs fixed in the Seeed original

All of these were verified against the ESPHome 2026.6.4 source or on the device. The original
**compiles cleanly**. These are all runtime bugs.

1. The analog frontend (GPIO21/14/3) was missing. The ADC read ~0.002 V, and the
   firmware turned that into "100 % / Normal Moisture".
2. The status LEDs never turned on: `id(x).turn_on()` only builds a `LightCall`.
   It needs `.perform()`.
3. The triple press was unreachable: a `static int` counter was reset in the
   else-branch on every press. It was replaced with `on_multi_click`.
4. Deep sleep was disabled twice: `on_boot` set `disable_sleep = true`, and
   `restore_mode: ALWAYS_ON` runs `turn_on_action` on every boot. The battery was empty in hours.
5. `wait_until: api.connected` had no timeout.
6. The LEDs were never switched off in `measure_and_sleep`.
7. There was 1.5 s of blocking `delay()` in the measurement loop. This is now a median of 5 hardware-averaged
   reads (~100 ms, still triggers a harmless "took a long time" warning).

Not a bug: `deep_sleep.prevent` without `allow`. `deep_sleep.enter` calls
`begin_sleep(manual=true)`, which ignores `prevent_`.

## Open points / ideas

- A new sensor needs a full dry-out and watering cycle before it reports
  percentages. That is expected.
- The per-device tuning values come from one device. If the other sensors
  show a very different span, adjust `min_span` / `confirm_tol` per device.
- The cosmetic warning `measure_and_sleep took a long time (≈109 ms)` comes
  from the 5 × 20 ms loop.

## Build size

| Config | ESPHome | RAM | Flash |
|---|---|---|---|
| single-device firmware (predecessor) | 2026.6.4 | 16.0 % (52 328 B) | 58.6 % (1 074 740 B) |
| `tests/soil-test-en.yaml` (v1.0.0) | 2026.6.4 | 16.3 % (53 408 B) | 59.7 % (1 095 054 B) |

The small growth comes from the `device_class` / `state_class` metadata and the
labels. It is not a problem: flash is at 60 % of 1.8 MB.
