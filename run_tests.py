"""Direct programmatic test runner."""

import sys

import pytest

if __name__ == "__main__":
    print("Iniciando bateria de testes...")
    exit_code = pytest.main(["-v", "-s", "tests"])
    print(f"Testes finalizados com código: {exit_code}")
    sys.exit(exit_code)
