// MolRecognizer's Windows-only runtime relocation helper for OSRA 2.2.4.
// Distributed under OSRA's GPL-2.0-or-later terms; see the accompanying sources.
#pragma once
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <cstdlib>
#include <string>

static void osra_configure_portable_runtime()
{
    char executable[32768];
    DWORD length = GetModuleFileNameA(NULL, executable, sizeof(executable));
    if (!length || length >= sizeof(executable)) return;
    std::string directory(executable, length);
    directory.resize(directory.find_last_of("/\\")); // bin
    directory.resize(directory.find_last_of("/\\")); // runtime root
    const auto use_directory = [&directory](const char* variable, const char* relative) {
        const std::string path = directory + relative;
        const DWORD attributes = GetFileAttributesA(path.c_str());
        if (attributes != INVALID_FILE_ATTRIBUTES && (attributes & FILE_ATTRIBUTE_DIRECTORY))
            _putenv_s(variable, path.c_str());
    };
    use_directory("BABEL_DATADIR", "/share/openbabel");
    use_directory("MAGICK_CODER_MODULE_PATH", "/lib/GraphicsMagick/modules");
    use_directory("MAGICK_CONFIGURE_PATH", "/lib/GraphicsMagick/config");
    use_directory("FONTCONFIG_PATH", "/etc/fonts");
}
#else
static void osra_configure_portable_runtime() {}
#endif
