#!/usr/bin/env python3
"""Install LekMod into the Mac (Aspyr, Steam) version of Civilization V.

    python3 LEKMOD_DLL/mac/install.py [--eui] [--dylib <game core>] [--app <Civilization V.app>]
    python3 LEKMOD_DLL/mac/install.py --uninstall

Run it from a checkout of this repository after building the game core
(LEKMOD_DLL/mac/build.py). It lays files out exactly as the Windows installer does, by
running LekmodInstaller/ui_manager.py (the ui_check.bat port, the DLC copy and stamp,
the Lekmap copy) with the app bundle's Contents/Assets as the game folder. Then:

- The Windows binaries are left out of the DLC folder. The Mac executable only loads
  the game core bundled in the app, never one from a DLC folder, so the Mac build
  replaces the bundled one. On Windows a DLC folder is always active, so its game core
  runs whenever LekMod is installed; the same holds here.
- Lua/Utilities/LekmodPlatform.lua tells the Lua code it runs on a Mac (see
  LekmodVersion.IsMac).

Aspyr's game core is backed up first; --uninstall puts it back and removes LekMod.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

MAC = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(MAC))
CORE = "libCvGameCoreDLL_Expansion2_DLL.dylib"
# Aspyr's game core as shipped (1.4.2, build 180925). Only this file is ever backed up.
ASPYR_CORE_SHA256 = "0da6a5ffc283c3f147b20a7ec426e4ed85a6838ab891faf61b50af4e25c4a09c"
BACKUP = os.path.expanduser(f"~/Library/Application Support/LekMod/{CORE}.aspyr")
STEAM = os.path.expanduser("~/Library/Application Support/Steam")
GAME = os.path.join("steamapps", "common", "Sid Meier's Civilization V", "Civilization V.app")
WINDOWS_BINARIES = re.compile(r"\.(dll|pdb|exe|bat)$", re.I)
CROSSPLAY_FIX = "https://github.com/yoshi864/civ5-crossplay-fix"


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def find_app():
    """Civilization V.app in any Steam library."""
    libraries = [STEAM]
    vdf = os.path.join(STEAM, "steamapps", "libraryfolders.vdf")
    if os.path.exists(vdf):
        libraries += re.findall(r'^\s*"path"\s*"(.*)"\s*$', open(vdf, encoding="utf-8").read(), re.M)
    for library in libraries:
        if os.path.isdir(os.path.join(library, GAME)):
            return os.path.join(library, GAME)
    sys.exit("Civilization V not found in your Steam libraries; pass --app \"/path/to/Civilization V.app\"")


def require_game_closed():
    if subprocess.run(["pgrep", "-f", "Civilization V.app/Contents/MacOS/Civilization V"], capture_output=True).returncode == 0:
        sys.exit("Civilization V is running; quit it first.")


def install_core(app, dylib):
    target = os.path.join(app, "Contents", "MacOS", CORE)
    if not os.path.exists(BACKUP):
        if sha256(target) != ASPYR_CORE_SHA256:
            sys.exit(f"{target} is not Aspyr's original and there is no backup of it. Restore it with Steam's "
                     "Properties > Installed Files > Verify integrity, then run this again.")
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        shutil.copy2(target, BACKUP)
        print(f"✓ Backed up Aspyr's game core to {BACKUP}")
    shutil.copy2(dylib, target)
    subprocess.run(["codesign", "--force", "--sign", "-", target], check=True, capture_output=True)
    print(f"✓ Installed LekMod's game core (sha256 {sha256(target)[:16]})")


def restore_core(app):
    target = os.path.join(app, "Contents", "MacOS", CORE)
    if os.path.exists(BACKUP) and sha256(BACKUP) == ASPYR_CORE_SHA256:
        shutil.copy2(BACKUP, target)
        print("✓ Restored Aspyr's game core")
    elif sha256(target) != ASPYR_CORE_SHA256:
        print("! No backup of Aspyr's game core; restore it with Steam's Verify integrity")


def upstream():
    sys.path.insert(0, os.path.join(REPO, "LekmodInstaller"))
    import ui_manager
    return ui_manager.UIManager()


def versions():
    """('v35.4', 'v6.3'): the LekMod version from LEKMOD/VERSION, checked against the
    installer's catalogue, and the Lekmap release listed with it."""
    raw = open(os.path.join(REPO, "LEKMOD", "VERSION")).read().strip()  # e.g. v35.4.003
    lekmod_version = ".".join(raw.split(".")[:2])
    setup = os.path.join(REPO, "LekmodInstaller", "github_setup")
    catalogue = json.load(open(os.path.join(setup, "versions.json")))
    if lekmod_version not in catalogue:
        sys.exit(f"LEKMOD/VERSION says {raw}, but {lekmod_version} is not in versions.json")
    released = catalogue[lekmod_version]["release_date"]
    maps = json.load(open(os.path.join(setup, "lekmap_versions.json")))
    same_day = [k for k, v in maps.items() if v["release_date"] == released]
    lekmap_label = same_day[0] if same_day else next(iter(maps))
    return lekmod_version, lekmap_label.split()[-1]


def remove_previous(m, assets, log):
    m.remove_lekmod_folders(assets, m.find_existing_lekmod_folders(assets), log)
    maps = os.path.join(assets, "Assets", "Maps")
    for name in os.listdir(maps):
        if os.path.isdir(os.path.join(maps, name)) and m._LEKMAP_FOLDER_VERSION_RE.match(name.strip()):
            shutil.rmtree(os.path.join(maps, name))
            log(f"✓ Removed {name} from Maps")


def warn_without_crossplay_fix(app):
    """The Lua rounding patch (see CROSSPLAY_FIX) is what keeps games with Windows players in sync."""
    exe = os.path.join(app, "Contents", "MacOS", "Civilization V")
    with open(exe, "rb") as f:
        f.seek(0xB47645)
        if f.read(1) != b"\x2d":
            print(f"! To play with Windows players, also install the cross-play fix: {CROSSPLAY_FIX}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--eui", action="store_true", help="configure LekMod's UI for EUI (Enhanced User Interface)")
    ap.add_argument("--dylib", default=os.path.join(MAC, "build", CORE), help="the Mac game core (default: build output)")
    ap.add_argument("--app", help="Civilization V.app (default: found in your Steam libraries)")
    ap.add_argument("--uninstall", action="store_true")
    a = ap.parse_args()
    app = a.app or find_app()
    assets = os.path.join(app, "Contents", "Assets")  # the Windows game folder's equivalent
    require_game_closed()
    m = upstream()
    log = print

    if a.uninstall:
        remove_previous(m, assets, log)
        restore_core(app)
        return
    if not os.path.exists(a.dylib):
        sys.exit(f"No game core at {a.dylib}; build it first: python3 LEKMOD_DLL/mac/build.py")

    lekmod_version, lekmap_version = versions()
    print(f"LekMod {lekmod_version}, Lekmap {lekmap_version}")
    with tempfile.TemporaryDirectory() as extract:
        # The installer works on an extracted release: a LEKMOD folder and a Lekmap folder.
        shutil.copytree(os.path.join(REPO, "LEKMOD"), os.path.join(extract, "LEKMOD"),
                        ignore=lambda d, names: [n for n in names if WINDOWS_BINARIES.search(n) and n != "ui_check.bat"])
        shutil.copytree(os.path.join(REPO, "Lekmap"), os.path.join(extract, "Lekmap"))
        remove_previous(m, assets, log)
        m.configure_ui_files(extract, "Enhanced UI (EUI)" if a.eui else "Standard UI", log, civ5_path=assets)
        m.install_mod(extract, assets, lekmod_version, log)
        m.install_lekmap(extract, lekmap_version, log, civ5_path=assets)

    dest = os.path.join(assets, "Assets", "DLC", f"LEKMOD_{lekmod_version}")
    stray = [p for p in glob.glob(os.path.join(dest, "**", "*"), recursive=True) if WINDOWS_BINARIES.search(p)]
    if stray:
        sys.exit(f"Windows binaries left in {dest}: {stray}")
    with open(os.path.join(dest, "Lua", "Utilities", "LekmodPlatform.lua"), "w") as f:
        f.write('LekmodPlatform = "mac"\n')
    install_core(app, a.dylib)
    warn_without_crossplay_fix(app)


if __name__ == "__main__":
    main()
