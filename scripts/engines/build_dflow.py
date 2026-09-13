"""Reproducible local D-Flow build using official source recipes and LF Dockerfiles.

Run after the pinned sparse checkout and the buildtools / thirdparty images exist.
The generated Dockerfile changes container locations and bounds build concurrency;
it does not change hydraulic source code.
"""
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
source=ROOT/"external/Delft3D"
original=(source/"doc/delft3d.Dockerfile").read_text(encoding="utf-8")
# The official runtime base is private; the public Alma base supplies the OS layer.
dockerfile=ROOT/"scripts/engines/DFlowRuntime.Dockerfile"
text=original.replace("ARG CONFIGURATION=all","ARG CONFIGURATION=fm-suite")
text=text.replace("RUN --mount=type=cache,target=/source/build", "ENV CMAKE_BUILD_PARALLEL_LEVEL=4\nRUN --mount=type=cache,target=/source/build")
# At this pinned source revision a test-only CMake rule unconditionally copies
# a Windows MSVC DLL. Remove that rule in the Linux build layer; hydraulic
# source code and the checked-out Git tree remain untouched.
test_cmake="/source/src/engines_gpl/dflowfm/packages/dflowfm_kernel/test/CMakeLists.txt"
text=text.replace("COPY . .\n", "COPY . .\nRUN grep -q 'third_party_open/pthreads/bin/x64/msvcr100.dll' " + test_cmake + " && sed -i '/# Copy pthreads runtime dependency/,/^)/d' " + test_cmake + "\n",1)
dockerfile.write_text(text,encoding="utf-8",newline="\n")
with (ROOT/"docs/evidence/phase2/dflow-runtime-build.log").open("w",encoding="utf-8") as log:
    result=subprocess.run(["docker","build","-f",str(dockerfile),
        "--build-arg","THIRDPARTYLIBS_IMAGE_URL=damsafe-dflow-thirdparty",
        "--build-arg","BASE_TAG=oneapi-2024","--build-arg","BASE_IMAGE_URL=almalinux:8",
        "--build-arg","CONFIGURATION=fm-suite","-t","damsafe-dflowfm:local",str(source)],
        stdout=log,stderr=subprocess.STDOUT,check=False)
raise SystemExit(result.returncode)
