// std::sort with the exact element-ordering behaviour of MSVC 2008 (Dinkumware STL),
// which the Windows game core is built with.
//
// std::sort is not stable, and different library implementations order *equivalent*
// elements differently. When the game core sorts AI candidates with tied scores, that
// order feeds straight into the simulation, so Mac and Windows must agree on it.
// Structure (from the VS2008 <algorithm> design):
//   * ranges of <= 32 elements: plain insertion sort (stable)
//   * otherwise: median-of-three / median-of-nine "fat" partition introsort, recursing
//     into the smaller side, with 1.5*log2(N) depth budget before heapsort fallback.
#pragma once
#include <iterator>
#include <utility>

namespace civ5mac {
namespace msvc_detail {

const long ISORT_MAX = 32;

template <class It, class Pr>
void insertion_sort(It first, It last, Pr pred)
{
	typedef typename std::iterator_traits<It>::value_type T;
	if (first == last)
		return;
	for (It next = first; ++next != last;)
	{
		It next1 = next;
		T val = *next;
		if (pred(val, *first))
		{
			std::copy_backward(first, next, ++next1);
			*first = val;
		}
		else
		{
			for (It first1 = next1; pred(val, *--first1); next1 = first1)
				*next1 = *first1;
			*next1 = val;
		}
	}
}

template <class It, class Pr>
void med3(It first, It mid, It last, Pr pred)
{
	if (pred(*mid, *first))
		std::iter_swap(mid, first);
	if (pred(*last, *mid))
		std::iter_swap(last, mid);
	if (pred(*mid, *first))
		std::iter_swap(mid, first);
}

template <class It, class Pr>
void median(It first, It mid, It last, Pr pred)
{
	if (40 < last - first)
	{
		size_t step = (last - first + 1) / 8;
		med3(first, first + step, first + 2 * step, pred);
		med3(mid - step, mid, mid + step, pred);
		med3(last - 2 * step, last - step, last, pred);
		med3(first + step, mid, last - step, pred);
	}
	else
		med3(first, mid, last, pred);
}

template <class It, class Pr>
std::pair<It, It> unguarded_partition(It first, It last, Pr pred)
{
	It mid = first + (last - first) / 2;
	median(first, mid, last - 1, pred);
	It pfirst = mid;
	It plast = pfirst + 1;

	while (first < pfirst && !pred(*(pfirst - 1), *pfirst) && !pred(*pfirst, *(pfirst - 1)))
		--pfirst;
	while (plast < last && !pred(*plast, *pfirst) && !pred(*pfirst, *plast))
		++plast;

	It gfirst = plast;
	It glast = pfirst;

	for (;;)
	{
		for (; gfirst < last; ++gfirst)
		{
			if (pred(*pfirst, *gfirst))
				;
			else if (pred(*gfirst, *pfirst))
				break;
			else
				std::iter_swap(plast++, gfirst);
		}
		for (; first < glast; --glast)
		{
			if (pred(*(glast - 1), *pfirst))
				;
			else if (pred(*pfirst, *(glast - 1)))
				break;
			else
				std::iter_swap(--pfirst, glast - 1);
		}
		if (glast == first && gfirst == last)
			return std::pair<It, It>(pfirst, plast);

		if (glast == first)
		{
			if (plast != gfirst)
				std::iter_swap(pfirst, plast);
			++plast;
			std::iter_swap(pfirst++, gfirst++);
		}
		else if (gfirst == last)
		{
			if (--glast != --pfirst)
				std::iter_swap(glast, pfirst);
			std::iter_swap(pfirst, --plast);
		}
		else
			std::iter_swap(gfirst++, --glast);
	}
}

template <class It, class Diff, class T, class Pr>
void push_heap_hole(It first, Diff hole, Diff top, T val, Pr pred)
{
	for (Diff idx = (hole - 1) / 2; top < hole && pred(*(first + idx), val); idx = (hole - 1) / 2)
	{
		*(first + hole) = *(first + idx);
		hole = idx;
	}
	*(first + hole) = val;
}

template <class It, class Diff, class T, class Pr>
void adjust_heap(It first, Diff hole, Diff bottom, T val, Pr pred)
{
	Diff top = hole;
	Diff idx = 2 * hole + 2;
	for (; idx < bottom; idx = 2 * idx + 2)
	{
		if (pred(*(first + idx), *(first + (idx - 1))))
			--idx;
		*(first + hole) = *(first + idx);
		hole = idx;
	}
	if (idx == bottom)
	{
		*(first + hole) = *(first + (bottom - 1));
		hole = bottom - 1;
	}
	push_heap_hole(first, hole, top, val, pred);
}

template <class It, class Pr>
void heap_sort(It first, It last, Pr pred)
{
	typedef typename std::iterator_traits<It>::difference_type Diff;
	typedef typename std::iterator_traits<It>::value_type T;
	Diff bottom = last - first;
	for (Diff hole = bottom / 2; 0 < hole;)
	{
		--hole;
		adjust_heap(first, hole, bottom, T(*(first + hole)), pred);
	}
	for (; 1 < last - first; --last)
	{
		T val = *(last - 1);
		*(last - 1) = *first;
		adjust_heap(first, Diff(0), Diff((last - 1) - first), val, pred);
	}
}

template <class It, class Diff, class Pr>
void sort_impl(It first, It last, Diff ideal, Pr pred)
{
	Diff count;
	for (; ISORT_MAX < (count = last - first) && 0 < ideal;)
	{
		std::pair<It, It> mid = unguarded_partition(first, last, pred);
		ideal /= 2, ideal += ideal / 2;
		if (mid.first - first < last - mid.second)
		{
			sort_impl(first, mid.first, ideal, pred);
			first = mid.second;
		}
		else
		{
			sort_impl(mid.second, last, ideal, pred);
			last = mid.first;
		}
	}
	if (ISORT_MAX < count)
		heap_sort(first, last, pred);
	else if (1 < count)
		insertion_sort(first, last, pred);
}

struct less_op
{
	// MSVC compares *it directly, so operator< may be a non-const member.
	template <class A, class B> bool operator()(A& a, B& b) const { return a < b; }
};

} // namespace msvc_detail

template <class It, class Pr>
inline void msvc_sort(It first, It last, Pr pred)
{
	msvc_detail::sort_impl(first, last, last - first, pred);
}

template <class It>
inline void msvc_sort(It first, It last)
{
	msvc_detail::sort_impl(first, last, last - first, msvc_detail::less_op());
}

} // namespace civ5mac
