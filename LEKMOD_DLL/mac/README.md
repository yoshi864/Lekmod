# LekMod on macOS

This folder builds LekMod's game core for the Mac version of Civilization V (Aspyr, from Steam) and installs LekMod there. Mac players can then play LekMod games with Windows players.

The Windows sources aren't forked or rewritten. The build compiles the same `CvGameCoreDLL_Expansion2` sources the Windows build uses. A few incompatibilities are handled at build time, in `compat/`.

## Installing (Mac players)

You need:

- Civilization V from Steam on macOS (Aspyr 1.4.2, build 180925), with Brave New World. Apple Silicon and Intel Macs both work.
- Apple's command line tools, for `python3` and the compiler. Run `xcode-select --install` once if you don't have them.
- To play with Windows players, the [Civ5 Crossplay Fix](https://github.com/yoshi864/civ5-crossplay-fix).

Then, in Terminal, with the game closed:

```sh
git clone --depth 1 https://github.com/EnormousApplePie/Lekmod.git
cd Lekmod
python3 LEKMOD_DLL/mac/build.py        # about a minute
python3 LEKMOD_DLL/mac/install.py      # add --eui if you use EUI
```

This installs LekMod into `Assets/DLC` and Lekmap into `Assets/Maps`, inside the app bundle. It's the same layout the Windows installer produces.

To update, pull the new version and run both commands again.

To remove LekMod and put back Aspyr's original game core:

```sh
python3 LEKMOD_DLL/mac/install.py --uninstall
```

## How it works

**Loading.** The Mac executable only loads the game core bundled in the app (`Contents/MacOS/libCvGameCoreDLL_Expansion2_DLL.dylib`). It can't load one from a DLC folder the way Windows does. So `install.py` replaces the bundled game core and keeps a backup of Aspyr's original. On Windows, LekMod's DLL runs whenever LekMod is installed, because DLC folders are always active, so the behaviour is the same.

**Compiling.** Aspyr compiled the game with clang for 64-bit macOS, while LekMod is written for 32-bit MSVC 2008. `build.py` copies the sources to `build/stage`, applies `compat/fixups.py` and compiles them with clang in MSVC-compatibility mode. Every source file includes `compat/prelude.h` before anything else.

What the compat layer handles:

| Area | Problem | Fix |
|---|---|---|
| Windows APIs | The headers aren't available on macOS | `compat/*.h` provide the small part the game core uses |
| Integer sizes | Windows `long` is 32-bit and macOS `long` is 64-bit. Random seeds, saves and network data depend on the Windows size | `long` becomes `int` in game core code (fixups `llp64-*`) |
| Sorting | `std::sort` orders equal elements differently in each standard library, which desyncs multiplayer | MSVC 2008's algorithm is used instead (`compat/msvc_sort.h`) |
| Floating point | Some compiler optimisations change results | They're turned off to match MSVC (`-ffp-contract=off`, `-fwrapv`) |
| Aspyr's object layouts | The game executable and game core share some objects | Their layouts are rebuilt to match Aspyr's, including one extra interface method Aspyr added (`compat/aspyr_abi.cpp`, `compat/abi_checks.cpp`) |
| MSVC-only C++ | Code that MSVC 2008 accepted but clang rejects, mostly in Firaxis' FireWorks headers | Exact-text fixups, listed with reasons in `compat/fixups.py` |

Every fixup states how many times it must match. If a LekMod change moves the code a fixup expects, the build stops and names the fixup, instead of quietly skipping it.

**Checking.** After linking, `build.py` checks the result against Aspyr's binaries using files in `reference/`, so CI doesn't need the game:

- Every engine symbol the game core imports must be one the executable exports (`aspyr_exe_exports.txt`).
- Every class the executable calls into must have the same number of virtual functions as in Aspyr's game core (`aspyr_vtables.json`, made with `vtables.py --dump`). A mismatch would send calls to the wrong function.

Aspyr's final Mac release won't change, so these files don't need updating.

**Lua.** Aspyr's `Network.HttpRequest` crashes the game. The installer writes `Lua/Utilities/LekmodPlatform.lua`, and `LekmodVersion.IsMac()` reads it so the main menu skips the online version check.

## CI

`.github/workflows/mac.yaml` builds and checks the game core on a macOS runner whenever `LEKMOD_DLL` changes. The dylib is uploaded as an artifact.

## Testing

### How we test

The goal is a Mac game core that plays **exactly** like the Windows DLL, since multiplayer only works if both sides compute the same game. So we don't test by playing and watching for desyncs; we make both machines play the same AI-only game and compare everything they compute.

- **Machines.** An Apple Silicon Mac running this build, and a Windows machine (a Windows 11 PC, later a Windows 11 VM) running LekMod's Windows DLL. The Windows DLL is either the shipped v35.4 DLL or one built by LekMod's own CI from the same commit as the Mac build.
- **Harness.** A small Lua harness is added to the test installs only (hooked into the main menu and `InGame.lua`). It sets up a game from a config (map script, size, speed, era, difficulty, civs, city-states, options, seed) and hands every seat to the AI (`Game.SetAIAutoPlay`, with a reserved observer slot). It plays N turns, then quits. Map and sync seeds are fixed (`MapRandSeed`/`SyncRandSeed` in `config.ini`).
- **What we compare, per game:**
  - **Every synchronised random number.** With `RandLog=5`, the game writes each sync roll to `RandCalls.csv`: turn, slice, range, value and the reason string ("AI Patrol", "Grand Strategy AI: GS rand roll." and so on). Any difference in game logic shows up here within a turn or two, and the reason string names the code.
  - **A snapshot per player per turn.** Score, gold and gold per turn, science, culture, faith, techs, policies, happiness, military might, city and unit counts, and hashes of every unit (type, position, damage) and every city (position, population, food and production stored).
- **Diagnosing a divergence.** We replay the game on both machines with detail logging. That adds every unit's ID, position, moves, activity, AI type and damage, every city's yields, and each player's gold breakdown, every turn. Where needed we add LekMod's AI logs too. The first differing line usually points at one function.
- **Crashes** are diagnosed from Windows minidumps (symbolised with the shipped PDB), from macOS crash reports, and by replaying the game deterministically under lldb.
- **Mac-only memory bugs** are found by building the Mac core with stack and heap poisoning (`-ftrivial-auto-var-init=pattern`, freshly allocated memory filled with a pattern). That turns "reads garbage" into a reproducible difference, which we then bisect by source file and by variable.

### Test matrices

- **Matrix-50 (quick games):** 25 games covering all 114 LekMod civs (each twice) and every Lekmap map script, at multiplayer settings.
- **Deity matrix (long games):** the same 25 games at Deity, played to the late game. That's 220 to 400 turns, up to 21 civs plus city-states on Huge maps, and about 1,000 units at peak. These games exercise far more AI and late-game code, and take 1 to 5 hours each.

## Status (2026-11-25)

- **Matrix-50:** 24 of 25 games identical on Mac and Windows: every snapshot and every sync roll, over 600,000 rolls in all. The 25th (g05) differs because of a Windows-side bug: the Windows DLL itself gives different results for that game depending on stack layout (see `bRandPassed` below). The Mac matches one of the two Windows outcomes.
- **Deity matrix (Mac build vs Windows CI DLL, both from `17401c1`):**
  - **Identical, end to end (17 games):** g01, g03, g05, g07, g08, g09, g13, g14, g15, g17, g18, g19, g20, g21, g22, g23, g24. The largest are over a million sync rolls each.
  - **Identical up to a crash (4 games):**
    - g16 hit the build-queue bug on both machines (fixed since: `a48f973`).
    - g11 hit the airlift-city crash on the Mac (fixed since: `fc8a139`).
    - g02 and g12 hit a Mac-only crash inside Aspyr's executable (under investigation, below).
  - **Diverged (1 game):** g25 at turn 181, from an uninitialised read on the Windows side. Fixed since (`5f5cd1b`, below): with the fix, g25 is identical on both machines (2,581 snapshots, 200,271 sync rolls, through turn 186).
  - **Also identical up to a stop:**
    - g06 matched for 1.17 million sync rolls, up to a silent Mac exit at turn 291. It didn't reproduce on replay, which played straight past.
    - g04 matched for 583,000 rolls, up to a silent Windows exit at turn 169 (old DLL, no crash dump). That's probably the build-queue bug, which the Mac build already had fixed.
  - **Not compared:** g10 never launched on the Mac ("Failed to Load database").

## What testing has found

### Bugs in LekMod (all platforms), fixed on this branch

| Commit | Bug | Effect |
|---|---|---|
| `18be0f7` | `CvPlayerCulture::GetInfluencePerTurn` uses the capital without checking for one | Crash at end of turn when a player has no capital (turn 0 on crowded maps, or after losing it) |
| `fc8a139` | Same pattern in `IsTestCityStrategy_GoodAirliftCity`, and in goody-hut distances to city-state capitals | Crash in long games once a civ survives losing its capital |
| `a48f973` | `CvCity::popOrder` deletes its order after the completion work, which can empty or move the queue; the delete then wraps the queue size from 0 to 0xFFFFFFFF | Crash in `pushOrder`/`popOrder` on Windows, crash or hang on the Mac, in AI Deity games past turn ~170 |
| `623ff98` | `CvGameTrade::CreateTradeRoute` adds a route whose yields aren't initialised, and they're read before being set | One-turn garbage gold (for example -1,071,000 gold per turn), different on every machine. This was the main cause of Deity divergences. |
| `7cababc` | `CvDiplomacyAI::DoRequest` reads an uninitialised `bRandPassed` | Phantom failed diplomacy requests. Depends on stack layout, so two **Windows** players can desync here too. |
| `590fba6` | `m_CurrentIndex = m_CurrentIndex++` (unsequenced) in city specialization | MSVC advances the index and clang doesn't, so every production subtype becomes Military Training on other compilers |
| `4980990` | `m_bCanChooseReformationBelief` not reset in `CvPlayer::reset()` | A free Reformation belief from leftover memory |
| `349f377` | Dangling `const char*` from temporary `CvString`s (Great People names, state religion name, Lua `GetScriptData`) | Garbage or empty Great People names, wrong Great Works, crashes when logging |
| `826af6a` | `viApproachWeights[NO_MINOR_CIV_APPROACH]` (index -1) in `GetBestApproachTowardsMinorCiv` | Harmless out-of-bounds read on 32-bit Windows; crash on 64-bit |
| `2765ffc`, `4420656` | `getTechInfo(NO_TECH)` from `CvUnit::upgradePrice`, and other unchecked info getters | Same pattern: a harmless read at index -1 on Win32, a crash on 64-bit |
| `db7c08b` | New Zealand Lua passes `GetOverflowResearch()` as a tech ID | Out-of-bounds write and crash when nothing is being researched |
| `5f5cd1b` | `CvCityStrategyAI`'s yield deltas are only initialised under `AUI_WARNING_FIXES` (off), and only computed at the start of worker tasking | For a city captured or founded that turn, `ScorePlot` weighs worker builds with heap garbage, so workers choose differently on every machine. Found as g25's divergence: a worker's oil well scored 4× higher on the Mac (zeros) than on Windows (garbage) right after Palmyra captured Edessa. |

### Differences between MSVC 2008 and clang, fixed in the Mac build

| Commit | Difference | Fix |
|---|---|---|
| `a6d6a92` | MSVC 2008's x87 code keeps float intermediates in double precision | `-ffp-eval-method=double` plus a few casts |
| `bd0c55e` | MSVC picks `<cmath>`'s float overloads and rounds their arguments to float | Fixups that round those arguments the same way |
| `7bb1795` | Members never initialised by constructors | A zero-filling `operator new` for the game core, so they start at 0 every time |
| `16e8a18`, `17401c1` | Reads at index -1 that 32-bit Windows tolerates | Mac reads what Windows reads |
| `dfe6be6` | The executable's net-message debug formatter crashes on `%` in names | Net-message debug text kept away from it |

Two Lekmap issues also turned up, not fixed here:
- `LekmapPangaeaFractalv6.3.lua` and `LekmapPangaeaRectangularv4.lua` never finish generating at Huge size. They only accept a map whose biggest landmass holds all the land.
- `LekmapTeamerMapLegacy.lua` includes `HBMapGeneratorMirrored`/`HBFeatureGeneratorMirrored`, which aren't shipped, so it fails to load on both platforms.

## What we're working on

- **Mac-only crash in Aspyr's executable (g02, g12; possibly g06).** This is the last known Mac-only crash. The game state is identical to Windows right up to it.
  - It happens in the Mac executable's unit-graphics code, which reacts to the game core's unit events.
  - A unit's animated model (`FGrannyAssetInstance`) is alive and valid, but one pointer in its list of sub-objects (state machines) is off by 2 bytes, so the next virtual call through it crashes.
  - The list's storage is in the engine's own memory pool. The crash reproduces exactly on replay (g12, turn 169), so we're catching the write that corrupts it with a hardware watchpoint.
  - It can't be fixed in LekMod's code unless the game core turns out to trigger it. Otherwise the fix would be a small patch to the Mac executable, like the existing Crossplay Fix patch.
- **Mac launch failure** ("Failed to Load database"): occasionally a game won't start on the Mac, even with a fresh database cache. It isn't tied to the game setup: g10, which failed three times in the matrix, launched first time when retried.
- **Next matrix:** a full Deity rerun with a fresh CI Windows DLL and Mac build from the same commit, including every fix above.

The test harness and tools (`suite.py`, the Lua harness, matrix generator, poison builds and bisection) live in a separate repository for now. They can be added here if that's useful.

## Is this AI-made?

Yes. Yoshi Hemzal set the strategy for the reverse engineering, the comparisons between the game versions, and the test setup, and did the multiplayer testing on two machines. [Claude](https://claude.ai) (Anthropic) carried out that strategy and wrote the code and tests.
