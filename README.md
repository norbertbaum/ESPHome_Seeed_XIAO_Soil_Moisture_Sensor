# ESPHome firmware for the Seeed XIAO Soil Moisture Sensor (ESP32-C6)

Battery-friendly ESPHome firmware for the
[Seeed Studio XIAO Soil Moisture Sensor](https://wiki.seeedstudio.com/xiao_soil_moisture_sensor/),
shipped as a **shared package**: every sensor runs exactly the same code, and
each device file in the ESPHome Device Builder only contains its name and
credentials.

- **Self-learning calibration.** No manual dry/wet calibration. The range is
  seeded from the first real reading, then widened by confirmed extremes and
  slowly shrunk again so outliers heal.
- **Dynamic deep sleep.** Dry soil is measured every 15 min, moist soil every 8 h.
- **USB detection.** Connected to a USB host, the device stays awake and
  re-measures every 60 s, so you can read logs and flash over the air. On battery it sleeps.
- **"Mailbox" wake window.** Request a 10 min wake window from Home Assistant
  while the device is asleep. It picks the request up on the next wake-up, so OTA updates work on battery.
- **Labels in English and German**, selected per device.

## Quick start

### 1. Home Assistant: one helper per sensor

Add [`homeassistant/soil_moisture_helpers.yaml`](homeassistant/soil_moisture_helpers.yaml)
to your `configuration.yaml` (or copy the entries you need), then
*Developer tools → YAML → Input booleans* to reload.

> Create the helper in YAML, not in the UI. The UI derives the entity id from
> the *name*: "Bodenfeuchte 1 wach bleiben" becomes
> `input_boolean.bodenfeuchte_1_wach_bleiben`. If the id does not match the device's
> `stay_awake_entity`, the device silently never sees the request. In YAML,
> the key is the entity id.

### 2. ESPHome Device Builder: secrets

In `/config/esphome/secrets.yaml`:

```yaml
wifi_ssid: "YourWifi"
wifi_password: "YourWifiPassword"

soil_1_api_key: "…32 bytes base64…"   # the Device Builder generates one for new devices
soil_1_ota_password: "…"
soil_1_ap_password: "…"               # fallback hotspot, only active without Wi-Fi
```

One `soil_N_*` set per sensor.

### 3. ESPHome Device Builder: device file

Create a new device, then replace its YAML with
[`esphome/example.yaml`](esphome/example.yaml) and adapt the substitutions:

```yaml
substitutions:
  name: soil-moisture-1
  friendly_name: Soil Moisture 1
  stay_awake_entity: input_boolean.soil_moisture_1_stay_awake
  api_encryption_key: !secret soil_1_api_key
  ota_password: !secret soil_1_ota_password
  ap_password: !secret soil_1_ap_password

packages:
  soil_moisture:
    url: https://github.com/norbertbaum/ESPHome_Seeed_XIAO_Soil_Moisture_Sensor
    ref: main          # or a release tag, e.g. v1.0.0
    refresh: 1d
    files:
      - esphome/labels/.soil-moisture-labels-en.yaml   # or -de.yaml
      - esphome/.soil-moisture.base.yaml
```

### 4. Flash

The **first** flash of a new device must go over USB (*Install → Plug into
this computer*, or download the binary and use
[web.esphome.io](https://web.esphome.io)). After that, OTA works whenever the device is awake (see
[Operating modes](#operating-modes)).

In Home Assistant, enable *Allow the device to perform Home Assistant actions*
for each device (Settings → Devices & services → ESPHome → device → Configure),
so the device can reset its stay-awake helper by itself.

### Updating all sensors

- `ref: main`: *Update All* in the Device Builder rebuilds every sensor with
  the latest code. `refresh: 1d` means the Device Builder checks GitHub at most once a day.
  To pick up a change right away, use *Clean Build Files* or set `refresh: 0s` temporarily.
- `ref: v1.2.3`: sensors stay on that release until you change the tag.
  This is the recommended way to run several sensors. Nothing changes by accident.

Battery sensors are asleep most of the time. Plan the OTA with the
[wake window](#requesting-a-wake-window-the-mailbox).

## Configuration

### Required substitutions

| Substitution | Example | Meaning |
|---|---|---|
| `name` | `soil-moisture-1` | Hostname, unique, `a-z 0-9 -` |
| `friendly_name` | `Soil Moisture 1` | Device name in Home Assistant |
| `stay_awake_entity` | `input_boolean.soil_moisture_1_stay_awake` | Wake-window helper, **one per device** |
| `api_encryption_key` | `!secret soil_1_api_key` | Native API encryption key |
| `ota_password` | `!secret soil_1_ota_password` | OTA password |
| `ap_password` | `!secret soil_1_ap_password` | Fallback hotspot password |

`wifi_ssid` / `wifi_password` are read from the Device Builder's `secrets.yaml`.

### Optional tuning (defaults in the base package)

Override any of these in the device's `substitutions:`.

| Substitution | Default | Meaning |
|---|---|---|
| `threshold_dry` | `20` | Below this % → status *Dry*, red LED |
| `threshold_wet` | `60` | From this % → status *Normal Moisture*, green LED |
| `sleep_dry_min` | `15` | Sleep after a *Dry* reading (min) |
| `sleep_almost_dry_min` | `60` | Sleep after an *Almost Dry* reading (min) |
| `sleep_wet_min` | `480` | Sleep after a *Normal Moisture* reading (min) |
| `sleep_error_min` | `15` | Sleep after an implausible reading (min) |
| `sleep_calibrating_min` | `60` | Sleep while the learned span is too small (min) |
| `wake_budget_min` | `10` | Length of a requested wake window (min) |
| `v_min_plausible` | `0.60` | Readings below (V) are rejected: frontend off / short |
| `v_max_plausible` | `2.95` | Readings above (V) are rejected |
| `min_span` | `0.05` | Learned span (V) needed before a percentage is reported |
| `decay_frac_per_day` | `0.02` | Fraction of the span both limits move inwards per day |
| `confirm_tol` | `0.02` | Tolerance (V) for confirming a new extreme |
| `usb_settle_ms` | `500` | Wait before evaluating USB detection. **Do not remove** |

Anything else can be added or overridden in the device file as usual, for
example `wifi: use_address: 192.168.1.50`.

### Languages

Pick exactly one label file in `files:`:

- `esphome/labels/.soil-moisture-labels-en.yaml`: English
- `esphome/labels/.soil-moisture-labels-de.yaml`: German

The label file sets both the entity names and the status texts (*Dry* /
*Trocken*, …).

> **Changing the language of an existing device creates new entities.**
> ESPHome derives the entity's unique id from its name, so after a language
> switch Home Assistant gets new entities, and the old ones lose their history.
> Choose the language when you set up the device.

## Entities

| Entity (en) | Entity (de) | Type | Notes |
|---|---|---|---|
| Soil Moisture % | Bodenfeuchte | sensor | 0–100 %, `unknown` while calibrating or on sensor error |
| Soil Status | Bodenstatus | text | Dry / Almost Dry / Normal Moisture / Calibrating / Sensor Error |
| Battery % | Akku | sensor | Eneloop NiMH curve, 1.10 V → 0 %, 1.40 V → 100 % |
| Battery Voltage | Akkuspannung | diagnostic | raw cell voltage |
| Soil Raw Voltage | Sondenspannung (roh) | diagnostic | median of 5×16 ADC samples |
| Cal Dry (learned) | Kalibrierung trocken (gelernt) | diagnostic | learned dry limit (V) |
| Cal Wet (learned) | Kalibrierung feucht (gelernt) | diagnostic | learned wet limit (V) |
| Cal Span | Kalibrierung Hub | diagnostic | dry − wet (V) |
| Next Sleep | Nächste Messung in | diagnostic | chosen sleep duration (min) |
| Power Mode | Stromversorgung | diagnostic | USB / battery |
| Sleep Decision | Schlafentscheidung | diagnostic | why it sleeps or stays awake |
| Disable Deep Sleep | Deep Sleep deaktivieren | switch | latching "stay awake", survives deep sleep |
| Reset Calibration | Kalibrierung zurücksetzen | button | discard learned range |

The web interface is available at `http://<name>.local/` while the device is awake.

## Operating modes

The device decides on **every boot** how to behave. The rules are checked in this order:

| Detected | Behaviour |
|---|---|
| USB host connected | No deep sleep. Re-measures every 60 s, logs and OTA available. |
| *Disable Deep Sleep* switch on | Stays awake on battery too (latching, until switched off). |
| Stay-awake helper on in HA | **One-time wake window** of `wake_budget_min` on the next wake-up. |
| Otherwise | Measure, then deep sleep for a moisture-dependent duration. |

A charger or power bank without data lines counts as "no USB". USB detection
looks for USB SOF packets, which only a real host sends.

### Dynamic sleep

| Moisture | Status | LED | Sleep |
|---|---|---|---|
| < 20 % | Dry | red | 15 min |
| 20–60 % | Almost Dry | yellow | 1 h |
| ≥ 60 % | Normal Moisture | green | 8 h |
| span < `min_span` | Calibrating | yellow | 1 h |
| implausible | Sensor Error | red | 15 min |

### Requesting a wake window (the mailbox)

**A sleeping ESP32 cannot be reached.** In deep sleep, Wi-Fi and the API server
are completely off. Home Assistant then logs something like
`Authenticated connection not ready yet … ConnectionState.HOST_RESOLVED`. This is not an error, the device is simply asleep.

So the direction is reversed. The device **fetches** the wish when it wakes up:

1. Switch on the device's `input_boolean.…_stay_awake` in HA at any time,
   even while the device sleeps.
2. On its next regular wake-up the device sees it and stays awake for
   `wake_budget_min` minutes (default 10).
3. Flash OTA, read logs, change settings.
4. The device switches the helper off again, so each request is one-time.

Two safety nets:

- **The time window decides, not the flag.** When the window expires the
  device sleeps even if the helper is still on. A forgotten helper costs one
  window per wake-up, not the whole battery.
- **No Home Assistant → sleep.** If HA is unreachable or the helper does not
  exist, the request is *unknown*, and the device sleeps.

## Calibration

Instead of a manual min/max calibration, the device remembers the driest and
wettest confirmed reading. Naive min/max has three traps, and each one is handled:

1. **Min/max only ever grows.** One outlier would widen the range forever.
   → A time-based, relative **decay** moves both limits inwards by
   `decay_frac_per_day` of the span per day.
2. **Readings outside the soil corrupt the extremes.**
   → Readings outside `v_min_plausible … v_max_plausible` are rejected. A new
   extreme is only accepted after a **second reading** confirms it (± `confirm_tol`).
3. **Every measurement is its own boot** because of deep sleep.
   → Everything that must survive between measurements is stored in NVS.

**The range is seeded, not guessed.** The first plausible reading sets
dry = wet = reading, and the limits then move apart. Until the span reaches
`min_span`, the device reports `unknown` with the status
`Calibrating (0.002/0.05 V)`. That is expected: the soil has to dry out and be
watered once. After a full cycle the whole 0–100 % scale is used.

Measured on a real device: probe in air 2.38 V, moist pot 2.21–2.24 V, learned
spans of 0.18–0.40 V. **Wet = lower voltage.** The span is much smaller than
the Seeed wiki values (2.75 / 1.2 V) suggest. Guessed factory values would
compress the scale to a few percent. That is why they are not used.

> **Limitation:** Air (2.38 V) is *inside* the plausible window. The sensor cannot detect "probe not in soil" at the dry end.
> It is learned as dry (0 %). Only the lower limit reliably catches a dead analog frontend (≈ 0 V).

**Reset**: press the button 3× quickly (blinks green twice) or press
*Reset Calibration* in HA. The next reading seeds again.

## Push button

- **1× short**: measure now
- **3× short**: discard learned calibration, then blink green twice

## Hardware

- **Board:** Seeed XIAO ESP32-C6 (native USB-Serial/JTAG), ESP-IDF framework
- **Power:** 1× AA Eneloop (NiMH, 1.2 V nominal)

| Pin | Function |
|---|---|
| GPIO1 | Soil moisture ADC |
| GPIO0 | Battery ADC |
| GPIO2 | Push button (pull-up, inverted) |
| GPIO18 / 19 / 20 | LED yellow / green / red |
| **GPIO21** | **200 kHz PWM @ 68 %: excitation of the capacitive probe** |
| **GPIO14** | **Power enable of the analog frontend (must be ON)** |
| **GPIO3** | **Analog frontend switch (must be OFF)** |

Without GPIO21/14/3 the probe ADC reads a constant ~0.002 V and the battery ADC reads 0 V.
GPIO14 also powers the battery measurement.

> A battery voltage measured while on USB is an open-circuit voltage. Under
> Wi-Fi load on battery it will read lower.

## Repository layout

```
esphome/
  .soil-moisture.base.yaml             shared firmware (the package)
  labels/.soil-moisture-labels-en.yaml English entity names and states
  labels/.soil-moisture-labels-de.yaml German entity names and states
  example.yaml                         device file for the Device Builder
homeassistant/
  soil_moisture_helpers.yaml           input_boolean helpers (one per device)
tests/
  soil-test-en.yaml, soil-test-de.yaml local-include configs for CI / local builds
  secrets.yaml                         dummy secrets for those configs
  check_labels.py                      label consistency check
requirements.txt                       pinned ESPHome version
CLAUDE.md                              design decisions and maintenance notes
```

## Development

```bash
pip install -U esphome      # always develop against the newest ESPHome release
python tests/check_labels.py
esphome config tests/soil-test-en.yaml
esphome compile tests/soil-test-en.yaml
```

CI runs the same steps for both languages on every push and pull request.
Each language is built twice: with the ESPHome version pinned in
`requirements.txt` and with the newest release from PyPI. A weekly scheduled
run catches breaking ESPHome releases. Dependabot raises the pin with a pull
request whenever a new ESPHome version appears.

On **Windows**, ESP-IDF build paths can exceed the 250-character limit when the checkout is deep.
Point the build directory to a short path, and compile from PowerShell or cmd, not from Git Bash.
ESPHome's ESP-IDF installer refuses to run under MSYS/MinGW:

```powershell
$env:ESPHOME_DATA_DIR = "C:\Daten\.esph"
esphome compile tests/soil-test-en.yaml
```

The test configs contain dummy credentials. Do not flash them to a real device.

## Credits

Based on the ESPHome example from the
[Seeed Studio wiki](https://wiki.seeedstudio.com/xiao_soil_moisture_sensor/).
It was reworked substantially: analog frontend init, working LEDs and button,
USB detection, self-learning calibration, bounded wake windows. The reasons are in
[CLAUDE.md](CLAUDE.md#history-bugs-fixed-in-the-seeed-original).
