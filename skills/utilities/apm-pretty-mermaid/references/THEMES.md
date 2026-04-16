# Themes (SVG only)

15 themes from `beautiful-mermaid`. List via `node scripts/themes.mjs`. ASCII output ignores theme.

## Recommended (APM Confluence)

| Theme | Bg | Fg | Accent | Use |
| --- | --- | --- | --- | --- |
| `tokyo-night` ⭐ | `#1a1b26` | `#a9b1d6` | `#7aa2f7` | Default dark — dev docs, architecture pages |
| `github-dark` | `#0d1117` | `#4493f8` | — | GitHub-familiar dark |
| `dracula` | `#282a36` | `#f8f8f2` | — | Vibrant high-contrast |
| `github-light` | `#ffffff` | `#0969da` | — | Default light — clean, professional |
| `zinc-light` | `#ffffff` | `#27272a` | — | Print / projector / high-contrast |
| `catppuccin-latte` | `#eff1f5` | `#8839ef` | — | Warm light |

## All 15 themes

**Light:** `zinc-light`, `tokyo-night-light`, `catppuccin-latte`, `nord-light`, `github-light`, `solarized-light`

**Dark:** `zinc-dark`, `tokyo-night`, `tokyo-night-storm`, `catppuccin-mocha`, `nord`, `dracula`, `github-dark`, `solarized-dark`, `one-dark`

## Selection by Context

| Context | Pick |
| --- | --- |
| Confluence dark-mode reader | `tokyo-night` |
| Confluence light-mode reader (majority) | `github-light` |
| Printed release doc | `zinc-light` |
| Slide deck projector | `zinc-light` or `github-light` |
| Marketing / vibrant | `dracula` |

## Apply

```bash
node scripts/render.mjs --input x.mmd --output x.svg --theme tokyo-night
```

## Override colors (bypass theme)

```bash
node scripts/render.mjs --input x.mmd \
  --bg "#1a1b26" --fg "#a9b1d6" --accent "#7aa2f7" \
  --output x.svg
```

## Transparent (for dark/light mode Confluence)

```bash
node scripts/render.mjs --input x.mmd --theme tokyo-night --transparent --output x.svg
```
