"""Source fixups applied to the staged copy of a game core tree before compiling.

Only for things a header cannot express. Every rule states how many matches it
expects, so upstream changes fail loudly instead of silently skipping a fix.

  Rule    - regex over every source file in the tree (count is a minimum)
  Literal - exact text in one file, by name (count is exact, per copy of the file)
"""
import os
import re

CPP_EXT = (".cpp", ".h", ".inl")


class Rule:
    """game_core_code: only game core sources (not the engine headers the exe was built
    against), and only code, never comments or string literals. skip: filenames left as-is."""
    def __init__(self, name, pattern, repl, min_hits, why, game_core_code=False, skip=()):
        self.name, self.rx, self.repl, self.min_hits, self.why = name, re.compile(pattern), repl, min_hits, why
        self.game_core_code, self.skip = game_core_code, {s.lower() for s in skip}


_CODE_SPLIT = re.compile(r'(//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\')', re.S)


def _subn_code(rx, repl, text):
    """re.subn over the code between comments and string/char literals."""
    parts = _CODE_SPLIT.split(text)
    n = 0
    for i in range(0, len(parts), 2):  # even indices are code
        parts[i], k = rx.subn(repl, parts[i])
        n += k
    return "".join(parts), n


def _is_game_core_dir(d):
    """The project directory (holds CvGameCoreDLLPCH.h) or its Lua/ subdirectory."""
    return (os.path.exists(os.path.join(d, "CvGameCoreDLLPCH.h"))
            or (os.path.basename(d) == "Lua" and os.path.exists(os.path.join(os.path.dirname(d), "CvGameCoreDLLPCH.h"))))


class Transform:
    """A Python function applied to one file; it returns (new_text, matches)."""
    def __init__(self, name, filename, func, count, why):
        self.name, self.filename, self.func, self.count, self.why = name, filename.lower(), func, count, why


class Literal:
    def __init__(self, name, filename, old, new, count, why):
        self.name, self.filename, self.old, self.new, self.count, self.why = name, filename.lower(), old, new, count, why


def _lua_wrapper_owner(text):
    """Let CvLuaMethodWrapper::BasicLuaMethod deduce the class that declares the member.

    Callers pass e.g. &CvPlayerAI::disbandUnit, whose type is void (CvPlayer::*)(bool);
    deduction against InstanceType::* fails in standard C++ (MSVC 2008 allowed it).
    """
    n = 0
    # Declarations / definitions that are already templates: prepend a deduced owner.
    text, k = re.subn(r"template<(typename ret[^>]*|typename arg1[^>]*)>(\s*(?:static )?int (?:CvLuaMethodWrapper<Derived, InstanceType>::)?BasicLuaMethod)",
                      r"template<\1, class Owner_>\2", text)  # last: callers give explicit <ret, arg> args
    n += k
    # The two non-template void() overloads (declaration + definition each).
    text, k = re.subn(r"(\n\t)(static int BasicLuaMethod\(lua_State\* L, void \(InstanceType::\*func\)\(\)( const)?\);)",
                      r"\1template<class Owner_>\1\2", text)
    n += k
    text, k = re.subn(r"(template<class Derived, class InstanceType>)(\s*int CvLuaMethodWrapper<Derived, InstanceType>::BasicLuaMethod\(lua_State\* L, void \(InstanceType::\*func\)\(\)( const)?\))",
                      r"\1 template<class Owner_>\2", text)
    n += k
    text, k = re.subn(r"\(InstanceType::\*func\)", "(Owner_::*func)", text)
    n += k
    return text, n


RULES = [
    Rule("net-debug-log-off", r"\bgDLL->netMessageDebugLog\(", "civ5mac::netMessageDebugLog(", 10,
         "Aspyr's exe runs this debug text through a printf-style formatter even with MessageLog off, "
         "and unit names in it can crash that (Great People names: see compat/prelude.h). Debug output only."),
    Rule("msvc-sort", r"\bstd::sort\s*\(", "civ5mac::msvc_sort(", 5,
         "std::sort orders tied elements differently per STL; use MSVC 2008's algorithm (compat/msvc_sort.h)."),
    # Windows is LLP64: long is 32 bits, and the game's results (RNG seeds that the exe
    # serialises as 4 bytes, overflow in AI scores) depend on it. CvDllRandom keeps its
    # ICvRandom1 signatures and converts at the boundary.
    Rule("llp64-unsigned-long", r"\bunsigned\s+long(?:\s+int)?\b(?!\s+(?:long|double)\b)", "unsigned int", 5,
         "Windows unsigned long is 32-bit", game_core_code=True, skip=("CvDllRandom.h", "CvDllRandom.cpp")),
    Rule("llp64-long", r"(?<!unsigned )(?<!long )\blong(?:\s+int)?\b(?!\s+(?:long|double)\b)", "int", 5,
         "Windows long is 32-bit", game_core_code=True, skip=("CvDllRandom.h", "CvDllRandom.cpp")),
]

# FireWorks template headers lean on MSVC 2008 only parsing template bodies at
# instantiation. These are identical in every tree derived from Firaxis' SDK.
LITERALS = [
    Literal("fixedblockalloc-default", "FFastAllocator.h",
            "typename BaseVector< T, bPODType >::FDefaultFastVectorAllocator\n> class FFixedBlockAllocator",
            "typename BaseVector< T, false >::FDefaultFastVectorAllocator\n> class FFixedBlockAllocator", 1,
            "default names a parameter FFixedBlockAllocator does not have; never instantiated on Windows"),
    Literal("fixedblockalloc-assign", "FFastAllocator.h",
            "void operator = (const FFastAllocator& rhs){}",
            "void operator = (const FFixedBlockAllocator& rhs){}", 1,
            "private no-copy operator names the wrong class"),
    Literal("fastlist-copyctor", "FFastList.h",
            "explicit TYPE( const TYPE& rhs ) : BASE_TYPE( rhs ) {};",
            "explicit FFastList( const TYPE& rhs ) : BASE_TYPE( rhs ) {};", 1,
            "constructor declared through a typedef name"),
    Literal("fastlist-friend", "FFastList.h", "friend class TYPE;", "friend TYPE;", 2,
            "elaborated 'class' on a typedef"),
    Literal("flua-get-int", "FLuaCommon.h",
            "template<> static inline long Get(lua_State *L, int idx) { return (long)lua_tointeger(L, idx); }",
            "template<> static inline int Get(lua_State *L, int idx) { return (int)lua_tointeger(L, idx); }", 1,
            "lua_Integer is ptrdiff_t: int on Win32, long on macOS (and in Aspyr's exe). Keep one specialization "
            "per distinct type so Get<int> exists, truncating exactly as Windows does."),
    Literal("ftimer-getticks", "FTimer.h",
            "__forceinline __int64 GetTicks() { __asm rdtsc }",
            "__forceinline __int64 GetTicks() { return (__int64)__rdtsc(); }", 1,
            "32-bit MSVC inline asm; profiling only"),
    Literal("ftimer-p5time", "FTimer.h",
            "inline __declspec(naked) uint P5time()\n{\n\tstatic\tint tick=0;\n\n\t__asm  mov   ecx,tick\n    __asm  rdtsc\n\t__asm  mov   tick,eax\n\t__asm  sub   eax,ecx\n\t__asm  ret\n}",
            "inline uint P5time()\n{\n\tstatic\tuint tick=0;\n\tuint now = (uint)__rdtsc();\n\tuint delta = now - tick;\n\ttick = now;\n\treturn delta;\n}", 1,
            "naked 32-bit inline asm; profiling only"),
    Literal("flua-unsafecast", "FLuaCommon.h",
            "FLUA_COMPILE_TIME_CONDITION(sizeof(TIn) == sizeof(TOut), CantUseUnsafeCast);\n\t\t\tunion { TIn inVal; TOut outVal; } u;\n\t\t\tu.inVal = inVal;\n\t\t\treturn u.outVal;",
            "// Itanium member-function pointers are {ptr, adj} (16 bytes) where MSVC's are 4: zero-fill so a\n"
            "\t\t\t// plain function pointer becomes the valid non-virtual member pointer {ptr, 0}.\n"
            "\t\t\tFLUA_COMPILE_TIME_CONDITION(sizeof(TIn) <= sizeof(TOut), CantUseUnsafeCast);\n"
            "\t\t\tTOut outVal;\n\t\t\tmemset(&outVal, 0, sizeof(outVal));\n\t\t\tmemcpy(&outVal, &inVal, sizeof(TIn));\n\t\t\treturn outVal;", 1,
            "function-pointer to member-function-pointer pun assumes MSVC sizes"),
    # Game core: a parameter named 'default' (a keyword MSVC 2008 let through).
    Literal("dbutil-default-decl", "CvDatabaseUtility.h", "const char* szTableName, T default = (T)0);",
            "const char* szTableName, T kDefault = (T)0);", 1, "'default' is a keyword"),
    Literal("dbutil-default-def", "CvDatabaseUtility.h", "const char* szTableName, T default)",
            "const char* szTableName, T kDefault)", 1, "'default' is a keyword"),
    Literal("dbutil-default-use", "CvDatabaseUtility.h", "InitializeArray(pArray, count, default);",
            "InitializeArray(pArray, count, kDefault);", 1, "'default' is a keyword"),
    Literal("localization-pushargument-int64", "CvLocalization.h",
            "CvLocalizationAPI bool PushArgument(const __int64 val);",
            "CvLocalizationAPI bool PushArgument(const long val);", 1,
            "Aspyr's exe exports PushArgument(long), not (long long); also resolves long-argument ambiguity"),
    Literal("localization-string-from-std", "CvLocalization.h",
            "CvLocalizationAPI String(const char* szString);",
            "CvLocalizationAPI String(const char* szString);\n"
            "\t\t// MSVC accepted CvString -> const char* -> String in copy-initialization.\n"
            "\t\tString(const std::string& s) : String(s.c_str()) {}\n"
            "\t\t// ...and keep CvString arguments on the const char* overloads, as on Windows.\n"
            "\t\tbool PushArgument(const std::string& s) { return PushArgument(s.c_str()); }\n"
            "\t\tString& operator=(const std::string& s) { return *this = s.c_str(); }", 1,
            "two user-defined conversions in copy-initialization"),
    Literal("datastream-write-long", "FDataStream.h", "\tvoid Write(const unsigned long &);",
            "\tvoid Write(const unsigned long &);\n"
            "\t// Windows 'long' is 32-bit: keep it 4 bytes in saves and network data.\n"
            "\tvoid Write(const long &v) { const INT32 i = (INT32)v; Write(i); }", 1,
            "no overload for long (ambiguous on LP64); serialize as Windows would"),
    Literal("datastream-read-long", "FDataStream.h", "\tvoid Read(unsigned long &);",
            "\tvoid Read(unsigned long &);\n\tvoid Read(long &v) { INT32 i; Read(i); v = i; }", 1,
            "pairs with datastream-write-long"),
    Literal("datastream-arraywrapper-in", "FDataStream.h",
            "FDataStream & operator>>(FDataStream & loadFrom, ArrayWrapper<ValueType> & v)",
            "FDataStream & operator>>(FDataStream & loadFrom, ArrayWrapper<ValueType> & v);\n"
            "// Callers also stream into temporary wrappers, which MSVC binds to non-const references.\n"
            "template<typename ValueType>\n"
            "FDataStream & operator>>(FDataStream & loadFrom, const ArrayWrapper<ValueType> & v)\n"
            "{ return loadFrom >> const_cast<ArrayWrapper<ValueType>&>(v); }\n"
            "template<typename ValueType>\n"
            "FDataStream & operator>>(FDataStream & loadFrom, ArrayWrapper<ValueType> & v)", 1,
            "temporary wrappers bound to non-const references"),
    Literal("datastream-arraywrapperconst-in", "FDataStream.h",
            "FDataStream & operator>>(FDataStream & loadFrom, ArrayWrapperConst<ValueType> & v)",
            "FDataStream & operator>>(FDataStream & loadFrom, ArrayWrapperConst<ValueType> & v);\n"
            "// Callers also stream into temporary wrappers, which MSVC binds to non-const references.\n"
            "template<typename ValueType>\n"
            "FDataStream & operator>>(FDataStream & loadFrom, const ArrayWrapperConst<ValueType> & v)\n"
            "{ return loadFrom >> const_cast<ArrayWrapperConst<ValueType>&>(v); }\n"
            "template<typename ValueType>\n"
            "FDataStream & operator>>(FDataStream & loadFrom, ArrayWrapperConst<ValueType> & v)", 1,
            "temporary wrappers bound to non-const references"),
    Literal("astar-explicit-base-ctor", "CvAStar.cpp", "\tCvAStar::CvAStar();\n", "", 1,
            "explicit base constructor call (MSVC extension); the base is already default-constructed"),
    Literal("infoserial-fstring-vararg", "CvInfosSerializationHelper.cpp",
            'szError.Format("LOAD ERROR: Type not found: %s", sTemp);',
            'szError.Format("LOAD ERROR: Type not found: %s", (LPCSTR)sTemp);', 1,
            "FString passed through '...' (works on MSVC only because the object is a lone char*)"),
    Literal("promotion-fstring-vararg", "CvPromotionClasses.cpp",
            'szError.Format("LOAD ERROR: Promotion Type not found: %s", sTemp);',
            'szError.Format("LOAD ERROR: Promotion Type not found: %s", (LPCSTR)sTemp);', 1,
            "FString passed through '...'"),
    Literal("player-tr1-array-assign", "CvPlayer.cpp", "aTeamCityCount.assign(0);", "aTeamCityCount.fill(0);", 1,
            "MSVC 2008 tr1::array::assign is std::array::fill"),
    Literal("pregame-teamtype-static", "CvPreGame.h", "static TeamTypes     teamType(PlayerTypes p)",
            "inline TeamTypes     teamType(PlayerTypes p)", 1,
            "static definition after an extern declaration: MSVC made it internal, C++ keeps it external"),
    Literal("pregame-iface-eratype", "CvDllInterfaces.h", "\tvirtual EraTypes DLLCALL era() = 0;\n",
            "\tvirtual EraTypes DLLCALL era() = 0;\n\tvirtual std::string DLLCALL eraType() = 0;\n", 1,
            "Aspyr's ICvPreGame1 has an extra slot after era() (218 vs 217); body in compat/aspyr_abi.cpp"),
    Literal("pregame-dll-eratype", "CvDllPreGame.h", "\tEraTypes DLLCALL era();\n",
            "\tEraTypes DLLCALL era();\n\tstd::string DLLCALL eraType();\n", 1,
            "declares the Aspyr-only ICvPreGame1::eraType()"),
    Literal("firetypes-dword", "FFireTypes.h", "typedef unsigned long\t\tdword;", "typedef unsigned int\t\tdword;", 1,
            "Windows dword is 32-bit; Aspyr's exe uses unsigned int (FCRC::Calc, TempHeap::Allocate exports)"),
    Literal("gamecoredll-loadsymbols", "CvGameCoreDLL.cpp",
            "\t\tFDebugHelper::GetInstance().LoadSymbols((HMODULE)hModule);\n", "", 1,
            "Windows symbol loading in DllMain (never called on macOS; not exported by the exe)"),
    Literal("fstringa-initdata-clinkage", "FString.h", "\nFStringA::FStringAData* FStringA_GetStringInitData();",
            "\nextern \"C\" FStringA::FStringAData* FStringA_GetStringInitData();", 1,
            "the exe exports the empty-string headers with C linkage"),
    Literal("fstringw-initdata-clinkage", "FString.h", "\nFStringW::FStringWData* FStringW_GetStringInitData();",
            "\nextern \"C\" FStringW::FStringWData* FStringW_GetStringInitData();", 1,
            "the exe exports the empty-string headers with C linkage"),
    Literal("database-connection-maps", "Database.h",
            "\t\tstd::tr1::unordered_map<std::string, sqlite3_stmt*> m_hshCountStatements;\n"
            "\t\tstd::tr1::unordered_map<std::string, int> m_hshCountValues;",
            "\t\t// Aspyr's exe lays its tr1::unordered_maps out in 72 bytes (libc++'s are 40); only\n"
            "\t\t// the exe touches these, so reserve exactly its space (see compat/abi_checks.cpp).\n"
            "\t\talignas(8) unsigned char m_hshCountStatements[72];\n"
            "\t\talignas(8) unsigned char m_hshCountValues[72];", 1,
            "Connection is constructed by the game core but laid out by the exe"),
    Literal("database-results-map", "DatabaseResults.h",
            "\t\tstdext::hash_map<std::string, int> m_hshColumnPositions;",
            "\t\t// Aspyr's hash containers are 72 bytes (see database-connection-maps); exe-only member.\n"
            "\t\talignas(8) unsigned char m_hshColumnPositions[72];", 1,
            "Results objects live on the game core's stack but are constructed by the exe"),
    # -ffp-eval-method=double (see build.py) types float expressions as double; keep MSVC's
    # float-typed arguments where a call would otherwise deduce or pick a double overload.
    Literal("fpeval-team-max", "CvTeam.cpp", "MAX(0.0f, fTimeElapsed - fGameTurnEnd + fBaseTurnTime)",
            "MAX(0.0f, (float)(fTimeElapsed - fGameTurnEnd + fBaseTurnTime))", 1,
            "std::max(float, double-typed float expression) cannot deduce one type"),
    Literal("fpeval-league-max", "CvVotingClasses.cpp",
            "MAX((float)iBestContribution, GC.getLEAGUE_PROJECT_REWARD_TIER_2_THRESHOLD() * GetProjectCostPerPlayer(eLeagueProject))",
            "MAX((float)iBestContribution, (float)(GC.getLEAGUE_PROJECT_REWARD_TIER_2_THRESHOLD() * GetProjectCostPerPlayer(eLeagueProject)))", 1,
            "std::max(float, double-typed float expression) cannot deduce one type"),
    # MSVC passes a float expression to the <cmath> float overload, rounding it to float first
    # (FindTargetSpyNumbers: fild; fmul dword; fstp dword; ...; call ceil). With
    # -ffp-eval-method=double the expression is double-typed and picks the double overload
    # unrounded: 0.3f * 10 = 3.0000001 -> ceil 4 instead of 3. Cast to float as MSVC does.
    Literal("fpeval-espionage-ceil", "CvEspionageClasses.cpp", "(int)ceil(fTechPositionRatio * iNumRemainingSpies)",
            "(int)ceil((float)(fTechPositionRatio * iNumRemainingSpies))", 3,
            "float argument to ceil (offensive spy count)"),
    Literal("fpeval-league-floor", "CvGame.cpp", "(int)floor(fCivVotesPortion + fCityStateVotesPortion)",
            "(int)floor((float)(fCivVotesPortion + fCityStateVotesPortion))", 1,
            "float argument to floor (votes needed to win)"),
    Literal("fpeval-trade-ceil", "CvTradeClasses.cpp", "(int)ceil(iTechDifference / 2.0f)",
            "(int)ceil((float)(iTechDifference / 2.0f))", 4,
            "float argument to ceil (trade route tech difference)"),
    # SetHasLostCapital can ask isHasMet(NO_TEAM). On Windows, m_abHasMet[-1] reads the byte
    # before the array, the last entry of m_abHasFoundPlayersTerritory (same layout here); on
    # 64-bit the index becomes 4 billion and the game crashes. Read what Windows reads.
    Literal("hasmet-no-team", "CvTeam.cpp", "\treturn m_abHasMet[eIndex];",
            "\treturn eIndex == NO_TEAM ? m_abHasFoundPlayersTerritory[REALLY_MAX_PLAYERS - 1] : m_abHasMet[eIndex];", 1,
            "isHasMet(NO_TEAM) reads the preceding member on Windows"),
    # FireWorks containers take their index as unsigned int. A negative index (NO_PLAYER,
    # NO_TEAM, ... = -1) then wraps: on 32-bit Windows base + 0xFFFFFFFF*size is base - size,
    # the element before the array; on 64-bit it is 4 billion elements on, and crashes. Index
    # with the signed value so the address is the one Windows uses.
    Literal("index32-farray", "FArray.h", "return m_pData[i];", "return m_pData[(int)i];", 1,
            "FArray: Windows' 32-bit wrap for negative indices"),
    Literal("index32-farray-static", "FArray.h", "return ( m_akItems[ i ] );", "return ( m_akItems[ (int)i ] );", 2,
            "Firaxis::Array: Windows' 32-bit wrap for negative indices"),
    Literal("index32-fastvector", "FFastVector.h", "return m_pData[ui];", "return m_pData[(int)ui];", 2,
            "FFastVector/FStaticVector: Windows' 32-bit wrap for negative indices"),
    Literal("index32-fastvector-at", "FFastVector.h", "return m_pData[i];", "return m_pData[(int)i];", 2,
            "FFastVector::at: Windows' 32-bit wrap for negative indices"),
    Literal("index32-fastallocator", "FFastAllocator.h", "return m_pData[ui];", "return m_pData[(int)ui];", 2,
            "FFastAllocator: Windows' 32-bit wrap for negative indices"),
    Literal("index32-fastallocator-vec", "FFastAllocator.h", "return m_vec[ui];", "return m_vec[(int)ui];", 2,
            "FFastAllocator: Windows' 32-bit wrap for negative indices"),
    Literal("fpeval-pushargument-double", "CvLocalization.h", "\t\tCvLocalizationAPI bool PushArgument(const double val);",
            "\t\t// Not exported by Aspyr's exe; float expressions (now double-typed) format as float, as on Windows.\n"
            "\t\tbool PushArgument(const double val) { return PushArgument((float)val); }", 1,
            "float expressions would bind the double overload, which the exe does not export"),
    Literal("inputdevice-map-alloc", "FInputDevice.h",
            "FSTL_Tagged_Allocator<std::pair<uint, uint>, 16,c_eMPoolTypeContainer> > HotKeyMap;",
            "FSTL_Tagged_Allocator<std::pair<const uint, uint>, 16,c_eMPoolTypeContainer> > HotKeyMap;", 1,
            "std::map allocator must allocate pair<const K, V> (libc++ enforces; same layout)"),
]


TRANSFORMS = [
    # 18 templated + 2x2 non-template signatures get an owner param; 40 member-pointer types renamed.
    Transform("lua-wrapper-owner", "CvLuaMethodWrapper.h", _lua_wrapper_owner, 36 + 4 + 40,
              "member pointers to base-class methods (MSVC-only deduction)"),
]


def apply(tree):
    hits = {r.name: 0 for r in RULES}
    lit_hits = {l.name: [] for l in LITERALS + TRANSFORMS}
    for d, _, files in os.walk(tree):
        for f in files:
            if not f.endswith(CPP_EXT):
                continue
            path = os.path.join(d, f)
            text = open(path, "rb").read().decode("latin-1")
            new = text.replace("\r\n", "\n")
            for r in RULES:
                if r.game_core_code:
                    if f.lower() in r.skip or not _is_game_core_dir(d):
                        continue
                    new, n = _subn_code(r.rx, r.repl, new)
                else:
                    new, n = r.rx.subn(r.repl, new)
                hits[r.name] += n
            for l in LITERALS:
                if f.lower() == l.filename:
                    n = new.count(l.old)
                    lit_hits[l.name].append((path, n))
                    new = new.replace(l.old, l.new)
            for t in TRANSFORMS:
                if f.lower() == t.filename:
                    new, n = t.func(new)
                    lit_hits[t.name].append((path, n))
            if new != text:
                open(path, "wb").write(new.encode("latin-1"))

    problems = []
    for r in RULES:
        if hits[r.name] < r.min_hits:
            problems.append(f"rule '{r.name}' matched {hits[r.name]}x, expected >= {r.min_hits}: {r.why}")
    for l in LITERALS + TRANSFORMS:
        seen = lit_hits[l.name]
        if not seen:
            problems.append(f"literal '{l.name}': no file named {l.filename}")
        for path, n in seen:
            if n != l.count:
                problems.append(f"literal '{l.name}' matched {n}x in {path}, expected {l.count}: {l.why}")
    if problems:
        raise SystemExit("fixups failed:\n  " + "\n  ".join(problems))
    print("fixups:", ", ".join([f"{k}={v}" for k, v in hits.items()] + [f"{k}=ok" for k in lit_hits]))
