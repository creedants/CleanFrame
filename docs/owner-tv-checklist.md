# Owner TV checklist

Read these four values off your Samsung The Frame before any setup work. Reading them needs only the TV and its remote. No computer connects to the TV at this step.

Record the real values only in your private setup record under ignored `.local/`. Never write them into this file or any committed file. The placeholders below show the shape of each entry.

## Checklist

1. **Model code.** Open **Settings → Support → About This TV**. Copy the full model code exactly as shown, including size, series and region characters. Record it as `<MODEL_CODE>`.
2. **Firmware (software) version.** On the same **About This TV** screen, copy the complete software version string, not only its trailing number. Record it as `<FIRMWARE_STRING>`.
3. **Tizen version.** The repository docs name no TV menu that shows it. If **About This TV** lists a Tizen or OS version, copy it as `<TIZEN_VERSION>`; this is unverified general guidance. Otherwise leave it blank. On the reference TV it was confirmed only from the developer connection's capability report and a native probe, which come later, in an authorised device stage.
4. **Developer Mode.** Open **Home → Apps → App Settings**, then enter **1, 2, 3, 4, 5** on the remote's number pad (its **123** button). The Developer Mode popup shows whether it is On and which **Host PC IP** it trusts. Record `<DEV_MODE_ON_OR_OFF>`. If it is On, check whether the Host PC IP is the local address of the computer you will set up from, and record only yes or no here. Change nothing in the popup at this step.

If a menu path differs on your model year, follow the closest matching labels, then send your agent a cropped photo of the screen or type the visible labels. The setup guide says menu wording can vary and asks for that fallback ([setup guide, Stage 1 and Stage 2](agent-tv-setup-guide.md)). Crop out serial numbers and account details.

Sources for the menu paths: About This TV is in the setup guide's Stage 1 (`docs/agent-tv-setup-guide.md:77`). App Settings and the 12345 popup are in Stage 2 (`docs/agent-tv-setup-guide.md:96-99`). The docs give no menu path for the Tizen version.

## What the reference status covers

`docs/tv-status.md` records one TV: a 55-inch The Frame, model code QA55LS03DAWXXY (LS03D), firmware 2130.0 (string T-PTMDUABC-0090-2130.0), Tizen 9.0.0 on 32-bit ARMv7, with Developer Mode enabled. It also records the SDK user UID 901 and a .NET 6 runtime with the required native libraries. It states that other models, firmware and operating systems need their own checks. The setup guide adds that matching the model alone does not establish compatibility (`docs/agent-tv-setup-guide.md:23`).

Those results describe that one configuration. If your model code, full firmware string or Tizen version differs, none of the recorded results carries over, and each needs its own check. A full match is still not proof that your TV behaves the same. It satisfies only the helper's model and firmware guards. The helper also checks the process architecture, the SDK user, the saved original values and, before apply, that the installed app is eligible for boot (`scripts/native-home/Control.cs:34-43`). You would also still need your own app identity and certificates.

## Which reference assumptions each value affects

The scripts are written for the reference TV. These are the lines that depend on each checklist value. The model, firmware and Developer Mode rows follow directly from the code or the setup guide. The rows marked Tizen version (inferred) are runtime and platform assumptions that the code does not tie to any version number. Grouping them under the Tizen version is this checklist's inference, since `docs/tv-status.md` confirms them together with Tizen 9.0.0 on the reference TV.

| Value | Assumption | Location |
| --- | --- | --- |
| Model code | Native Home runner reads the model from the TV's information endpoint on port 8001 before any SDB step; a working SDB connection alone does not satisfy this | `scripts/native-home/run.py:7`, `docs/agent-tv-setup-guide.md:118` |
| Model code | Native Home runner refuses unless the TV reports model QA55LS03DAWXXY | `scripts/native-home/run.py:8` |
| Model code | Inspect probe reads the model and firmware version from the TV's product file | `scripts/native-home/inspect.sh:5` |
| Firmware | Helper refuses any firmware string other than T-PTMDUABC-0090-2130.0 | `scripts/native-home/Control.cs:35` |
| Firmware | Helper notes scope it to firmware 2130.0 | `scripts/native-home/README.md:3` |
| Firmware | Runner uses the package-name command workaround and a 400-byte command limit reviewed on this firmware | `scripts/native-home/run.py:30-32` |
| Firmware | Native Home operation and vconf keys the helper reads and writes | `scripts/native-home/Control.cs:7`, `scripts/native-home/Control.cs:9-10` |
| Firmware | Native library names the helper calls | `scripts/native-home/Control.cs:11-22` |
| Tizen version (inferred) | Helper requires a 32-bit process running as SDK user UID 901 | `scripts/native-home/Control.cs:34` |
| Tizen version (inferred) | Helper targets .NET 6 | `scripts/native-home/Control.csproj:1` |
| Tizen version (inferred) | Shell steps call `/usr/bin/dotnet` on the TV | `scripts/native-home/apply.sh:3`, `scripts/native-home/query.sh:3`, `scripts/native-home/restore.sh:3` |
| Tizen version | Inspect probe reads the Tizen release file | `scripts/native-home/inspect.sh:6` |
| Tizen version (inferred) | Inspect probe reads the user, architecture, .NET runtimes and native libraries | `scripts/native-home/inspect.sh:3-4`, `scripts/native-home/inspect.sh:7-8`, `scripts/native-home/inspect.sh:11-12` |
| Tizen version (inferred) | Files are staged in `/home/owner/share/tmp/sdk_tools/` | `scripts/tv.py:54`, `scripts/native-home/run.py:18-22` |
| Tizen version (inferred) | Install, launch and app-list use the TV shell commands `vd_appinstall`, `execute` and `applist` | `scripts/tv.py:58`, `scripts/tv.py:46`, `scripts/tv.py:61` |
| Tizen version (inferred) | Runner's callback relies on Bash `/dev/tcp`; inspect relies on `vconftool` | `scripts/native-home/run.py:27-30`, `scripts/native-home/inspect.sh:10` |
| Developer Mode | SDB connects to the TV on port 26101 | `scripts/tv.py:39`, `scripts/native-home/run.py:9` |
| Developer Mode | `info` reports the developer capability, which is where the Tizen version is confirmed | `scripts/tv.py:44` |
| Developer Mode | Host PC IP in the Developer Mode popup must be the local address of the computer that runs the scripts | `docs/agent-tv-setup-guide.md:83`, `docs/agent-tv-setup-guide.md:99` |

The docs do not say which of the firmware and Tizen rows change with a Tizen release and which change with a firmware update. Treat every native Home row as needing a new check after any firmware update (`docs/agent-tv-setup-guide.md:285`).

## Assumptions not read off the TV

These depend on none of the four values. Your agent sets them up on the computer or reads them from the project.

- Signing and SDK paths. Packaging expects a workspace-local Tizen SDK on macOS, private certificates and `profiles.xml`, and a hard-coded reference signing profile name that your own profile replaces (`scripts/package.py:1`, `scripts/package.py:14-15`, `scripts/package.py:28`, `scripts/package.py:45`). The distributor certificate includes the TV's unique device ID (`docs/agent-tv-setup-guide.md:135`), which is a separate value from the model code (`docs/agent-tv-setup-guide.md:144`).
- App identity. The helper targets the reference app `nClrkHome1.FrameHome` and checks for its install folder (`scripts/native-home/Control.cs:8`, `scripts/native-home/Control.cs:43`). `scripts/tv.py` reads the app ID from `app/config.xml` (`scripts/tv.py:26`). An identity change also updates the manifest, the assertions in `scripts/check.py` and the launch/self-filter IDs.
- Callback route. The native Home runner opens a listener on the computer's address on the route to the TV, and accepts only the TV's address as the caller (`scripts/native-home/run.py:23-27`, `scripts/native-home/run.py:36`).
- TV address. Both device scripts read the TV address from `.local/device.json` (`scripts/tv.py:16-21`, `scripts/native-home/run.py:6`). The address comes from the TV's network settings in a later stage. Keep it out of committed files.

## Next step

After you record these values in `.local/`, your agent compares them with the reference table above and flags every difference. Each device stage after that needs your explicit authorisation, starting with the first developer connection.
