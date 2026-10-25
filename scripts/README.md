# scripts

Generates the two profile panels in `../assets/`:
`profile-signal.svg` (dark theme) and `profile-print.svg` (light theme).

```
pip install fonttools brotli numpy pillow
python scripts/build.py
```

- `config.json`: all the text (name, role, notes, ring label) and `spin_ms` (one turn of the object, default 14000).
- `tokens.json`: Cyber Nihilism design tokens (colours, spacing, tempos). Nothing is hard-coded.
- `poster.py`: the panel: layout, gaussian point cloud, ASCII ring, terminal, fluid motion.
- `sheet.py`: shared drawing helpers (lattice, wipes, glyphs) and the previous V1 sheet.
- `panel.py`: icosahedron helpers used by the previous versions.
- `build.py`: shared helpers (tokens, fonts, text to outlines) and the entry point.
- `fonts/`: Rajdhani and JetBrains Mono, both SIL Open Font License (see the OFL files).

Text is converted to vector outlines by default, so the SVGs need no web fonts.
`python scripts/build.py --embed-fonts` keeps live text with embedded WOFF2 subsets instead.
