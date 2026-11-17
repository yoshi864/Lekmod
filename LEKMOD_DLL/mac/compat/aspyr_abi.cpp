// Interface methods Aspyr added to the Mac game core. The exe calls them by vtable slot,
// so they must exist in the same position (see the matching fixups.py rules), even
// though Firaxis' source and the Windows game never had them.
#include "CvGameCoreDLLPCH.h"
#include "CvDllPreGame.h"

// ICvPreGame1 slot 28, after era(): the current era's Type string (e.g. "ERA_ANCIENT").
// Reconstructed from Aspyr's body: GC.getEraInfo(s_era), then its m_strType as a std::string.
std::string CvDllPreGame::eraType()
{
	CvEraInfo* pkEra = GC.getEraInfo(CvPreGame::era());
	const char* szType = pkEra ? pkEra->GetType() : NULL;
	return szType ? szType : "";
}
