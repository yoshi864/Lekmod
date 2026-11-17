// Force-included before every game core translation unit.
//
// Supplies the slice of the Win32/MSVC environment the Firaxis SDK sources expect.
// Everything declared extern here is *provided by Aspyr's Civilization V executable*
// at load time; the declarations mirror the exact signatures Aspyr's own game core
// imports, so the mangled names line up (tools/build.py verifies this after linking).
#pragma once
#ifndef CIV5MAC_PRELUDE_H
#define CIV5MAC_PRELUDE_H

#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <wchar.h>
#include <wctype.h>
#include <ctype.h>
#include <limits.h>
#include <float.h>
#include <math.h>
#include <assert.h>
#include <x86intrin.h>

#ifdef __cplusplus
#include <new>
#include <string>
#include <vector>
#include <list>
#include <map>
#include <set>
#include <deque>
#include <algorithm>
#include <functional>
#include <utility>
#include <unordered_map>
#include <unordered_set>
#include <memory>
#include <array>
#include <tuple>
#endif

// ---------------------------------------------------------------------------
// Win32 scalar types (Windows is ILP32/LLP64: DWORD and LONG are 32-bit).
// ---------------------------------------------------------------------------
typedef int BOOL;
typedef unsigned char BYTE;
typedef unsigned short WORD;
typedef unsigned short USHORT;
typedef uint32_t DWORD;
typedef int32_t LONG;
typedef uint32_t ULONG;
typedef unsigned int UINT;
typedef int INT;
typedef char CHAR;
typedef short SHORT;
typedef float FLOAT;
typedef wchar_t WCHAR;
typedef char TCHAR;
typedef int8_t INT8;
typedef uint8_t UINT8;
typedef int16_t INT16;
typedef uint16_t UINT16;
typedef int32_t INT32;
typedef uint32_t UINT32;
typedef int64_t INT64;
typedef uint64_t UINT64;
typedef int64_t LONGLONG;
typedef uint64_t ULONGLONG;
typedef intptr_t INT_PTR;
typedef uintptr_t UINT_PTR;
typedef intptr_t LONG_PTR;
typedef uintptr_t ULONG_PTR;
typedef uintptr_t DWORD_PTR;
typedef size_t SIZE_T;
typedef void* HANDLE;
typedef void* HMODULE;
typedef void* HINSTANCE;
typedef void* HWND;
typedef void* LPVOID;
typedef const void* LPCVOID;
typedef char* LPSTR;
typedef const char* LPCSTR;
typedef wchar_t* LPWSTR;
typedef const wchar_t* LPCWSTR;
typedef char* LPTSTR;
typedef const char* LPCTSTR;
typedef DWORD* LPDWORD;
typedef BOOL* LPBOOL;
typedef BYTE* LPBYTE;
typedef long HRESULT;
typedef UINT MMRESULT;
typedef void* PVOID;
typedef ULONG* PULONG;
typedef DWORD* PDWORD;
typedef uint64_t DWORD64;

typedef union _LARGE_INTEGER {
	struct { DWORD LowPart; LONG HighPart; };
	struct { DWORD LowPart; LONG HighPart; } u;
	LONGLONG QuadPart;
} LARGE_INTEGER;

typedef struct _GUID {
	uint32_t Data1;
	unsigned short Data2;
	unsigned short Data3;
	unsigned char Data4[8];
} GUID;

// Aspyr's exe implements critical sections on a Win64-shaped 40-byte struct
// (FCriticalSection::FCriticalSection writes offsets 0x00-0x27), so match that size.
typedef struct _RTL_CRITICAL_SECTION {
	void* DebugInfo;
	LONG LockCount;
	LONG RecursionCount;
	HANDLE OwningThread;
	HANDLE LockSemaphore;
	ULONG_PTR SpinCount;
} CRITICAL_SECTION, *LPCRITICAL_SECTION;
#ifdef __cplusplus
static_assert(sizeof(CRITICAL_SECTION) == 40, "must match Aspyr exe layout");
#endif

typedef struct tagPOINT { LONG x; LONG y; } POINT, *LPPOINT;
typedef struct tagRECT { LONG left, top, right, bottom; } RECT, *LPRECT;

typedef struct _SYSTEMTIME {
	WORD wYear, wMonth, wDayOfWeek, wDay, wHour, wMinute, wSecond, wMilliseconds;
} SYSTEMTIME, *LPSYSTEMTIME;
typedef struct _CONTEXT CONTEXT, *PCONTEXT;

#ifdef __cplusplus
inline bool operator==(const GUID& a, const GUID& b) { return memcmp(&a, &b, sizeof(GUID)) == 0; }
inline bool operator!=(const GUID& a, const GUID& b) { return !(a == b); }
#endif

typedef struct _FILETIME { DWORD dwLowDateTime; DWORD dwHighDateTime; } FILETIME;
static inline LONG CompareFileTime(const FILETIME* a, const FILETIME* b)
{
	const uint64_t x = ((uint64_t)a->dwHighDateTime << 32) | a->dwLowDateTime;
	const uint64_t y = ((uint64_t)b->dwHighDateTime << 32) | b->dwLowDateTime;
	return x < y ? -1 : (x > y ? 1 : 0);
}
typedef struct _WIN32_FILE_ATTRIBUTE_DATA {
	DWORD dwFileAttributes;
	FILETIME ftCreationTime, ftLastAccessTime, ftLastWriteTime;
	DWORD nFileSizeHigh, nFileSizeLow;
} WIN32_FILE_ATTRIBUTE_DATA;
typedef enum _GET_FILEEX_INFO_LEVELS { GetFileExInfoStandard, GetFileExMaxInfoLevel } GET_FILEEX_INFO_LEVELS;
typedef struct _SECURITY_ATTRIBUTES SECURITY_ATTRIBUTES, *LPSECURITY_ATTRIBUTES;
typedef struct _OVERLAPPED OVERLAPPED, *LPOVERLAPPED;
typedef enum _HEAP_INFORMATION_CLASS { HeapCompatibilityInformation } HEAP_INFORMATION_CLASS;

#define TRUE 1
#define FALSE 0
#define WINAPI
#define APIENTRY
#define CALLBACK
#define __cdecl
#define __stdcall
#define __fastcall
#define __thiscall
#define __w64
#define _CRTIMP
#define DECLSPEC_NOVTABLE
#define DECLSPEC_DEPRECATED
#define DECLSPEC_DEPRECATED_S(x)
#define __ptr64
#define __assume(x) ((void)0)
#define __debugbreak() __builtin_trap()
#define __noop(...) ((void)0)
#define _alloca __builtin_alloca
#define _MAX_PATH 260
#define MAX_PATH 260
#define INFINITE 0xFFFFFFFF
#define INVALID_HANDLE_VALUE ((HANDLE)(intptr_t)-1)
#define _TRUNCATE ((size_t)-1)
#define _T(x) x
#define TEXT(x) x
#define _TEXT(x) x
#define S_OK ((HRESULT)0)
#define GENERIC_READ 0x80000000u
#define GENERIC_WRITE 0x40000000u
#define FILE_SHARE_READ 0x00000001
#define OPEN_EXISTING 3
#define CREATE_ALWAYS 2
#define FILE_ATTRIBUTE_NORMAL 0x80
#define INVALID_FILE_ATTRIBUTES ((DWORD)-1)
#define HEAP_NO_SERIALIZE 0x00000001
#define HEAP_GENERATE_EXCEPTIONS 0x00000004
#define HEAP_ZERO_MEMORY 0x00000008
#define MAKEWORD(a, b) ((WORD)(((BYTE)(a)) | ((WORD)((BYTE)(b))) << 8))
#define MAKELONG(a, b) ((LONG)(((WORD)(a)) | ((DWORD)((WORD)(b))) << 16))
#define LOWORD(l) ((WORD)((DWORD)(l) & 0xffff))
#define HIWORD(l) ((WORD)((DWORD)(l) >> 16))
#define UNREFERENCED_PARAMETER(P) (void)(P)
#define ZeroMemory(p, n) memset((p), 0, (n))
#define _malloca(n) alloca(n)
#define _freea(p) ((void)0)
#define _tcslen strlen
#define _tcsicmp _stricmp
#define _tcscmp strcmp
#define _tcsncmp strncmp
#define _tcscpy strcpy
#define _tcsncpy strncpy
#define _tcsstr strstr
#define _tcschr strchr
#define _tcsrchr strrchr
#define _stprintf sprintf
#define MAXINT INT_MAX
#define MININT INT_MIN
#define MAXUINT UINT_MAX
#define MAXDWORD 0xffffffffu
#define INVALID_FILE_SIZE ((DWORD)0xFFFFFFFF)
#define FILE_SHARE_WRITE 0x00000002
#define FILE_SHARE_DELETE 0x00000004
#define FILE_FLAG_SEQUENTIAL_SCAN 0x08000000
#define ERROR_FILE_NOT_FOUND 2L
#define ERROR_PATH_NOT_FOUND 3L
#define CopyMemory(d, s, n) memcpy((d), (s), (n))
#define fprintf_s fprintf
#define sscanf_s sscanf
#define CP_UTF8 65001
#define DLL_PROCESS_DETACH 0
#define DLL_PROCESS_ATTACH 1
#define DLL_THREAD_ATTACH 2
#define DLL_THREAD_DETACH 3
#define TIMERR_NOERROR 0
#define CP_ACP 0

// SAL annotations: documentation only.
#include "sal.h"

// ---------------------------------------------------------------------------
// MSVC CRT names. The exe exports _stricmp/_strnicmp/_vsnprintf; others map to POSIX.
// ---------------------------------------------------------------------------
#ifdef __cplusplus
extern "C" {
#endif
int _stricmp(const char*, const char*);
int _strnicmp(const char*, const char*, size_t);
int _vsnprintf(char*, size_t, const char*, va_list);
char* _strdup(const char*);
#ifdef __cplusplus
}
#endif
#define stricmp _stricmp
#define strnicmp _strnicmp
#define _snprintf snprintf
#define _wcsicmp wcscasecmp
#define _wcsnicmp wcsncasecmp
#define _strlwr(s) civ5mac_strlwr(s)
#define _strupr(s) civ5mac_strupr(s)
#define _isnan isnan
#define _finite isfinite
#define _hypot hypot
#define _copysign copysign
#define _countof(a) (sizeof(a) / sizeof((a)[0]))
static inline char* civ5mac_strlwr(char* s) { for (char* p = s; *p; ++p) *p = (char)tolower((unsigned char)*p); return s; }
static inline char* civ5mac_strupr(char* s) { for (char* p = s; *p; ++p) *p = (char)toupper((unsigned char)*p); return s; }
// Used by the SDK's FireWorks FStringA/FStringW.inl. Collation is the "C" locale, as on
// the exe's side (its _stricmp), so _stricoll == _stricmp.
#define _stricoll _stricmp
#define _wcsicoll wcscasecmp
static inline char* _strnset(char* s, int c, size_t n) { for (size_t i = 0; i < n && s[i]; ++i) s[i] = (char)c; return s; }
static inline wchar_t* _wcsnset(wchar_t* s, wchar_t c, size_t n) { for (size_t i = 0; i < n && s[i]; ++i) s[i] = c; return s; }
static inline wchar_t* _wcsupr(wchar_t* s) { for (wchar_t* p = s; *p; ++p) *p = (wchar_t)towupper(*p); return s; }
static inline wchar_t* _wcslwr(wchar_t* s) { for (wchar_t* p = s; *p; ++p) *p = (wchar_t)towlower(*p); return s; }
template <class C> static inline C* civ5mac_strrev(C* s)
{
	C* e = s;
	while (*e) ++e;
	for (C* b = s; b < --e; ++b) { C t = *b; *b = *e; *e = t; }
	return s;
}
#define _strrev civ5mac_strrev<char>
#define _wcsrev civ5mac_strrev<wchar_t>

#ifdef __cplusplus
// "Secure" CRT helpers: C++ linkage with unsigned long sizes, as the exe exports them.
int sprintf_s(char*, unsigned long, const char*, ...);
int vsprintf_s(char*, unsigned long, const char*, va_list);
int strcpy_s(char*, unsigned long, const char*);
int strncpy_s(char*, unsigned long, const char*, unsigned long);
int wcscpy_s(wchar_t*, unsigned long, const wchar_t*);
int _itoa_s(int, char*, unsigned long, int);
template <size_t N> inline int sprintf_s(char (&buf)[N], const char* fmt, ...)
{
	va_list ap;
	va_start(ap, fmt);
	int r = vsprintf_s(buf, N, fmt, ap);
	va_end(ap);
	return r;
}
template <size_t N> inline int vsprintf_s(char (&buf)[N], const char* fmt, va_list ap) { return vsprintf_s(buf, N, fmt, ap); }
template <size_t N> inline int strcpy_s(char (&buf)[N], const char* src) { return strcpy_s(buf, N, src); }
template <size_t N> inline int strncpy_s(char (&buf)[N], const char* src, unsigned long n) { return strncpy_s(buf, N, src, n); }
template <size_t N> inline int wcscpy_s(wchar_t (&buf)[N], const wchar_t* src) { return wcscpy_s(buf, N, src); }
template <size_t N> inline int _itoa_s(int v, char (&buf)[N], int radix) { return _itoa_s(v, buf, N, radix); }
inline int strcat_s(char* dst, unsigned long n, const char* src) { strlcat(dst, src, n); return 0; }
template <size_t N> inline int strcat_s(char (&buf)[N], const char* src) { return strcat_s(buf, N, src); }
inline int _snprintf_s(char* buf, size_t n, size_t, const char* fmt, ...)
{
	va_list ap;
	va_start(ap, fmt);
	int r = vsnprintf(buf, n, fmt, ap);
	va_end(ap);
	return r;
}
template <size_t N> inline int _snprintf_s(char (&buf)[N], size_t cnt, const char* fmt, ...)
{
	va_list ap;
	va_start(ap, fmt);
	int r = vsnprintf(buf, N, fmt, ap);
	va_end(ap);
	return r;
}
#endif

// ---------------------------------------------------------------------------
// Win32 API shims exported by the exe (C linkage).
// ---------------------------------------------------------------------------
#ifdef __cplusplus
extern "C" {
#endif
DWORD GetLastError(void);
void OutputDebugStringA(LPCSTR);
BOOL QueryPerformanceCounter(LARGE_INTEGER*);
BOOL QueryPerformanceFrequency(LARGE_INTEGER*);
HANDLE CreateFileW(LPCWSTR, DWORD, DWORD, LPSECURITY_ATTRIBUTES, DWORD, DWORD, HANDLE);
BOOL ReadFile(HANDLE, LPVOID, DWORD, LPDWORD, LPOVERLAPPED);
DWORD GetFileSize(HANDLE, LPDWORD);
BOOL CloseHandle(HANDLE);
BOOL DeleteFileW(LPCWSTR);
BOOL GetFileAttributesExW(LPCWSTR, GET_FILEEX_INFO_LEVELS, LPVOID);
int MultiByteToWideChar(UINT, DWORD, LPCSTR, int, LPWSTR, int);
HANDLE HeapCreate(DWORD, SIZE_T, SIZE_T);
BOOL HeapDestroy(HANDLE);
LPVOID HeapAlloc(HANDLE, DWORD, SIZE_T);
BOOL HeapFree(HANDLE, DWORD, LPVOID);
BOOL HeapSetInformation(HANDLE, HEAP_INFORMATION_CLASS, LPVOID, SIZE_T);
HRESULT CoCreateGuid(GUID*);
DWORD timeGetTime(void);
UINT timeBeginPeriod(UINT);
UINT timeEndPeriod(UINT);
#ifdef __cplusplus
}
#endif
#define OutputDebugString OutputDebugStringA

#ifdef __cplusplus
// The game core's single export (a .def file on Windows); everything else stays hidden.
class ICvGameContext1;
extern "C" __attribute__((visibility("default"))) ICvGameContext1* DllGetGameContext();

// The exe exports GetTempHeap with C linkage; FTempHeap.h's later C++ declaration inherits it.
class TempHeap;
extern "C" TempHeap* GetTempHeap();
#endif

#ifdef __cplusplus
// MSVC 2008 shipped TR1 in std::tr1 and hash_map in stdext.
namespace std { namespace tr1 {
using std::unordered_map; using std::unordered_set; using std::hash;
using std::shared_ptr; using std::weak_ptr; using std::make_shared; using std::enable_shared_from_this;
using std::static_pointer_cast; using std::dynamic_pointer_cast; using std::const_pointer_cast;
using std::function; using std::bind;
// MSVC 2008's tr1::array had assign(); std::array calls it fill().
using std::array;  // MSVC 2008's tr1::array::assign() is fixed up at its call site using std::ref; using std::cref; using std::tuple;
namespace placeholders { using namespace std::placeholders; }
} }
#endif

#ifdef __cplusplus
#include "msvc_sort.h"
#endif

// MSVC defines NULL as plain 0; overload resolution (e.g. CvString(int) vs
// CvString(const char*)) depends on it, so match Windows rather than clang's __null.
#undef NULL
#define NULL 0

#endif // CIV5MAC_PRELUDE_H
