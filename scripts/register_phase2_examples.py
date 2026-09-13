"""Register checksum-pinned retained Phase 2 benchmark output in a synthetic project."""

from damsafe.db import engine_for
from damsafe.numerics.archive import register

if __name__ == "__main__":
    print(register(engine_for()))
