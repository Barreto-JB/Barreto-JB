"""Build responsive SVG logo grids from the checked-in Devicon assets."""
import copy
import html
import pathlib
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
ET.register_namespace("", "http://www.w3.org/2000/svg")
GROUPS = {
    "languages": [("javascript", "JavaScript"), ("typescript", "TypeScript"), ("python", "Python"),
                  ("html5", "HTML5"), ("css3", "CSS3"), ("postgresql", "SQL")],
    "databases": [("supabase", "Supabase"), ("postgresql", "PostgreSQL"), ("github", "GitHub Pages")],
    "tools": [("react", "React"), ("nodejs", "Node.js"), ("electron", "Electron"),
              ("vitejs", "Vite"), ("git", "Git"), ("github", "GitHub")],
}


def build(name, items, theme, mobile):
    width = 300 if mobile else 900
    row_height = 89 if mobile else 104
    icon_size = 40 if mobile else 52
    label_size = 12 if mobile else 15
    cell_width = width / 3
    rows = (len(items) + 2) // 3
    height = rows * row_height
    dark = theme == "dark"
    background = "#0D1117" if dark else "#FFFFFF"
    alternate = "#161B22" if dark else "#F6F8FA"
    border = "#30363D" if dark else "#D0D7DE"
    text = "#F0F6FC" if dark else "#1F2328"
    labels = ", ".join(label for _, label in items)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">',
        f'<title id="title">{html.escape(labels)}</title>',
        f'<rect width="{width}" height="{height}" fill="{background}"/>',
    ]
    for index, (icon, label) in enumerate(items):
        col, row = index % 3, index // 3
        x, y = col * cell_width, row * row_height
        fill = alternate if row % 2 else background
        parts.append(f'<rect x="{x}" y="{y}" width="{cell_width}" height="{row_height}" fill="{fill}"/>')
        svg = copy.deepcopy(ET.parse(ROOT / "assets" / "icons" / f"{icon}.svg").getroot())
        identifiers = {element.attrib["id"]: f"{name}-{index}-{element.attrib['id']}"
                       for element in svg.iter() if "id" in element.attrib}
        for element in svg.iter():
            for attribute, value in list(element.attrib.items()):
                if attribute == "id":
                    element.set(attribute, identifiers[value])
                else:
                    for original, unique in identifiers.items():
                        value = value.replace(f"url(#{original})", f"url(#{unique})")
                        if value == f"#{original}":
                            value = f"#{unique}"
                    element.set(attribute, value)
        svg.set("x", str(x + (cell_width - icon_size) / 2))
        svg.set("y", str(y + 13))
        svg.set("width", str(icon_size))
        svg.set("height", str(icon_size))
        parts.append(ET.tostring(svg, encoding="unicode"))
        label_y = y + (74 if mobile else 88)
        parts.append(f'<text x="{x + cell_width / 2}" y="{label_y}" text-anchor="middle" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" font-size="{label_size}" fill="{text}">{html.escape(label)}</text>')

    for col in (1, 2):
        parts.append(f'<path d="M{col * cell_width} 0V{height}" stroke="{border}"/>')
    for row in range(1, rows):
        parts.append(f'<path d="M0 {row * row_height}H{width}" stroke="{border}"/>')
    parts.append(f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" fill="none" stroke="{border}"/>')
    parts.append("</svg>")
    suffix = "-mobile" if mobile else ""
    target = ROOT / "assets" / f"technology-{name}-{theme}{suffix}.svg"
    target.write_text("\n".join(parts) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for name, items in GROUPS.items():
        for theme in ("dark", "light"):
            for mobile in (False, True):
                build(name, items, theme, mobile)
