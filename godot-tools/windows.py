import sys

import my_spawn

from SCons.Tool import msvc, mingw
from SCons.Variables import *


def options(opts):
    mingw = os.getenv("MINGW_PREFIX", "")

    opts.Add(BoolVariable("use_mingw", "Use the MinGW compiler instead of MSVC - only effective on Windows", False))
    opts.Add(BoolVariable("use_clang_cl", "Use the clang driver instead of MSVC - only effective on Windows", False))
    opts.Add(BoolVariable("use_static_cpp", "Link MinGW/MSVC C++ runtime libraries statically", True))
    opts.Add(BoolVariable("debug_crt", "Compile with MSVC's debug CRT (/MDd)", False))
    opts.Add(BoolVariable("use_llvm", "Use the LLVM compiler", False))
    opts.Add("mingw_prefix", "MinGW prefix", mingw)


def exists(env):
    return True


def generate(env):
    base = None
    if not env["use_mingw"] and msvc.exists(env):
        if env["arch"] == "x86_64":
            env["TARGET_ARCH"] = "amd64"
        elif env["arch"] == "arm64":
            env["TARGET_ARCH"] = "arm64"
        elif env["arch"] == "arm32":
            env["TARGET_ARCH"] = "arm"
        elif env["arch"] == "x86_32":
            env["TARGET_ARCH"] = "x86"

        env["MSVC_SETUP_RUN"] = False  # Need to set this to re-run the tool
        env["MSVS_VERSION"] = None
        env["MSVC_VERSION"] = None

        env["is_msvc"] = True

        # MSVC, linker, and archiver.
        msvc.generate(env)
        env.Tool("msvc")
        env.Tool("mslib")
        env.Tool("mslink")

        env.Append(CPPDEFINES=["TYPED_METHOD_BIND", "NOMINMAX"])
        env.Append(CCFLAGS=["/EHsc", "/utf-8"])
        if env["debug_crt"]:
            # Always use dynamic runtime, static debug CRT breaks thread_local.
            env.AppendUnique(CCFLAGS=["/MDd"])
        else:
            if env["use_static_cpp"]:
                env.AppendUnique(CCFLAGS=["/MT"])
            else:
                env.AppendUnique(CCFLAGS=["/MD"])
        env.Append(LINKFLAGS=["/WX"])

        if env["use_clang_cl"]:
            env["CC"] = "clang-cl"
            env["CXX"] = "clang-cl"

    elif (sys.platform == "win32" or sys.platform == "msys") and not env["mingw_prefix"]:
        env["use_mingw"] = True
        mingw.generate(env)
        env.Append(CPPDEFINES=["MINGW_ENABLED"])
        # Don't want lib prefixes
        env["IMPLIBPREFIX"] = ""
        env["SHLIBPREFIX"] = ""
        # Want dll suffix
        env["SHLIBSUFFIX"] = ".dll"
        # Long line hack. Use custom spawn, quick AR append (to avoid files with the same names to override each other).
        my_spawn.configure(env)

    else:
        env["use_mingw"] = True
        # Cross-compilation using MinGW
        prefix = ""
        if env["mingw_prefix"]:
            prefix = env["mingw_prefix"] + "/bin/"

        if env["arch"] == "x86_64":
            prefix += "x86_64"
        elif env["arch"] == "arm64":
            prefix += "aarch64"
        elif env["arch"] == "arm32":
            prefix += "armv7"
        elif env["arch"] == "x86_32":
            prefix += "i686"

        if env["use_llvm"]:
            env["CXX"] = prefix + "-w64-mingw32-clang++"
            env["CC"] = prefix + "-w64-mingw32-clang"
            env["AR"] = prefix + "-w64-mingw32-ar"
            env["RANLIB"] = prefix + "-w64-mingw32-ranlib"
            env["LINK"] = prefix + "-w64-mingw32-clang"
        else:
            env["CXX"] = prefix + "-w64-mingw32-g++"
            env["CC"] = prefix + "-w64-mingw32-gcc"
            env["AR"] = prefix + "-w64-mingw32-gcc-ar"
            env["RANLIB"] = prefix + "-w64-mingw32-ranlib"
            env["LINK"] = prefix + "-w64-mingw32-g++"

        env.Append(CPPDEFINES=["MINGW_ENABLED"])
        env.Append(CCFLAGS=["-O3", "-Wwrite-strings"])
        if env["arch"] == "x86_32":
            if env["use_static_cpp"]:
                env.Append(LINKFLAGS=["-static"])
                env.Append(LINKFLAGS=["-static-libgcc"])
                env.Append(LINKFLAGS=["-static-libstdc++"])
        else:
            if env["use_static_cpp"]:
                env.Append(LINKFLAGS=["-static"])
        env.Append(
            LINKFLAGS=[
                "-Wl,--no-undefined",
            ]
        )

        if (sys.platform == "win32" or sys.platform == "msys"):
            my_spawn.configure(env)
