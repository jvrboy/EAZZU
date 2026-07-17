# EAZZU on iSH (iOS)

[**iSH**](https://ish.app) runs an Alpine Linux userland on your iPhone/iPad
by emulating x86 in userspace. EAZZU is built with iSH as a first-class
target — the base install has zero native/compiled dependencies beyond
`cryptography`, which Alpine ships as a prebuilt package (`py3-cryptography`).

## One-liner install

```sh
apk add git && git clone https://github.com/EAZZU/EAZZU.git && \
  cd EAZZU && sh ish/bootstrap.sh
```

`bootstrap.sh` installs Python + system-provided crypto, then does
`pip install -e .` with `PIP_PREFER_BINARY=1` so pip never tries to compile
from source (which is painfully slow under iSH's x86 emulation on ARM iOS).

## What works on iSH

| Feature                             | Status                                        |
| ----------------------------------- | --------------------------------------------- |
| `eazzu chat` / `eazzu ask`          | ✅ full support                                |
| `eazzu keys` (encrypted store)      | ✅ (uses system `cryptography`)                |
| `eazzu providers`                   | ✅                                             |
| `eazzu net ip/dns/http`             | ✅                                             |
| `eazzu dev analyze/run`             | ✅                                             |
| `eazzu research`                    | ✅ (needs network)                             |
| `eazzu web` (bundled chat UI)       | ✅ (open `http://localhost:8787` in Safari)    |
| `eazzu trade backtest`              | ⚠️ requires `pip install eazzu[trading]` (needs pandas/numpy wheels — heavier on iSH) |
| `eazzu trade live`                  | ⚠️ needs your Deriv token + `--i-understand-risk` |

## Pinning a provider

```sh
echo 'export EAZZU_PROVIDER=openai' >> ~/.profile
echo 'export EAZZU_MODEL=gpt-4o-mini' >> ~/.profile
```

## Troubleshooting

* **`cryptography` fails to import** — reinstall with `apk add py3-cryptography`
  and re-run `pip install -e .`.
* **Slow first launch** — normal under x86 emulation; subsequent launches use
  cached `.pyc` files and are much faster.
* **Missing wheels for pandas/numpy** — stick to the base install (no
  `[trading]` extra). All chat/dev/net/research features still work.
