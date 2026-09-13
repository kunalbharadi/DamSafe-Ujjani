# Native engine feasibility audit — phase 1 baseline, 2026-09-12

This records the initial host prerequisite audit and is retained for traceability. Docker Desktop later became available. Genuine DualSPHysics CPU and D-Flow FM images were built; both executed official examples and a shared synthetic benchmark. Current statuses, exact image/input hashes and run logs are in [PHASE2_EVIDENCE.md](PHASE2_EVIDENCE.md). The "not found" and "not run" statements below describe the earlier phase 1 checkpoint, not the current workspace.

## Host evidence

Windows, CPython 3.12.10 via the Python launcher; MSYS Python is first on PATH and was not used. Node 24.19.0, npm 11.17.0. Intel Core i5-14450HX, 10 physical cores / 16 logical processors. Reported RAM: 25,383,882,752 bytes (~23.64 GiB). `nvidia-smi` reports RTX 3050 Laptop GPU, 6,144 MiB, driver 591.91. A GPU driver does not establish CUDA development toolkit or solver compatibility.

`dflowfm`, `DualSPHysics`, `psql`, `cmake`, `cl`, `ifx` and `nvcc` were not found on PATH. Checked conventional Visual Studio, Intel oneAPI and CUDA installation directories were absent. No native solver was found or started. Docker CLI exists but `docker version` could not connect to the Docker Desktop Linux engine named pipe. An automatic approval rejection blocked a combined setup command that included starting Docker Desktop; the fallback is explicitly labelled SQLite preview. No service availability is claimed from Compose configuration.

## D-Flow FM

Official repository: https://github.com/Deltares/Delft3D

Audited tree commit: `18f8ebb239e5a746a2ac1a7c85631b539fb15e51`. This pins the inspected source, **not an installed executable**. Evidence: `source-audit.json`.

[Official Windows build instructions](https://github.com/Deltares/Delft3D/blob/18f8ebb239e5a746a2ac1a7c85631b539fb15e51/doc/compiling_Windows.md) describe Visual Studio C++ support, Intel oneAPI Fortran/MPI/MKL, CMake, Conan 2 and external dependency compilation (including Cygwin/PETSc requirements). The local prerequisites were not found. No speculative engine CLI or invented Python solver API was added. An appropriate complete runtime distribution or substantial toolchain installation is needed for phase 2.

The repository provides `examples/` and manuals linked from its README. D-Flow FM/other kernels have component-specific AGPL/GPL/LGPL or third-party licences; preserve selected-component licence provenance. The source repository is not itself a validated run or a complete installed GUI.

## DualSPHysics

Official repository: https://github.com/DualSPHysics/DualSPHysics

Audited tree commit: `ef3721a861fda961f0e2f9ec4cd317b19de99086`. The source licence is LGPL-2.1; additional bundled tool terms still need review. `bin/windows/` contains GenCase and postprocessors but no main DualSPHysics solver executable in the inspected listing. Its README explicitly points to the [complete package](https://dual.sphysics.org/downloads/). GitHub's latest-release endpoint returned 404. Although the web fetcher initially failed, a direct Python GET returned HTTP 200 for the package page. The page presents a registration/download form and CAPTCHA; no registration, personal details or CAPTCHA response was submitted. The complete package was not retrieved. No helper binary was misreported as a solver.

The official README describes Visual Studio 2022 and CUDA 12.3 for GPU source builds. Those build prerequisites were absent locally. CPU operation is a possible phase-2 route once a complete compatible package is available; no performance or availability claim is made yet.

Relevant official example: `examples/main/01_DamBreak/CaseDambreakVal2D_Def.xml`, CPU/GPU batch scripts, and attributed `EXP_X-DamTipPosition_Koshizula&Oka1996.txt`. Inspect those exact scripts to obtain supported GenCase/solver arguments. GenCase preparation is required before the solver. The case has not run locally.

## Completion evidence

| Evidence | D-Flow FM | DualSPHysics |
| --- | --- | --- |
| Official source/build/package locations checked | Yes | Yes |
| Native executable present / startup verified | No | No |
| Official example run | No | No |
| Shared benchmark | No | No |
| Ujjani run | No | No |
| Compatible Ujjani comparison | No | No |

Phase 2 must retain executable identity/hash, actual supported invocation, inputs, logs, outputs, runtime and resource limits. Do not count source inspection, adapters, GenCase, or skipped integration tests as successful hydraulic execution.
