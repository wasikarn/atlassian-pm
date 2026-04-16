# ASCII Box-Drawing Characters — Palette + Examples

Reference palette for hand-drawing ASCII diagrams in Jira code blocks. Sourced from [dsample's gist](https://gist.github.com/dsample/79a97f38bf956f37a0f99ace9df367b9) + gist comment contributions + Wikipedia Unicode box-drawing spec.

**Rendering rule:** use **Unicode code points** (U+250x / U+255x / U+258x), NOT legacy Extended ASCII codes. Modern terminals, editors, Jira, Confluence, GitHub, and Slack all render Unicode box chars correctly; Extended ASCII is unreliable across SSH / locale boundaries.

## Single line (U+2500–U+253C)

| Char | U+ | Name |
| --- | --- | --- |
| `─` | 2500 | light horizontal |
| `│` | 2502 | light vertical |
| `┌` | 250C | light down + right (upper-left corner) |
| `┐` | 2510 | light down + left (upper-right corner) |
| `└` | 2514 | light up + right (lower-left corner) |
| `┘` | 2518 | light up + left (lower-right corner) |
| `├` | 251C | light vertical + right (T-left) |
| `┤` | 2524 | light vertical + left (T-right) |
| `┬` | 252C | light horizontal + down (T-down) |
| `┴` | 2534 | light horizontal + up (T-up) |
| `┼` | 253C | light horizontal + vertical (cross) |

## Heavy line (U+2501–U+254B)

Use for emphasis, architectural boundaries, or to contrast against light detail lines.

| Char | U+ | Name |
| --- | --- | --- |
| `━` | 2501 | heavy horizontal |
| `┃` | 2503 | heavy vertical |
| `┏` | 250F | heavy down + right (upper-left corner) |
| `┓` | 2513 | heavy down + left (upper-right corner) |
| `┗` | 2517 | heavy up + right (lower-left corner) |
| `┛` | 251B | heavy up + left (lower-right corner) |
| `┣` | 2523 | heavy vertical + right |
| `┫` | 252B | heavy vertical + left |
| `┳` | 2533 | heavy horizontal + down |
| `┻` | 253B | heavy horizontal + up |
| `╋` | 254B | heavy cross |

## Arc corners (U+256D–U+2570)

Rounded alternatives to sharp 90° corners — softer look for UI-style diagrams.

| Char | U+ | Name |
| --- | --- | --- |
| `╭` | 256D | light arc down + right (rounded upper-left) |
| `╮` | 256E | light arc down + left (rounded upper-right) |
| `╯` | 256F | light arc up + left (rounded lower-right) |
| `╰` | 2570 | light arc up + right (rounded lower-left) |

Example (rounded box):

```
╭───╮
│   │
╰───╯
```

## Dashed / dotted (U+2504–U+250B, U+254C–U+254F)

Use for optional paths, feature-flag edges, pending integrations, or "soft" connections.

| Char | U+ | Name |
| --- | --- | --- |
| `┄` | 2504 | light triple-dash horizontal |
| `┅` | 2505 | heavy triple-dash horizontal |
| `┆` | 2506 | light triple-dash vertical |
| `┇` | 2507 | heavy triple-dash vertical |
| `┈` | 2508 | light quadruple-dash horizontal |
| `┉` | 2509 | heavy quadruple-dash horizontal |
| `┊` | 250A | light quadruple-dash vertical |
| `┋` | 250B | heavy quadruple-dash vertical |
| `╌` | 254C | light double-dash horizontal |
| `╍` | 254D | heavy double-dash horizontal |
| `╎` | 254E | light double-dash vertical |
| `╏` | 254F | heavy double-dash vertical |

## Double line (U+2550–U+256C)

| Char | U+ | Name |
| --- | --- | --- |
| `═` | 2550 | double horizontal |
| `║` | 2551 | double vertical |
| `╔` | 2554 | double down + right (upper-left) |
| `╗` | 2557 | double down + left (upper-right) |
| `╚` | 255A | double up + right (lower-left) |
| `╝` | 255D | double up + left (lower-right) |
| `╠` | 2560 | double vertical + right |
| `╣` | 2563 | double vertical + left |
| `╦` | 2566 | double horizontal + down |
| `╩` | 2569 | double horizontal + up |
| `╬` | 256C | double horizontal + vertical (cross) |

## Mixed single + double junctions (U+255E–U+256B)

Combine single-line detail with double-line architectural boundary in the same diagram — the junction char picks which side is heavy.

| Char | U+ | Name |
| --- | --- | --- |
| `╞` | 255E | single vertical + double right |
| `╟` | 255F | double vertical + single right |
| `╡` | 2561 | single vertical + double left |
| `╢` | 2562 | double vertical + single left |
| `╤` | 2564 | single down + double horizontal |
| `╥` | 2565 | double down + single horizontal |
| `╧` | 2567 | single up + double horizontal |
| `╨` | 2568 | double up + single horizontal |
| `╪` | 256A | double horizontal + single vertical (cross) |
| `╫` | 256B | single horizontal + double vertical (cross) |

## Shading / blocks (U+2580–U+25A0 subset)

| Char | U+ | Name |
| --- | --- | --- |
| `░` | 2591 | light shade (low density) |
| `▒` | 2592 | medium shade |
| `▓` | 2593 | dark shade |
| `█` | 2588 | full block |
| `▄` | 2584 | lower half block |
| `▀` | 2580 | upper half block |
| `▌` | 258C | left half block |
| `■` | 25A0 | black square |

## Arrows (useful for flow diagrams)

| Char | U+ | Name |
| --- | --- | --- |
| `▶` | 25B6 | right triangle (flow arrow right) |
| `◀` | 25C0 | left triangle |
| `▲` | 25B2 | up triangle |
| `▼` | 25BC | down triangle |
| `→` | 2192 | rightwards arrow |
| `←` | 2190 | leftwards arrow |
| `↑` | 2191 | upwards arrow |
| `↓` | 2193 | downwards arrow |
| `⇒` | 21D2 | rightwards double arrow |

## Stroke-weight rule

`─` (light) and `═` (double) are **wider** than `━` (heavy) in most monospace fonts. Use weight deliberately:

- **Light** (`─ │`) — routine edges, most common.
- **Heavy** (`━ ┃`) — emphasis, critical path.
- **Double** (`═ ║`) — architectural boundaries, module/service separation.

## Example patterns

Simple box:

```
┌───┐
│   │
└───┘
```

Horizontal connection:

```
┌───┐  ┌───┐
│   ├──┤   │
└───┘  └───┘
```

Vertical hierarchy (tree):

```
┌───┐
│   │
└─┬─┘
  │
┌─┴─┐
│   │
└───┘
```

## Drawing tools (free first)

- **MonoSketch** — <https://github.com/tuanchauict/MonoSketch> · free, OSS, cross-platform GUI
- **asciiflow.com** — web-based, no install, drag-drop
- **monodraw** — Mac-only, paid

## See also

- `references/mermaid-guide.md` — Jira ASCII convention, width rules, multi-branch flowchart bug (mermaid-ascii#56)
- `skills/utilities/apm-pretty-mermaid/SKILL.md` — ASCII rendering skill for Jira
- `.claude/rules/mermaid.md` — auto-loaded rule, target matrix
