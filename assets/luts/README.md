# Small licensed LUT candidate library

Eighteen creative candidates are bundled: ten original analytic looks in
`creative-v1/` (MIT), six Pat David Hald film-emulation
approximations converted to CUBE33 under CC-BY-SA-4.0, and two unchanged original
CUBE33 looks from Zhengxiao Wu under MIT. Their provenance, hashes, color-space
assumptions, measured neutral ramps, RGB probes, and scene hypotheses are in
`catalog.json`. Original Hald PNGs and source notices remain alongside them.

No candidate is selected automatically. Start from the unmodified/no-LUT result,
inspect a preview, and judge highlight separation, black anchoring, subject
color, and atmosphere. Lower global contrast and raised blacks are not universal
film qualities. Each LUT can already contain a tone curve; avoid blindly adding
another strong curve before it. These tables cannot reconstruct clipped JPEG
data or encode grain, sharpening, denoising, spatial masks, or halation.

Use `download_sources.py` only to reproduce the pinned public-source downloads.
Use `prepare_library.py` offline to regenerate the six converted CUBEs and
measured catalog. These scripts process LUT assets, not photographs, and never
execute downloaded code. Regeneration requires the project's existing NumPy and
OpenCV environment. Source checksums in the catalog verify individual LUTs; the
original MIT CUBE files remain unchanged.

After `prepare_library.py`, run `scripts/build_creative_looks.py` from the project
root to restore the ten original looks and complete 18-entry catalog.
The original looks are fixed formulas, not neural weights or learned photographer
presets. They require no training. See the scene guide in
`skills/color-strategy/references/ready-looks.md` before selecting one.

The Pat David family assumes encoded sRGB input and output; the exact 16-bit
Natron assets have no ICC/gamma tags, so the assumption is explicit. The MIT
looks declare a profile-specific LUMIX Standard/sRGB design input. Neither group
is a camera Log conversion. Do not use them to transform Log/HDR/P3/AdobeRGB or
linear image values without a verified prior color-space conversion.

Pat David source and license: <https://github.com/NatronGitHub/clut>.
Original creator's explanation: <https://patdavid.net/2013/08/film-emulation-presets-in-gmic-gimp/>.
Related collection color-space documentation: <https://rawpedia.rawtherapee.com/Film_Emulation>.
MIT source and explicit CUBE license: <https://github.com/t0saki/lumix-original-looks>.

`UPSTREAM_README.md` files are retained verbatim as provenance. Their relative
links refer to files in the original upstream repository, not this checkout;
use the linked source repository to follow those references.

Other collections were excluded when their repository license did not clearly
cover the LUT assets, or when they were camera Log transforms unsuitable for
these already-rendered JPEGs. "Free download" alone was not treated as a license.
