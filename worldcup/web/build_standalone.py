"""Bundle the tool into one self-contained, double-clickable HTML file.

Inlines styles.css, app.js and rankings.json into worldcup/standalone.html so it
runs from the local filesystem with no web server (browsers block fetch() over
file://, so the data is embedded instead of fetched). Re-run after changing the
page or regenerating rankings.json:

    python build_standalone.py
"""
import base64
import os

HERE = os.path.dirname(__file__)


def _embed_images(html):
    """Replace local <img src="img/..."> with base64 data URIs, when present."""
    img_dir = os.path.join(HERE, "img")
    for fname in os.listdir(img_dir) if os.path.isdir(img_dir) else []:
        if not fname.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            continue
        ref = f'src="img/{fname}"'
        if ref not in html:
            continue
        ext = "jpeg" if fname.lower().endswith((".jpg", ".jpeg")) else fname.rsplit(".", 1)[1]
        with open(os.path.join(img_dir, fname), "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
        html = html.replace(ref, f'src="data:image/{ext};base64,{data}"')
    return html


def read(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return fh.read()


def main():
    html = read("index.html")
    css = read("styles.css")
    app = read("app.js")
    data = read("rankings.json")

    html = html.replace(
        '<link rel="stylesheet" href="styles.css" />',
        f"<style>\n{css}\n</style>")

    # Use the embedded data instead of fetching rankings.json.
    app = app.replace(
        '  const res = await fetch("rankings.json");\n  DATA = await res.json();',
        "  DATA = window.__RANKINGS__;")

    html = html.replace(
        '<script src="app.js"></script>',
        f"<script>window.__RANKINGS__ = {data};</script>\n  <script>\n{app}\n</script>")

    html = _embed_images(html)

    out = os.path.join(HERE, "..", "standalone.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"Wrote {os.path.abspath(out)} ({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
