// Replaces the SDK's Win32 header funnel: the prelude already provides the Win32 surface.
#pragma once
#include "prelude.h"
// FFastVector.h names c_eMPoolTypeContainer in default template arguments without
// including its definition; MSVC 2008 parsed those lazily, clang does not.
#include "FMemHooks.h"
