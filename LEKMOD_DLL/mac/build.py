#!/usr/bin/env python3
"""Build LekMod's game core (LEKMOD_DLL/CvGameCoreDLL_Expansion2) as a macOS dylib.

    python3 LEKMOD_DLL/mac/build.py [--out LEKMOD_DLL/mac/build]

The sources are staged into <out>/stage with the fixups from compat/fixups.py applied,
compiled with the headers in compat/ force-included, and linked so that engine symbols
resolve from the game executable at load time. The result is then checked against
Aspyr's binaries, using data in reference/ so no game install is needed:
- every symbol it imports must be one the executable exports;
- every C++ class the executable calls into must have the same vtable size.
"""
import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys

MAC = os.path.dirname(os.path.abspath(__file__))
COMPAT = os.path.join(MAC, "compat")
REFERENCE = os.path.join(MAC, "reference")
LEKMOD_DLL = os.path.dirname(MAC)
PROJECT = "CvGameCoreDLL_Expansion2"

INCLUDE_DIRS = [
    "CvWorldBuilderMap/include", "CvGameCoreDLLUtil/include", "CvLocalization/include",
    "CvGameDatabase/include", "FirePlace/include", "FirePlace/include/FireWorks",
    "ThirdPartyLibs/Lua51/include",
]
DEFINES = ["WIN32", "_WINDOWS", "FXS_IS_DLL", "NDEBUG", "FINAL_RELEASE", "CVGAMECOREDLL_EXPORTS", "_CRT_SECURE_NO_WARNINGS"]
CXXFLAGS = [
    "-target", "x86_64-apple-macos10.13", "-std=gnu++11", "-O2", "-fPIC",
    "-fvisibility=hidden", "-fvisibility-inlines-hidden",
    "-fms-extensions", "-fms-compatibility", "-fms-compatibility-version=19.00",
    # ms-compat drops the GNU macros macOS headers key on (va_list!) and defines _MSC_VER,
    # which would send SDK headers down MSVC-only paths (inline __asm etc.).
    "-D__GNUC__=4", "-D__GNUC_MINOR__=2", "-D__GNUC_PATCHLEVEL__=1", "-U_MSC_VER", "-U_MSC_FULL_VER", "-U_MSC_BUILD",
    "-fdelayed-template-parsing",
    # Determinism: MSVC never exploits signed overflow or aliasing; match it, and
    # never fuse or reassociate floating point (Aspyr's reference build is plain SSE).
    "-fwrapv", "-fno-strict-aliasing", "-ffp-contract=off",
    # MSVC 2008's x87 code evaluates float expressions in double precision and rounds only
    # on assignment, cast, argument and return; SSE would round every float operation.
    "-ffp-eval-method=double",
    # MSVC accepts these; keep its behaviour rather than editing the sources.
    "-Wno-invalid-token-paste", "-fallow-editor-placeholders", "-Wno-c++11-narrowing",
    "-w", "-ferror-limit=0",
]


def stage(src, out):
    sys.path.insert(0, COMPAT)
    import fixups
    dst = os.path.join(out, "stage")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    windows_only = shutil.ignore_patterns(".git", "BuildOutput", "BuildTemp", "*.dll", "*.pdb", "*.lib")
    # Not this folder: it holds the build output.
    shutil.copytree(src, dst, ignore=lambda d, names: set(windows_only(d, names)) | ({"mac"} if d == src else set()))
    fixups.apply(dst)
    return dst


def sources(tree):
    proj = os.path.join(tree, PROJECT)
    vcx = sorted(f for f in os.listdir(proj) if f.endswith(".vcxproj"))[-1]
    text = open(os.path.join(proj, vcx), encoding="utf-8", errors="replace").read()
    files = [f.replace("\\", "/") for f in re.findall(r'ClCompile Include="([^"]+\.cpp)"', text)]
    return [f for f in files if f != "_precompile.cpp"]


def compile_one(tree, objdir, rel):
    proj = os.path.join(tree, PROJECT)
    name = "compat_" + os.path.basename(rel) if os.path.isabs(rel) else rel.replace("/", "_")
    obj = os.path.join(objdir, name[:-4] + ".o")
    cmd = ["clang++", *CXXFLAGS, "-include", os.path.join(COMPAT, "prelude.h"), "-I", COMPAT]
    # Reproducible output: __FILE__ strings must not depend on the output directory.
    cmd += ["-ffile-prefix-map=" + os.path.abspath(tree) + "=.", "-ffile-prefix-map=" + MAC + "=."]
    # LekMod nests Firaxis' shared libraries inside the project.
    cmd += ["-I" + os.path.join(proj, d) for d in INCLUDE_DIRS] + ["-I" + proj, "-I" + os.path.join(proj, "Lua")]
    cmd += ["-D" + d for d in DEFINES] + ["-c", os.path.join(proj, rel), "-o", obj]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    return rel, obj, r.returncode, r.stderr


def exe_exports():
    """nm -gU of Aspyr's executable (Civilization V.app/Contents/MacOS/Civilization V, 1.4.2 build 180925)."""
    return set(open(os.path.join(REFERENCE, "aspyr_exe_exports.txt")).read().split())


def verify(dylib):
    ours = subprocess.run(["nm", "-gU", dylib], capture_output=True, text=True).stdout.split()
    if "_DllGetGameContext" not in ours:
        print("ERROR: _DllGetGameContext is not exported")
        return False
    exports = exe_exports()
    und = subprocess.run(["nm", "-u", dylib], capture_output=True, text=True).stdout.split()
    runtime = re.compile(r"^(__ZNSt3__1|__ZNKSt3__1|__ZTVNSt3__1|__ZTINSt3__1|__ZSt|__ZNSt|__ZTVSt|__ZTISt|__ZTv0_n24_NSt3__1|"
                         r"__Znw|__Zna|__Zdl|__Zda|__ZTVN10__cxxabiv|__ZTI[a-z]$|___cxa|___gxx|__Unwind|___stack_chk|"
                         r"dyld_stub_binder|_[a-z_][a-z0-9_]*$)")
    missing = [s for s in und if s not in exports and not runtime.match(s)]
    print(f"undefined symbols: {len(und)}; resolved by exe: {sum(s in exports for s in und)}; "
          f"unresolved (not exe, not C/C++ runtime): {len(missing)}")
    for s in missing:
        dm = subprocess.run(["c++filt", s], capture_output=True, text=True).stdout.strip()
        print("   ", s, " ", dm)
    if missing:
        return False
    sys.path.insert(0, MAC)
    import vtables
    return vtables.compare(os.path.join(REFERENCE, "aspyr_vtables.json"), dylib) == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=LEKMOD_DLL, help="folder containing CvGameCoreDLL_Expansion2/")
    ap.add_argument("--out", default=os.path.join(MAC, "build"))
    ap.add_argument("--only", nargs="*", help="compile just these sources (relative paths)")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    ap.add_argument("--no-stage", action="store_true", help="reuse existing stage dir")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    tree = os.path.join(a.out, "stage") if a.no_stage else stage(os.path.abspath(a.src), a.out)
    objdir = os.path.join(a.out, "obj")
    os.makedirs(objdir, exist_ok=True)
    files = a.only or sources(tree)

    # Our own glue (e.g. DllMain driver) is compiled alongside the game core sources.
    glue = [] if a.only else sorted(os.path.join(COMPAT, f) for f in os.listdir(COMPAT) if f.endswith(".cpp"))
    failed, objs = {}, []
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex:
        for rel, obj, rc, err in ex.map(lambda f: compile_one(tree, objdir, f), files + glue):
            if rc:
                failed[rel] = err
            else:
                objs.append(obj)
    log = os.path.join(a.out, "errors.log")
    with open(log, "w") as fh:
        for rel, err in sorted(failed.items()):
            fh.write(f"==== {rel}\n{err}\n")
    errors = [l for e in failed.values() for l in e.splitlines() if " error: " in l]
    print(f"compiled {len(objs)}/{len(files) + len(glue)}; failed {len(failed)}; error lines {len(errors)} -> {log}")
    if failed or a.only:
        return 1 if failed else 0

    dylib = os.path.join(a.out, "libCvGameCoreDLL_Expansion2_DLL.dylib")
    expfile = os.path.join(a.out, "exports.txt")
    open(expfile, "w").write("_DllGetGameContext\n")
    link = ["clang++", "-target", "x86_64-apple-macos10.13", "-dynamiclib", "-o", dylib, *objs,
            "-install_name", "/libCvGameCoreDLL_Expansion2_DLL.dylib",
            "-Wl,-undefined,dynamic_lookup", "-Wl,-exported_symbols_list," + expfile]
    r = subprocess.run(link, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr)
        return 1
    print("linked", dylib)
    return 0 if verify(dylib) else 2


if __name__ == "__main__":
    sys.exit(main())
