# 11B-X-1371

`x1371` is a local-first forensic and cryptanalytic toolkit for investigating the 11B-X-1371 puzzle from raw source artifacts. It is designed around **proof, provenance, and reproducibility** rather than community consensus or folklore.

## Evidence standard

A valid solve in this repository must be reproducible from primary source artifacts with a documented evidence chain. Public writeups may be collected as untrusted references, but they remain quarantined as `external_claim` material unless independently reproduced.

### Evidence hierarchy

1. **Primary evidence** — original artifacts, exact bytes, exact metadata, and directly reproducible derivatives.
2. **Derived evidence** — OCR, normalized text, frame extracts, archive expansion, enhancement outputs.
3. **Heuristic leads** — anomaly flags, branch scores, encoding guesses, pattern detections.
4. **External claims** — community solves, summaries, accepted narratives, public interpretations.

External claims are stored separately, labeled as unverified, and can only produce candidate hypotheses. Agreement with a claim is reported as **correlation**, never confirmation.

## Safety and forensic hygiene

- Originals are preserved and never overwritten.
- Derived outputs are isolated from primary evidence.
- External claims are quarantined under a separate evidence tier.
- Archive expansion sanitizes paths to prevent traversal.
- Unknown binaries are never executed.
- Optional external tools are detected and skipped gracefully when absent.

## Installation

```bash
python -m pip install -e .[dev]
```

Optional external tools supported when installed:

- `ffmpeg` / `ffprobe`
- `exiftool`
- `7z`
- `binwalk`
- `tesseract`
- `file`
- `strings`
- `ImageMagick`
- Pillow-backed image enhancement if Pillow is installed in the environment

The default workflows still run with only Python installed.

## Quick start

```bash
x1371 ingest samples/
x1371 metadata
x1371 expand
x1371 media-extract
x1371 enhance
x1371 ocr
x1371 text-scan
x1371 decode
x1371 correlate
x1371 determinism
x1371 report
```

Or run the full pipeline in one command:

```bash
x1371 run-all samples/ --claims untrusted-notes/
```

## CLI commands

- `ingest` — inventory inputs, hash them, preserve originals, and create manifests.
- `inventory` — show the current artifact store.
- `metadata` — extract built-in and optional external metadata.
- `expand` — safely enumerate and extract nested archives.
- `media-extract` — extract frames, audio, and timing metadata from videos when ffmpeg is available.
- `enhance` — create reversible or documented image enhancement variants.
- `ocr` — run OCR over image artifacts and enhanced variants.
- `text-scan` — inspect Unicode anomalies, invisible markers, scripts, motifs, and heuristics.
- `decode` — run registry-driven layered decoders and cryptanalytic helpers.
- `correlate` — compare artifacts, text overlap, lineage, and path clues.
- `determinism` — rerun selected stages and flag instability.
- `report` — emit JSON and Markdown reports.
- `run-all` — execute the entire case pipeline.
- `ingest-claims` — quarantine external claims.
- `compare-claims` — compare claims against independently derived branches.

Use `x1371 --help` or `x1371 <command> --help` for details.

## Output layout

By default all outputs are written under `.x1371/`:

```text
.x1371/
├── analysis/
├── evidence/
│   ├── primary/
│   ├── derived/
│   ├── heuristic/
│   └── external_claims/
├── logs/
├── manifests/
├── metadata/
└── reports/
```

This keeps raw inputs, derivatives, heuristics, and claims clearly separated.

## Provenance model

Every artifact record tracks at least:

- artifact id
- source path and logical path
- artifact class and type
- detected MIME/type
- size and hashes
- timestamps
- parent-child relationships
- derivation step and tool
- transform parameters
- reproducibility and determinism metadata
- suspicion tags
- evidence tier

## Determinism philosophy

Deterministic stages are favored during ranking. Heuristic stages are useful for discovery, but they are not treated as proof. Report output explicitly distinguishes reproducible findings from heuristic leads and unsupported branches.

## Decoder and heuristic architecture

The toolkit uses plugin-style registries for:

- metadata extractors
- enhancement passes
- OCR passes
- decoders and transforms
- heuristic analyzers
- report sections

This allows future analyzers and transforms to be added without redesigning the orchestration layer.

## Reporting

Reports are emitted as both JSON and Markdown and include:

- source inventory
- manifest summary
- metadata summary
- extraction and enhancement outputs
- Unicode anomaly findings
- decode trees
- heuristic leads
- cross-artifact correlations
- determinism checks
- unresolved residue
- external-claim comparison in a non-evidentiary section
- proof-status labels: `proven`, `strongly_supported`, `tentative`, `unsupported`, `rejected`

## Configuration

A documented example is available at `config/example.toml`. Configuration supports package defaults, TOML overrides, and CLI overrides for workspace location.

## Developer workflow

```bash
make install
make lint
make test
make help
```

The codebase uses Python type hints, pytest, and ruff. Tests focus on manifesting, provenance, evidence-tier separation, Unicode analysis, decoder traversal, heuristics, claims isolation, ranking, correlations, and CLI smoke coverage.

## Forensic workflow guidance

1. Ingest only primary artifacts first.
2. Keep claims out of the evidence path until you explicitly quarantine them.
3. Treat every transformation as provisional until it is reproducibly tied back to the original bytes.
4. Prefer branches that minimize unexplained residue and remain stable across reruns.
5. Never upgrade a public interpretation into evidence without independent reproduction.
