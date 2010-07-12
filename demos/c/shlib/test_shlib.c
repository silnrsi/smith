
#ifdef _MSC_VER
#	define test_EXPORT __declspec(dllexport)
#else
#	define test_EXPORT
#endif

extern test_EXPORT void foo() { }

static const int truc=5;

void foo() { }

