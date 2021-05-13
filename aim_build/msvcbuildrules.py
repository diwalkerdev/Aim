def add_compile(nfw):
    # Note, there cannot be a space between /Fo and $out
    command = "$compiler $flags $defines $includes /showIncludes /c $in /Fo$out"
    nfw.rule(
        name="compile",
        description="Compile source files to object files",
        deps="msvc",
        depfile="deps.d",
        command=command,
    )
    nfw.newline()


def add_ar(nfw):
    nfw.rule(
        name="archive",
        description="Combine object files into an archive",
        command="llvm-ar cr $out $in",
    )
    nfw.newline()


def add_exe(nfw):
    command = (
        "$compiler $flags $defines $includes $in /link /out:$exe_name $linker_args"
    )
    nfw.rule(name="exe", description="Build an executable.", command=command)
    nfw.newline()


def add_shared(nfw):
    command = "$compiler $flags $defines $includes $in /link /DLL /out:$lib_name $linker_args"
    nfw.rule(name="shared", description="Build a shared library.", command=command)
    nfw.newline()
