FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends build-essential ca-certificates && rm -rf /var/lib/apt/lists/*
COPY src /opt/dualsphysics/src
COPY bin/linux /opt/dualsphysics/bin/linux
WORKDIR /opt/dualsphysics/src/source
# Official CPU makefile; optional unrelated coupling libraries disabled explicitly.
# Fast-math disabled so IEEE nonfinite checks retain their meaning.
RUN make -f Makefile_cpu -j4 COMPILE_CHRONO=NO COMPILE_WAVEGEN=NO COMPILE_MOORDYNPLUS=NO USE_FAST_MATH=NO ../../bin/linux/DualSPHysics5.4CPU_linux64
RUN chmod +x /opt/dualsphysics/bin/linux/*
ENV PATH="/opt/dualsphysics/bin/linux:$PATH"
ENV LD_LIBRARY_PATH="/opt/dualsphysics/bin/linux"
ENV OMP_NUM_THREADS=2
WORKDIR /work
