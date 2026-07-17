#!/bin/sh
# ------------------------------------------------------------------
# EAZZU · iSH (Alpine on iOS) bootstrapper
# ------------------------------------------------------------------
# Usage (inside iSH):
#     apk add git
#     git clone https://github.com/EAZZU/EAZZU.git && cd EAZZU
#     sh ish/bootstrap.sh
# ------------------------------------------------------------------
set -eu

echo "==> EAZZU · iSH bootstrap"

# 1) Base packages available on Alpine/musl x86 (which is what iSH emulates)
apk update
apk add --no-cache python3 py3-pip py3-cryptography py3-requests \
                   ca-certificates openssl git curl

# 2) Prefer wheels — building from source is painfully slow under iSH's
#    x86 emulation on ARM iOS, so we ask pip to reach for prebuilt wheels.
export PIP_PREFER_BINARY=1
export PIP_DISABLE_PIP_VERSION_CHECK=1

# 3) Install EAZZU in editable base mode (no heavy scientific extras)
python3 -m pip install --upgrade pip
python3 -m pip install -e .

# 4) Config dir
mkdir -p "$HOME/.eazzu"
chmod 700 "$HOME/.eazzu"

# 5) Smoke test
echo "==> Smoke test"
python3 -c "import eazzu, sys; print('eazzu', eazzu.__version__, 'ok')"
eazzu --version
eazzu providers --category llm | head -20 || true

cat <<'BANNER'

  ✓ EAZZU is installed inside iSH.

  Next steps
  ----------
    eazzu keys set openai sk-...
    eazzu chat

  Tip: put `export EAZZU_PROVIDER=openai` in ~/.profile so every iSH
  session starts wired to your preferred provider.

BANNER
