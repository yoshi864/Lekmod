// Sizes of objects the game core allocates but Aspyr's exe constructs or operates on.
// Each value was read from the exe's own code (constructor writes / member offsets);
// a mismatch means the exe would write outside our object.
#include "CvGameCoreDLLPCH.h"

static_assert(sizeof(CRITICAL_SECTION) == 40, "FCriticalSection ctor writes 0x00-0x27");
static_assert(sizeof(GUID) == 16, "Win32 GUID");
static_assert(sizeof(FStringA::FStringAData) == 12, "FString text starts 0xc after its header");
static_assert(sizeof(FStringW::FStringWData) == 12, "FString text starts 0xc after its header");
static_assert(sizeof(FStringA) == sizeof(void*), "FString is a lone pointer");
static_assert(sizeof(Database::Connection) == 0xb8, "Connection::Open reads the logger at 0xb0");
static_assert(sizeof(Database::Results) == 0x70, "Aspyr's game core spaces stack Results 0x70 apart (72-byte hash_map at 0x28)");
static_assert(sizeof(Localization::String) == 0x90, "String() initializes SharedStrings at 0x08/0x30, zeroes to 0x90");
static_assert(sizeof(DWORD) == 4 && sizeof(dword) == 4, "Win32 32-bit DWORD");
