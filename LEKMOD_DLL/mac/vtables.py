#!/usr/bin/env python3
"""Compare C++ vtable shapes between x86_64 Mach-O dylibs via RTTI (works on stripped binaries).

    vtables.py reference.dylib|reference.json candidate.dylib [ClassNameFilter]
    vtables.py --dump aspyr.dylib out.json

reference/aspyr_vtables.json is the --dump of Aspyr's shipped game core, so builds
can be checked without the game installed.

For every class with typeinfo, finds its vtables ([offset-to-top][typeinfo][fn ...]) and
reports how many function slots each has. The exe calls our interface implementations
(ICvGameContext1, ICvPlayer1, ...) through these slots, so a count mismatch means calls
land in the wrong method. Identical counts do not prove identical order, but every
interface method in this codebase is distinct, so reordering would also change bodies.
"""
import json
import struct
import sys


def load(path):
    data = open(path, "rb").read()
    segs = []  # (vmaddr, vmsize, fileoff, filesize, sections)
    ncmds = struct.unpack_from("<I", data, 16)[0]
    off = 32
    text = (0, 0)
    for _ in range(ncmds):
        cmd, size = struct.unpack_from("<II", data, off)
        if cmd == 0x19:  # LC_SEGMENT_64
            segname = data[off + 8:off + 24].rstrip(b"\0").decode()
            vmaddr, vmsize, fileoff, filesize = struct.unpack_from("<QQQQ", data, off + 24)
            nsects = struct.unpack_from("<I", data, off + 64)[0]
            secs = []
            for s in range(nsects):
                so = off + 72 + s * 80
                sect = data[so:so + 16].rstrip(b"\0").decode()
                addr, ssize = struct.unpack_from("<QQ", data, so + 32)
                sfo = struct.unpack_from("<I", data, so + 48)[0]
                secs.append((sect, addr, ssize, sfo))
                if segname == "__TEXT" and sect == "__text":
                    text = (addr, addr + ssize)
            segs.append((segname, vmaddr, vmsize, fileoff, filesize, secs))
        off += size
    return data, segs, text


def vtables(path):
    data, segs, text = load(path)
    # Typeinfo name strings live in __TEXT,__const (or __cstring): "<len><Name>\0"
    names = {}
    for segname, vmaddr, vmsize, fileoff, filesize, secs in segs:
        for sect, addr, ssize, sfo in secs:
            if sect in ("__const", "__cstring") and segname == "__TEXT":
                blob = data[sfo:sfo + ssize]
                i = 0
                while i < len(blob):
                    j = blob.find(b"\0", i)
                    if j < 0:
                        break
                    s = blob[i:j]
                    # Names can directly follow other constant data (e.g. a GUID) with no
                    # NUL before them, so accept a "<len><Name>" that ends the chunk.
                    for st in range(len(s)):
                        if not s[st:st + 1].isdigit() or (st and s[st - 1:st].isdigit()):
                            continue
                        k = st
                        while k < len(s) and s[k:k + 1].isdigit():
                            k += 1
                        n = int(s[st:k])
                        if n == len(s) - k and n > 2:
                            names[addr + i + st] = s[k:].decode("latin-1")
                            break
                    i = j + 1
    # 8-byte words in data segments
    words = {}
    for segname, vmaddr, vmsize, fileoff, filesize, secs in segs:
        if segname.startswith("__DATA"):
            for sect, addr, ssize, sfo in secs:
                if sfo == 0:
                    continue
                for o in range(0, ssize - 7, 8):
                    words[addr + o] = struct.unpack_from("<Q", data, sfo + o)[0]
    # typeinfo objects: {class-typeinfo vptr, name ptr, ...}; name ptr matches a name string.
    # libc++ sets bit 63 on the name pointer of non-unique (hidden-visibility) typeinfo.
    ti = {a - 8: names[v & ~(1 << 63)] for a, v in words.items() if v & ~(1 << 63) in names}
    result = {}
    for a, v in words.items():
        if v in ti and words.get(a - 8, 1) in (0,) or (v in ti and (words.get(a - 8, 0) >> 63)):
            # vtable: [offset-to-top][typeinfo][fn...]
            n = 0
            p = a + 8
            while p in words and text[0] <= words[p] < text[1]:
                n += 1
                p += 8
            if n:
                result.setdefault(ti[v], []).append(n)
    return {k: sorted(v) for k, v in result.items()}


def load_ref(path):
    return json.load(open(path)) if path.endswith(".json") else vtables(path)


def compare(ref_path, cand_path, flt=""):
    ref, cand = load_ref(ref_path), vtables(cand_path)
    bad = 0
    for cls in sorted(set(ref) & set(cand)):
        if flt not in cls:
            continue
        if ref[cls] != cand[cls]:
            bad += 1
            print(f"MISMATCH {cls:40s} ref {ref[cls]}  ours {cand[cls]}")
    common = len([c for c in set(ref) & set(cand) if flt in c])
    print(f"{common} classes compared, {bad} mismatched; only in ref: {len(set(ref) - set(cand))}, only in ours: {len(set(cand) - set(ref))}")
    for side, names in (("only in ref", set(ref) - set(cand)), ("only in ours", set(cand) - set(ref))):
        if names:
            print(f"  {side}: {', '.join(sorted(names))}")
    return 1 if bad else 0


def main():
    if sys.argv[1] == "--dump":
        json.dump(vtables(sys.argv[2]), open(sys.argv[3], "w"), indent=0, sort_keys=True)
        return 0
    return compare(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")


if __name__ == "__main__":
    sys.exit(main())
