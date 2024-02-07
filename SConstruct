#!/usr/bin/env python

import os
import platform
import sys
import subprocess
from pathlib import Path
from SCons.Errors import UserError

EnsureSConsVersion(4, 0)


def add_sources(sources, dir, extension):
    for f in os.listdir(dir):
        if f.endswith("." + extension):
            sources.append(dir + "/" + f)


def normalize_path(val):
    return val if os.path.isabs(val) else os.path.join(env.Dir("#").abspath, val)


# Try to detect the host platform automatically.
# This is used if no `platform` argument is passed
if sys.platform == "darwin":
    default_platform = "macos"
elif sys.platform == "win32" or sys.platform == "msys":
    default_platform = "windows"
elif ARGUMENTS.get("platform", ""):
    default_platform = ARGUMENTS.get("platform")
else:
    raise ValueError("Could not detect platform automatically, please specify with platform=<platform>")

try:
    Import("env")
except:
    # Default tools with no platform defaults to gnu toolchain.
    # We apply platform specific toolchains via our custom tools.
    env = Environment(tools=["default"], PLATFORM="")

env.PrependENVPath("PATH", os.getenv("PATH"))

# Default num_jobs to local cpu count if not user specified.
# SCons has a peculiarity where user-specified options won't be overridden
# by SetOption, so we can rely on this to know if we should use our default.
initial_num_jobs = env.GetOption("num_jobs")
altered_num_jobs = initial_num_jobs + 1
env.SetOption("num_jobs", altered_num_jobs)
if env.GetOption("num_jobs") == altered_num_jobs:
    cpu_count = os.cpu_count()
    if cpu_count is None:
        print("Couldn't auto-detect CPU count to configure build parallelism. Specify it with the -j argument.")
    else:
        safer_cpu_count = cpu_count if cpu_count <= 4 else cpu_count - 1
        print(
            "Auto-detected %d CPU cores available for build parallelism. Using %d cores by default. You can override it with the -j argument."
            % (cpu_count, safer_cpu_count)
        )
        env.SetOption("num_jobs", safer_cpu_count)

# Custom options and profile flags.
customs = ["custom.py"]
profile = ARGUMENTS.get("profile", "")
if profile:
    if os.path.isfile(profile):
        customs.append(profile)
    elif os.path.isfile(profile + ".py"):
        customs.append(profile + ".py")
opts = Variables(customs, ARGUMENTS)

platforms = ("macos", "windows")
opts.Add(
    EnumVariable(
        key="platform",
        help="Target platform",
        default=env.get("platform", default_platform),
        allowed_values=platforms,
        ignorecase=2,
    )
)

# Add platform options
tools = {}
for pl in platforms:
    tool = Tool(pl, toolpath=["godot-tools"])
    if hasattr(tool, "options"):
        tool.options(opts)
    tools[pl] = tool

# CPU architecture options.
architecture_array = ["", "universal", "x86_32", "x86_64", "arm32", "arm64", "rv64", "ppc32", "ppc64", "wasm32"]
architecture_aliases = {
    "x64": "x86_64",
    "amd64": "x86_64",
    "armv7": "arm32",
    "armv8": "arm64",
    "arm64v8": "arm64",
    "aarch64": "arm64",
    "rv": "rv64",
    "riscv": "rv64",
    "riscv64": "rv64",
    "ppcle": "ppc32",
    "ppc": "ppc32",
    "ppc64le": "ppc64",
}
opts.Add(
    EnumVariable(
        key="arch",
        help="CPU architecture",
        default=env.get("arch", ""),
        allowed_values=architecture_array,
        map=architecture_aliases,
    )
)

opts.Add("cppdefines", "Custom defines for the pre-processor")
opts.Add("ccflags", "Custom flags for both the C and C++ compilers")
opts.Add("cxxflags", "Custom flags for the C++ compiler")
opts.Add("cflags", "Custom flags for the C compiler")
opts.Add("linkflags", "Custom flags for the linker")
opts.Add("extra_suffix", "Custom extra suffix added to the base filename of all generated binary files.", "")

# Targets flags tool (optimizations, debug symbols)
target_tool = Tool("targets", toolpath=["godot-tools"])
target_tool.options(opts)

opts.Update(env)
Help(opts.GenerateHelpText(env))

# Process CPU architecture argument.
if env["arch"] == "":
    # No architecture specified. Default to arm64 if building for Android,
    # universal if building for macOS or iOS, wasm32 if building for web,
    # otherwise default to the host architecture.
    if env["platform"] in ["macos", "ios"]:
        env["arch"] = "universal"
    else:
        host_machine = platform.machine().lower()
        if host_machine in architecture_array:
            env["arch"] = host_machine
        elif host_machine in architecture_aliases.keys():
            env["arch"] = architecture_aliases[host_machine]
        elif "86" in host_machine:
            # Catches x86, i386, i486, i586, i686, etc.
            env["arch"] = "x86_32"
        else:
            print("Unsupported CPU architecture: " + host_machine)
            Exit()

tool = Tool(env["platform"], toolpath=["godot-tools"])

if tool is None or not tool.exists(env):
    raise ValueError("Required toolchain not found for platform " + env["platform"])

tool.generate(env)
target_tool.generate(env)

# Detect and print a warning listing unknown SCons variables to ease troubleshooting.
unknown = opts.UnknownVariables()
if unknown:
    print("WARNING: Unknown SCons variables were passed and will be ignored:")
    for item in unknown.items():
        print("    " + item[0] + "=" + item[1])

print("Building for architecture " + env["arch"] + " on platform " + env["platform"])

env.Append(CPPDEFINES=env.get("cppdefines", "").split())
env.Append(CCFLAGS=env.get("ccflags", "").split())
env.Append(CXXFLAGS=env.get("cxxflags", "").split())
env.Append(CFLAGS=env.get("cflags", "").split())
env.Append(LINKFLAGS=env.get("linkflags", "").split())

# Require C++17
if env.get("is_msvc", False):
    env.Append(CXXFLAGS=["/std:c++17"])
else:
    env.Append(CXXFLAGS=["-std=c++17"])

if env["platform"] == "macos":
    # CPU architecture.
    if env["arch"] == "arm64":
        print("Building for macOS 11.0+.")
        env.Append(ASFLAGS=["-mmacosx-version-min=11.0"])
        env.Append(CCFLAGS=["-mmacosx-version-min=11.0"])
        env.Append(LINKFLAGS=["-mmacosx-version-min=11.0"])
    elif env["arch"] == "x86_64":
        print("Building for macOS 10.13+.")
        env.Append(ASFLAGS=["-mmacosx-version-min=10.13"])
        env.Append(CCFLAGS=["-mmacosx-version-min=10.13"])
        env.Append(LINKFLAGS=["-mmacosx-version-min=10.13"])
elif env["platform"] == "windows":
    env.AppendUnique(CPPDEFINES=["WINVER=0x0603", "_WIN32_WINNT=0x0603"])


scons_cache_path = os.environ.get("SCONS_CACHE")
if scons_cache_path is not None:
    CacheDir(scons_cache_path)
    Decider("MD5")

mesa_dir = "#godot-mesa"
mesa_gen_dir = "#godot-mesa/generated"
mesa_absdir = Dir(mesa_dir).abspath
mesa_gen_absdir = Dir(mesa_dir + "/generated").abspath

custom_build_steps = [
    [
        "src/compiler",
        "glsl/ir_expression_operation.py enum > %s/ir_expression_operation.h",
        "ir_expression_operation.h",
    ],
    ["src/compiler/nir", "nir_builder_opcodes_h.py > %s/nir_builder_opcodes.h", "nir_builder_opcodes.h"],
    ["src/compiler/nir", "nir_constant_expressions.py > %s/nir_constant_expressions.c", "nir_constant_expressions.c"],
    ["src/compiler/nir", "nir_intrinsics_h.py --outdir %s", "nir_intrinsics.h"],
    ["src/compiler/nir", "nir_intrinsics_c.py --outdir %s", "nir_intrinsics.c"],
    ["src/compiler/nir", "nir_intrinsics_indices_h.py --outdir %s", "nir_intrinsics_indices.h"],
    ["src/compiler/nir", "nir_opcodes_h.py > %s/nir_opcodes.h", "nir_opcodes.h"],
    ["src/compiler/nir", "nir_opcodes_c.py > %s/nir_opcodes.c", "nir_opcodes.c"],
    ["src/compiler/nir", "nir_opt_algebraic.py > %s/nir_opt_algebraic.c", "nir_opt_algebraic.c"],
    ["src/compiler/spirv", "vtn_generator_ids_h.py spir-v.xml %s/vtn_generator_ids.h", "vtn_generator_ids.h"],
    [
        "src/microsoft/compiler",
        "dxil_nir_algebraic.py -p ../../../src/compiler/nir > %s/dxil_nir_algebraic.c",
        "dxil_nir_algebraic.c",
    ],
    ["src/util", "format_srgb.py > %s/format_srgb.c", "format_srgb.c"],
    ["src/util/format", "u_format_table.py u_format.csv --header > %s/u_format_pack.h", "u_format_pack.h"],
    ["src/util/format", "u_format_table.py u_format.csv > %s/u_format_table.c", "u_format_table.c"],
]

mesa_sources = []
mesa_gen_headers = []
mesa_gen_sources = []
mesa_gen_include_paths = [mesa_gen_dir + "/src"]

# See update_mesa.sh for explanation.
for v in custom_build_steps:
    subdir = v[0]
    cmd = v[1]
    gen_filename = v[2]

    in_dir = str(Path(mesa_absdir + "/" + subdir))
    out_dir = str(Path(mesa_absdir + "/generated/" + subdir))
    script_filename = cmd.split()[0]
    out_full_path = mesa_dir + "/generated/" + subdir
    out_file_full_path = out_full_path + "/" + gen_filename

    if gen_filename.endswith(".h"):
        mesa_gen_include_paths += [out_full_path]
        mesa_gen_headers += [out_file_full_path]
    else:
        mesa_gen_sources += [out_file_full_path]

mesa_private_inc_paths = [v[0] for v in os.walk(mesa_absdir)]
mesa_private_inc_paths = [v.replace(mesa_absdir, mesa_dir) for v in mesa_private_inc_paths]
mesa_private_inc_paths = [v.replace("\\", "/") for v in mesa_private_inc_paths]
# Avoid build results depending on if generated files already exist.
mesa_private_inc_paths = [v for v in mesa_private_inc_paths if not v.startswith(mesa_gen_dir)]
mesa_private_inc_paths.sort()
# Include the list of the generated ones now, so out-of-the-box sources can include generated headers.
mesa_private_inc_paths += mesa_gen_include_paths
# We have to blacklist some because we are bindly adding every Mesa directory
# to the include path and in some cases that causes the wrong header to be included.
mesa_blacklist_inc_paths = [
    "src/c11",
]
mesa_blacklist_inc_paths = [mesa_dir + "/" + v for v in mesa_blacklist_inc_paths]
mesa_private_inc_paths = [v for v in mesa_private_inc_paths if v not in mesa_blacklist_inc_paths]
# Prepending these to avoid some conflicts, at least with OS GL headers.
env.Prepend(CPPPATH=mesa_private_inc_paths)

mesa_sources += [v for v in list(Path(mesa_absdir).rglob("*.c"))]
mesa_sources += [v for v in list(Path(mesa_absdir).rglob("*.cpp"))]
mesa_sources = [str(v).replace(mesa_absdir, mesa_dir) for v in mesa_sources]
mesa_sources = [v.replace("\\", "/") for v in mesa_sources]
# Avoid build results depending on if generated files already exist.
mesa_sources = [v for v in mesa_sources if not v.startswith(mesa_gen_dir)]
mesa_sources.sort()
# Include the list of the generated ones now.
mesa_sources += mesa_gen_sources

# Clean C/C++/both flags to avoid std clashes.
for key in ["CFLAGS", "CXXFLAGS", "CCFLAGS"]:
    env[key] = [v for v in env[key] if "/std:" not in v and "-std=" not in v]

# Added by ourselves.
extra_defines = [
    "WINDOWS_NO_FUTEX",
]

# These defines are inspired by the Meson build scripts in the original repo.
extra_defines += [
    "__STDC_CONSTANT_MACROS",
    "__STDC_FORMAT_MACROS",
    "__STDC_LIMIT_MACROS",
    ("PACKAGE_VERSION", '\\"' + Path(mesa_absdir + "/VERSION").read_text().strip() + '\\"'),
    ("PACKAGE_BUGREPORT", '\\"https://gitlab.freedesktop.org/mesa/mesa/-/issues\\"'),
    "PIPE_SUBSYSTEM_WINDOWS_USER",
    "_USE_MATH_DEFINES",
]

if env.get("is_msvc", False):
    extra_defines += [
        "_USE_MATH_DEFINES",
        "VC_EXTRALEAN",
        "_CRT_SECURE_NO_WARNINGS",
        "_CRT_SECURE_NO_DEPRECATE",
        "_SCL_SECURE_NO_WARNINGS",
        "_SCL_SECURE_NO_DEPRECATE",
        "_ALLOW_KEYWORD_MACROS",
        ("_HAS_EXCEPTIONS", 0),
        "NOMINMAX",
        "HAVE_STRUCT_TIMESPEC",
        "HAVE_TIMESPEC_GET",
        ("_Static_assert", "static_assert"),
    ]
    env.Append(CFLAGS=["/std:c11"])
else:
    env.Append(
        CPPDEFINES=[
            ("__MSVCRT_VERSION__", 0x0700),
            "HAVE_STRUCT_TIMESPEC",
        ]
    )
    env.Append(CFLAGS=["-std=c11"])
    env.Append(CXXFLAGS=["-fno-exceptions"])

if env.get("use_llvm", False):
    extra_defines += [
        "HAVE_TIMESPEC_GET",
        "_UCRT",
    ]

env.Append(CPPDEFINES=extra_defines)
env.Append(CPPPATH=".")
env.Append(CPPPATH="#vulkan/include")

suffix = ".{}.{}".format(env["platform"], env["arch"])
if env.get("extra_suffix", "") != "":
    suffix += "." + env["extra_suffix"]

# Expose it when included from another project
env["suffix"] = suffix

library = None
env["OBJSUFFIX"] = suffix + env["OBJSUFFIX"]
library_name = "libNIR{}{}".format(suffix, env["LIBSUFFIX"])

library = env.StaticLibrary(name="NIR", target=env.File("bin/%s" % library_name), source=mesa_sources)

Return("env")
