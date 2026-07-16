# Security policy

ZaeREo has no supported binary release yet. Security fixes are nevertheless
accepted on the main development branch, especially for content parsing,
installation, save handling, networking, and packaging.

| Version | Supported |
| --- | --- |
| Published stable release | None exists |
| main / pre-release development | Best effort |
| Legacy Zaero binaries | Not supported by this project |

## Report a vulnerability privately

Do not open a public issue containing exploit details, malicious files,
credentials, or private paths.

Use GitHub's private vulnerability-reporting form for this repository:
[open a private security advisory](https://github.com/themuffinator/ZaeREo/security/advisories/new).
If GitHub says private reporting is unavailable, contact the repository owner
privately through the account linked from the repository and ask for a secure
channel before sending details.

Include the affected commit/version, platform, impact, minimal reproduction, and
whether the report involves a PAK, BSP, save, archive, importer source, server,
or release artifact. Use a harmless synthetic fixture where possible.

We will acknowledge receipt when a maintainer sees the report, assess scope, and
coordinate disclosure after a fix and supported update path exist. No response
time or bounty is promised at this pre-release stage.

## Security boundaries

Treat all imported and downloaded content as untrusted. Parsers, importers,
installers, and release tooling must reject:

- path traversal, absolute paths, drive/UNC escapes, and symlink/reparse escapes;
- malformed, negative, overlapping, or out-of-range PAK/BSP offsets and sizes;
- unsafe visible PAK member names even when a known legacy archive has ignored
  non-zero bytes after the first NUL in its fixed-width name field;
- decompression/archive bombs and unreasonable counts or allocations;
- duplicate normalized paths and case-only collisions;
- writes outside an explicitly verified stage or game-mod directory;
- unsafe target deletion or cleanup not backed by an owned manifest; and
- command injection through filenames, paths, metadata, tags, or release text.

Never put tokens in .zaereo.local.json or logs. GitHub publication uses the
GitHub CLI credential store or a least-privilege Actions token. Developer
installation must never overwrite baseq2 or remove files it did not stage.
