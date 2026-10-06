"""Fold sibling Borozdov themes into this one as Style Settings variants.

Each variant is another theme of the collection, read from ../<slug>/theme.css.
Its palette, its mapping onto Obsidian's variables and its type are resolved to
plain values, then translated into this theme's own vocabulary: a variant sets
this theme's palette names (--canvas, --ink…) to the colours that play the same
role in the sibling, plus the Obsidian variables that still come out different.
Only what differs is written, so a variant costs about three kilobytes.

The result goes between the VARIANTS:GENERATED markers at the end of section 1,
together with the @settings block Style Settings reads. Don't edit it by hand:
change the sibling theme or scripts/variants_config.py (the member list and
aliases for palette names with no Obsidian role) and run `npm run variants`.

Usage: npm run variants   (needs the sibling repositories and Obsidian installed)
"""
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
COLLECTION = pathlib.Path(os.environ.get("COLLECTION", ROOT.parent))
sys.path.insert(0, str(ROOT / "scripts"))
import screenshots  # noqa: E402  (finds Obsidian's app.css)

from variants_config import ID, NAME, DEFAULT_LABEL, MEMBERS, ALIASES  # noqa: E402
import variants_config  # noqa: E402

MARK_TEXT = getattr(variants_config, "MARK_TEXT", None)

START = "/* VARIANTS:GENERATED:START */"
END = "/* VARIANTS:GENERATED:END */"
FACES = ("light", "dark")
LEFT = {}  # palette names a variant had nothing for, reported at the end
SKIP = re.compile(r"--(code-.*|.*-rgb|(h[1-6]|inline-title)-(size|line-height)|font-monospace-theme|callout-quote)$")


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def section(css, n):
    m = re.search(r"/\* ===== %d\..*?(?=/\* ===== %d\.|\Z)" % (n, n + 1), css, re.S)
    if not m:
        raise SystemExit(f"section {n} not found")
    return m.group(0)


def rules(css):
    """Top-level rules of a section as (selectors, [(name, value)])."""
    out = []
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", strip_comments(css)):
        decls = []
        for d in body.split(";"):
            if ":" in d and d.strip().startswith("--"):
                k, v = d.split(":", 1)
                decls.append((k.strip(), " ".join(v.split())))
        out.append(([s.strip() for s in sel.split(",")], decls))
    return out


# From the component sections (4-12) only the colours that carry a theme's
# look are worth their bytes: tags and the quote bar. Sections 1-3 come whole.
LATE = re.compile(r"--(tag-(background|color)(-hover)?|blockquote-border-color)$")


def env(css, face, sections=tuple(range(1, 13))):
    """Variables as Obsidian sees them on <body class="theme-<face>">.
    .theme-* (0,1,0) beats body (0,0,1) whatever the order, so two layers."""
    body, cls = {}, {}
    parts = [(n, section(css, n)) for n in sections] if sections else [(0, css)]
    for n, part in parts:
        for sels, all_decls in rules(part):
            decls = [d for d in all_decls if n <= 3 or LATE.match(d[0])]
            if f".theme-{face}" in sels:
                cls.update(decls)
            elif "body" in sels or ":root" in sels:
                body.update(decls)
    return {**body, **cls}


VAR = re.compile(r"var\(\s*(--[a-z0-9-]+)\s*(?:,\s*([^()]*(?:\([^()]*\)[^()]*)*))?\)")


def resolve(value, vars_, own, depth=0):
    """Substitute the theme's own variables; Obsidian's stay as var()."""
    if depth > 20:
        raise SystemExit(f"cycle while resolving {value}")

    def sub(m):
        name, fallback = m.group(1), m.group(2)
        if name in own and name in vars_:
            return resolve(vars_[name], vars_, own, depth + 1)
        if name in own and fallback is not None:
            return resolve(fallback, vars_, own, depth + 1)
        return m.group(0)
    prev = None
    while prev != value:
        prev, value = value, VAR.sub(sub, value)
    return value


def load(slug, app_vars, css=None):
    css = css if css is not None else (COLLECTION / slug / "theme.css").read_text()
    faces = {f: env(css, f) for f in FACES}
    names = set(faces["light"]) | set(faces["dark"])
    own = {n for n in names if n not in app_vars}
    resolved = {f: {k: resolve(v, faces[f], own) for k, v in faces[f].items()} for f in FACES}
    mapping = {}  # Obsidian variable -> the palette name it reads, from section 3
    for sels, decls in rules(section(css, 3)):
        for k, v in decls:
            m = re.fullmatch(r"var\((--[a-z0-9-]+)\)", v)
            if m and m.group(1) in own and k not in own:
                mapping.setdefault(k, m.group(1))
    return {"slug": slug, "css": css, "raw": faces, "own": own, "res": resolved, "map": mapping}


def variant_decls(host, member, face, app):
    host_raw = dict(host["raw"][face])
    # What the sibling leaves alone is Obsidian's default, and this theme may
    # have changed it (a sans for headings, say), so defaults count too.
    mres = {**app[face], **member["res"][face]}
    out = {}
    # 1. This theme's palette names take the sibling's colour for the same role.
    roles = {}
    for obs, name in host["map"].items():
        roles.setdefault(name, []).append(obs)
    for name in sorted(host["own"]):
        if name not in host["raw"][face]:
            continue
        value = None
        for obs in roles.get(name, []):
            if obs in mres:
                value = mres[obs]
                break
        if value is None and name in ALIASES:
            alias = ALIASES[name]
            value = mres.get(alias) if alias.startswith("--") else alias
        if value is None and name in member["own"] and name in mres:
            value = mres[name]
        if value is None:
            LEFT.setdefault(name, []).append(member["slug"])
            continue
        host_raw[name] = value
        out[name] = value
    # 2. Obsidian variables that still come out different from the sibling.
    host_now = {**app[face], **{k: resolve(v, host_raw, host["own"]) for k, v in host_raw.items()}}
    # Skipped on purpose, to stay under the directory's 100 KiB: the -rgb twins
    # (they only feed Obsidian's deprecated error/success variables) and code
    # colours (section 1 spells them as palette variables, so they follow) and
    # heading sizes (the layout is this theme's; faces and weights carry over),
    # the monospace stack and the quote callout's grey.
    for obs in sorted(k for k in mres if k not in member["own"] and not SKIP.match(k)):
        if host_now.get(obs) != mres[obs]:
            out[obs] = mres[obs]
    legible(host_raw, out, mres, app, host, face)
    return out


def rgb(value):
    """(r, g, b) of a plain colour value, or None for anything fancier."""
    v = value.strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})", v)
    if m:
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) <= 4 else h
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)\s*(?:[,/]\s*(1|1\.0|100%))?\s*\)", v)
    return tuple(int(m.group(i)) for i in (1, 2, 3)) if m else {"white": (255,) * 3, "black": (0,) * 3}.get(v)


def contrast(a, b):
    def lum(c):
        c = [x / 255 for x in c]
        c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def legible(host_raw, out, mres, app, host, face):
    """A sibling's text colours were picked for its own surfaces: Hive's dark
    inline title sits on a yellow banner this layout doesn't draw, Specimen's
    highlight is an inverted block. Check what actually lands on the canvas
    and in a highlight here, and fall back to the sibling's body text."""
    raw = {**app[face], **host_raw, **out}

    def value(name, depth=0):
        v = raw.get(name, "")
        while depth < 20 and (m := VAR.fullmatch(v.strip())):
            v, depth = raw.get(m.group(1), m.group(2) or ""), depth + 1
        return rgb(v)
    canvas, text = value("--background-primary"), rgb(mres.get("--text-normal", ""))
    if not canvas or not text:
        return
    for name in ["--inline-title-color"] + [f"--h{i}-color" for i in range(1, 7)]:
        c = value(name)
        if c and contrast(c, canvas) < 3:
            out[name] = mres["--text-normal"]
            raw[name] = out[name]
    mark = value("--text-highlight-bg")
    if MARK_TEXT and mark:
        pick = max(("--text-normal", "--background-primary"), key=lambda k: contrast(rgb(mres.get(k, "")) or mark, mark))
        out[MARK_TEXT] = mres[pick]


NAMED = {"white": "#fff", "black": "#000"}  # the lint rejects colour keywords


def css_block(sel, decls):
    decls = {k: re.sub(r"\b(white|black)\b", lambda m: NAMED[m.group(1)], v) for k, v in decls.items()}
    # Tight lines: the release keeps whitespace, and these are values, not
    # code anyone reads. The lint wants one declaration per line.
    return sel + " {\n" + "".join(f"{k}:{v};\n" for k, v in decls.items()) + "}\n"


def main():
    with tempfile.TemporaryDirectory() as t:
        screenshots.extract(screenshots.obsidian_asar(), {"app.css"}, pathlib.Path(t))
        app_css = (pathlib.Path(t) / "app.css").read_text()
    app_vars = set(re.findall(r"--[a-z0-9-]+", app_css))
    app = {f: env(app_css, f, sections=None) for f in FACES}
    source = (ROOT / "theme.css").read_text()
    if source.count(START) != 1 or source.count(END) != 1:
        raise SystemExit("VARIANTS markers missing or repeated in theme.css")
    bare = re.sub(re.escape(START) + ".*?" + re.escape(END), "", source, flags=re.S)
    host = load(ROOT.name, app_vars, bare)
    opts = [f"      - label: {DEFAULT_LABEL}\n        value: {ID}-default"]
    blocks = []
    for slug, label in MEMBERS:
        member = load(slug, app_vars)
        cls = f"{ID}-{slug}"
        opts.append(f"      - label: {label}\n        value: {cls}")
        light = variant_decls(host, member, "light", app)
        dark = variant_decls(host, member, "dark", app)
        both = {k: v for k, v in light.items() if dark.get(k) == v}
        light = {k: v for k, v in light.items() if k not in both}
        dark = {k: v for k, v in dark.items() if k not in both}
        if both:
            blocks.append(css_block(f"body.{cls}", both))
        if light:
            blocks.append(css_block(f".theme-light.{cls}", light))
        if dark:
            blocks.append(css_block(f".theme-dark.{cls}", dark))
    settings = (f"/* @settings\nname: {NAME}\nid: {ID}\nsettings:\n"
                f"  - id: {ID}-variant\n    title: Variant\n"
                f"    description: Another theme of the collection in this one's layout\n"
                f"    type: class-select\n    allowEmpty: false\n    default: {ID}-default\n"
                f"    options:\n" + "\n".join(opts) + "\n*/\n")
    generated = f"{START}\n\n{settings}\n" + "\n".join(blocks) + "\n" + END
    out = re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: generated, source, flags=re.S)
    (ROOT / "theme.css").write_text(out)
    print(f"theme.css: {len(MEMBERS)} variants, {len(generated):,} bytes generated")
    for name, slugs in sorted(LEFT.items()):
        print(f"  {name} keeps this theme's value in: {', '.join(sorted(set(slugs)))}")


if __name__ == "__main__":
    main()
