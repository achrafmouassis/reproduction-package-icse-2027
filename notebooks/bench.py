import marimo

__generated_with = "0.23.4"
app = marimo.App(width="medium")


@app.cell
def _():
    import subprocess
    import shutil
    import os
    import random
    from tqdm import tqdm
    import time
    from pathlib import Path

    return Path, os, random, shutil, subprocess, tqdm


@app.cell
def _(Path):
    GSON_PATH = "gson"
    TOKEN_PATTERN = "(?P<plugin>[\w-]+):(?P<version>[\d.]+):(?P<goal>[\w-]+)\s+\((?P<id>[^)]+)\)\s+@\s+(?P<module>[\w-]+)"
    OUTPUT_DIR = Path("results")
    HOME = Path.home()
    MAVEN_BIN = "mvn"
    return GSON_PATH, HOME, MAVEN_BIN, OUTPUT_DIR, TOKEN_PATTERN


@app.cell
def _(HOME, shutil):
    def clear_m2():
        shutil.rmtree(f"{HOME}/.m2", ignore_errors=True)

    return (clear_m2,)


@app.cell
def _(TOKEN_PATTERN, subprocess):
    def profiler_exec(cmd, profiler_args=[], output_file="profiler_output.csv", sockets=[], profiler_path="joule-profiler", taskset=None, perf_counters=False, nvml=False, profiler_taskset=None, token_pattern=TOKEN_PATTERN):
        perf_counters_args = ["--perf"] if perf_counters else []
        nvml_args = ["--gpu"] if nvml else []
        socket_args = ["--sockets", *[str(socket) for socket in sockets]] if sockets else []
        token_pattern_args = ["--token-pattern", token_pattern] if token_pattern else []
        base = [profiler_path, *perf_counters_args, *nvml_args, *socket_args, "-o", output_file, "--json", *[str(arg) for arg in profiler_args], "profile", *token_pattern_args, "--"]
        taskset_args = ["taskset", "-c", taskset] if taskset else []
        profiler_taskset_args = ["taskset", "-c", profiler_taskset] if profiler_taskset else []
        full = [*profiler_taskset_args, *base, *taskset_args, *cmd.split()]
        return subprocess.Popen(full, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


    return (profiler_exec,)


@app.cell
def _(GSON_PATH, subprocess):
    def git_restore():
        cmd = ["git", "-C", GSON_PATH, "restore", "."]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate()
        status = p.wait()
        return status

    return


@app.cell
def _(GSON_PATH, subprocess):
    def checkout_version(version):
        cmd = ["git", "-C", GSON_PATH, "checkout", f"gson-parent-{version}"]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate()
        status = p.wait()
        return status

    return (checkout_version,)


@app.cell
def _(GSON_PATH, MAVEN_BIN, shutil, subprocess):
    def clean():
        cmd = f"{MAVEN_BIN} -f {GSON_PATH}/pom.xml clean".split(" ")
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate()
        status = p.wait()
        shutil.rmtree(f"{GSON_PATH}/target", ignore_errors=True)
        return status

    return (clean,)


@app.cell
def _(
    GSON_PATH,
    MAVEN_BIN,
    OUTPUT_DIR,
    checkout_version,
    clean,
    clear_m2,
    os,
    profiler_exec,
    random,
    tqdm,
):
    ITER = 40
    VERSIONS = ["2.12.1", "2.13.0", "2.13.1", "2.13.2", "2.14.0"]
    sockets = [0]
    process_pinning = "2"
    profiler_pinning = "4"

    for i in tqdm(range(ITER), delay=1):
        random.shuffle(VERSIONS)
        for version in VERSIONS:
            output_dir = OUTPUT_DIR / version / f"iter_{i}"
            os.makedirs(output_dir, exist_ok=True)

            print(f"Version {version} - iter {i}")

            clean()
            checkout_version(version)
            clear_m2()

            output_file = output_dir / "cold_build.json"

            proc = profiler_exec(f"{MAVEN_BIN} -f {GSON_PATH}/pom.xml package", output_file=output_file, taskset=process_pinning, sockets=sockets, profiler_taskset=profiler_pinning)
            out, err = proc.communicate()
            status = proc.wait()
            if proc.wait() != 0:
                raise RuntimeError(f"Error: {err}")

            clean()

            output_file = output_dir / "warm_build.json"

            proc = profiler_exec(f"{MAVEN_BIN} -f {GSON_PATH}/pom.xml package", output_file=output_file, taskset=process_pinning, sockets=sockets, profiler_taskset=profiler_pinning)

            out, err = proc.communicate()
            status = proc.wait()
            if proc.wait() != 0:
                raise RuntimeError(f"Error: {err}")
    return


if __name__ == "__main__":
    app.run()
