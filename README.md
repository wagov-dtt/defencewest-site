# WA Defence Industry Directory

[![CI](https://github.com/wagov-dtt/defencewest-site/actions/workflows/ci.yml/badge.svg)](https://github.com/wagov-dtt/defencewest-site/actions/workflows/ci.yml)

Western Australia's Defence Industry and Science Capability Directory - a static site built with Hugo.

## Quick Links

- **Submit a company** -> [submission form](https://wagov-dtt.github.io/defencewest-site/submit/) (for external companies)
- **Contribute code** -> [CONTRIBUTING.md](CONTRIBUTING.md) (for developers and admins)
- **AI agent guide** -> [AGENTS.md](AGENTS.md) (for AI assistants)

## Tech Stack

- [Hugo](https://gohugo.io) - Static site generator
- [PicoCSS](https://picocss.com) - CSS framework
- [MapLibre GL JS](https://maplibre.org) - Interactive maps
- Tools: [mise](https://mise.jdx.dev), [uv](https://docs.astral.sh/uv/)

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contributing guide, development setup, admin tasks
- [AGENTS.md](AGENTS.md) - AI agent development guide
- [ACCESSIBILITY.md](ACCESSIBILITY.md) - Accessibility statement and testing approach
- [docs/decisions/](docs/decisions/) - Architecture Decision Records

## Maps

The map implementation uses:

- **[OpenFreeMap Liberty](https://openfreemap.org/)** - free, open-source map tiles
- **[MapLibre GL JS](https://maplibre.org)** - vector map rendering with globe projection
- **Static minimaps** - pre-rendered PNG images for company cards (generated via [`mlnative`](https://pypi.org/project/mlnative/))

All map configuration (style URL, tile URL) is in `hugo.toml` under `[params]`.

## License

This project is released under the MIT License.

## AI-Assisted Development

This website was developed with assistance from [OpenCode](https://github.com/anomalyco/opencode), in accordance with [ADR 011: AI Tool Governance](https://adr.dtt.digital.wa.gov.au/security/011-ai-governance.html).
