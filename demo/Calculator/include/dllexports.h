#pragma once

#if defined(_MSC_VER)
#define DLL_EXPORT __declspec(dllexport)
#define DLL_IMPORT __declspec(dllimport)
#elif defined(__GNUC__)
#define DLL_EXPORT __attribute__((visibility("default")))
#define DLL_IMPORT
#elif defined(__clang__)
#define DLL_EXPORT __attribute__((visibility("default")))
#define DLL_IMPORT
#else
#define DLL_EXPORT
#define DLL_IMPORT
#warning Unknown dynamic link import / export semantics.
#endif

#if defined(EXPORT_DLL_PUBLIC)
#define DLL_PUBLIC DLL_EXPORT
#else
#define DLL_PUBLIC DLL_IMPORT
#endif
