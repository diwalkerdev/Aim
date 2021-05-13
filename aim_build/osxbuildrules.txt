from ninja_syntax import Writer


def add_compile(nfw: Writer):
    command = f"$compiler $defines $flags -MMD -MF deps.d $includes -c $in -o $out"
    nfw.rule(
        name="compile",
        description="Compiles source files into object files",
        deps="gcc",
        depfile="deps.d",
        command=command,
    )
    nfw.newline()


def add_ar(nfw: Writer):
    nfw.rule(
        name="archive",
        description="Combine object files into an archive",
        command="$archiver cr $out $in",
    )
    nfw.newline()


def add_exe(nfw: Writer):
    # TODO: origin should only really be added when we need to link against an so.
    command = f"$compiler $defines $flags $includes $in -o $exe_name $linker_args"
    nfw.rule(name="exe", description="Builds an executable.", command=command)
    nfw.newline()


def add_shared(nfw: Writer):
    command = f"$compiler $defines -shared -fvisibility=hidden -fPIC $flags $includes $in -o $out $linker_args"
    nfw.rule(name="shared", description="Builds a shared library.", command=command)
    nfw.newline()
