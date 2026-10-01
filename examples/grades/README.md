# Photo-specific example LUTs

Four CUBE33 assets reproduce the final global mappings in the showcase. They are
original AI-assisted recipes under root MIT, not trained models or general-purpose
photographer presets. `recipes.json` stores hashes, lightness knots, chroma/tint
parameters and selected strengths. Each was evaluated on its particular source.

For a compatible encoded sRGB image, pass the CUBE path as `strategy.lut` to
`apply_color_grade`, after assessing suitability. Strength is already baked into
these files; do not apply it a second time. Full-resolution source photos are
private and not included. See `docs/showcase.md` for the intent and limitations.

`python scripts/bake_example_luts.py` rebuilds the same numeric mappings into
`assets/luts/derived/showcase-rebuilt/` without reading any photograph. Headers
can differ; table equivalence is checked by the asset tests. Regeneration uses
the pinned OpenCV/NumPy environment. Other dependency versions may change
rounding; redistributed originals remain protected from regeneration.
