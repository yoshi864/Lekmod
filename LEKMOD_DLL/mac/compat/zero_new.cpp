// The game core's objects are allocated once at load (players, infos, managers) with plain
// new. On Windows that memory comes from fresh heap pages and reads as zero, so members the
// sources never initialise (LekMod has several) are 0/false there. libc++'s operator new does
// not clear memory: zero it here too, so such members start out as they do on Windows.
// These definitions bind only within the game core dylib.
#include <cstdlib>
#include <new>

void* operator new(size_t n)
{
	if (void* p = calloc(1, n ? n : 1))
		return p;
	throw std::bad_alloc();
}
void* operator new[](size_t n) { return operator new(n); }
void* operator new(size_t n, const std::nothrow_t&) throw() { return calloc(1, n ? n : 1); }
void* operator new[](size_t n, const std::nothrow_t&) throw() { return calloc(1, n ? n : 1); }
void operator delete(void* p) throw() { free(p); }
void operator delete[](void* p) throw() { free(p); }
void operator delete(void* p, size_t) throw() { free(p); }
void operator delete[](void* p, size_t) throw() { free(p); }
