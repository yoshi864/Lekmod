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

LekMod v35.4 was tested on an Apple Silicon Mac against a Windows 11 PC over LAN: Lekmap Pangaea, LekMod civs, 15 turns.

- No desyncs.
- All 4,685 synchronised random numbers were identical on both machines.
- The game database built from LekMod's XML and SQL was identical on both machines.

The stock Firaxis game core built the same way also matched an unmodified Windows game exactly.

## Is this AI-made?

Yes. Yoshi Hemzal set the strategy for the reverse engineering, the comparisons between the game versions, and the test setup, and did the multiplayer testing on two machines. [Claude](https://claude.ai) (Anthropic) carried out that strategy and wrote the code and tests.
