# Four individually graded photographs

Approved on 2026-10-02 after visual comparison. Left original, right graded.
Each was executed through MCP `apply_color_grade` with a photo-specific CUBE.
Originals were unchanged.

| Example | Visual decision | Original-size output |
| --- | --- | --- |
| clouds | Orange/blue separation and cloud density; keep silhouettes | 5568 × 3712 |
| architecture | Brighter midtones and pink clouds; retain building separation | 5568 × 3712 |
| traffic | Warm sky / cool mountain-road palette; limit pale-sky tint | 3712 × 5568 |
| night | Blue atmosphere, warm buildings and readable white/red trails | 5568 × 3712 |

The model authored and revised these recipes after viewing input and actual
output. These are not the ten default looks, neural model outputs or trained
photographer presets. They contain no dehazing or spatial masking. Ordinary
strategy controls stayed neutral because each CUBE already contains the chosen
lightness/color changes; a non-identity LUT therefore gives non-neutral output.

The final example CUBEs and numeric recipes are in `examples/grades/`, under MIT.
Photos have separate copyright. They assume encoded sRGB, retain black/white
endpoints and passed a 256-level neutral-ramp monotonicity check. This is technical
evidence, not universal visual quality or highlight recovery. Full originals are
not included; another photo needs its own visual judgment and possibly a revised
recipe. The initial cloud version's darkening and the traffic version's pale-sky
cool tint were reduced before approval.

![Clouds](images/showcase-clouds.jpg)
![Architecture](images/showcase-architecture.jpg)
![Traffic](images/showcase-traffic.jpg)
![Night](images/showcase-night.jpg)
