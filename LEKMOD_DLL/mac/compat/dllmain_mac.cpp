// Windows calls DllMain when the game core is loaded/unloaded; dyld does not. Drive
// the game core's own DllMain from the dylib's load/unload hooks so initialization
// (CvDllGameContext::InitializeSingleton, timer resolution) is exactly as on Windows.
#include "prelude.h"
#include <dlfcn.h>

BOOL APIENTRY DllMain(HANDLE hModule, DWORD ul_reason_for_call, LPVOID);

__attribute__((constructor)) static void civ5mac_process_attach()
{
	// Stay mapped after the exe's FreeLibrary (dlclose): Lua states outlive the game
	// core and still hold its C functions (CvLuaFractal's __gc runs at lua_close on
	// quit). Aspyr's game core registers the same finalizer and must stay mapped too.
	Dl_info kInfo;
	if (dladdr((const void*)&civ5mac_process_attach, &kInfo) && kInfo.dli_fname)
		dlopen(kInfo.dli_fname, RTLD_NOLOAD | RTLD_NODELETE);

	DllMain(NULL, DLL_PROCESS_ATTACH, NULL);
}

__attribute__((destructor)) static void civ5mac_process_detach()
{
	DllMain(NULL, DLL_PROCESS_DETACH, NULL);
}
