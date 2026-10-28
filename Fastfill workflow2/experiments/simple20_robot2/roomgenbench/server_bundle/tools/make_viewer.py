"""Wrap an assembled room GLB into a single HTML file with a three.js viewer (open it in any browser)."""
import base64, sys
from pathlib import Path
glb, html = Path(sys.argv[1]), Path(sys.argv[2])
template = (Path(__file__).parent / "viewer_template.html").read_text()
html.write_text(template.format(title=f"{glb.stem} · {sys.argv[3] if len(sys.argv) > 3 else 'trellis_text'}",
                                glb=base64.b64encode(glb.read_bytes()).decode()))
print(html)
