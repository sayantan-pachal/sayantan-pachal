import os
import json
import math
import base64
import mimetypes
import urllib.request
from html import escape

def get_base64_image(image_source):
    """Converts a local file path or URL into a Base64 data URI so GitHub's SVG proxy renders it."""
    if not image_source:
        return None
    if image_source.startswith("data:image/"):
        return image_source
    try:
        if image_source.startswith("http://") or image_source.startswith("https://"):
            req = urllib.request.Request(image_source, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw_data = resp.read()
                content_type = resp.headers.get_content_type() or "image/png"
        else:
            if not os.path.exists(image_source):
                return None
            with open(image_source, "rb") as f:
                raw_data = f.read()
            content_type, _ = mimetypes.guess_type(image_source)
            if image_source.endswith(".svg"):
                content_type = "image/svg+xml"
            elif not content_type:
                content_type = "image/png"
        b64 = base64.b64encode(raw_data).decode("utf-8")
        return f"data:{content_type};base64,{b64}"
    except Exception as e:
        print(f"Warning: Could not load image '{image_source}': {e}")
        return None

def wrap_text(text, max_chars=44):
    """Wraps description text into at most 2 clean lines with ellipsis if needed."""
    words = text.split()
    lines = []
    current = ""
    for w in words:
        if len(current) + len(w) + (1 if current else 0) <= max_chars:
            current = f"{current} {w}" if current else w
        else:
            lines.append(current)
            current = w
            if len(lines) == 2:
                break
    if len(lines) < 2 and current:
        lines.append(current)
    elif len(lines) == 2 and current:
        if len(lines[1]) > max_chars - 3:
            lines[1] = lines[1][:max_chars - 3] + "..."
        else:
            lines[1] = lines[1] + "..."
    while len(lines) < 2:
        lines.append("")
    return lines[:2]

def render_donut(cx, cy, langs):
    """Generates SVG circle segments for the language percentage donut chart."""
    r = 28
    circumference = 2 * math.pi * r
    svg_parts = [f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" class="donut-track" stroke-width="8" />']
    
    offset = 0.0
    for lang in langs:
        pct = max(0, min(100, float(lang.get("percent", 0))))
        seg_len = (pct / 100.0) * circumference
        color = escape(str(lang.get("color", "#a78bfa")))
        if seg_len > 0:
            svg_parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="8" '
                f'stroke-dasharray="{seg_len:.2f} {circumference:.2f}" stroke-dashoffset="{-offset:.2f}" '
                f'transform="rotate(-90 {cx} {cy})" />'
            )
            offset += seg_len

    top_pct = int(round(float(langs[0].get("percent", 0)))) if langs else 0
    svg_parts.append(
        f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" class="donut-pct">{top_pct}%</text>'
    )
    return "\n      ".join(svg_parts)

def build_projects_svg():
    with open("projects.json", "r", encoding="utf-8") as f:
        projects = json.load(f)

    cols = 2
    rows = math.ceil(len(projects) / cols)
    
    card_w = 544
    card_h = 205
    gap_x = 24
    gap_y = 22
    start_x = 34
    start_y = 84

    total_w = 1180
    total_h = start_y + rows * card_h + max(0, rows - 1) * gap_y + 34

    cards_svg = []

    for idx, proj in enumerate(projects):
        col = idx % cols
        row = idx // cols
        cx = start_x + col * (card_w + gap_x)
        cy = start_y + row * (card_h + gap_y)

        repo = escape(proj.get("repo", "sayantan-pachal/project"))
        title = escape(proj.get("title", "Project"))
        desc = proj.get("description", "")
        tags = proj.get("tags", [])[:4]
        stars = escape(str(proj.get("stars", 0)))
        updated = escape(proj.get("updated", "updated recently"))
        langs = proj.get("languages", [])[:3]
        
        has_langs = len(langs) > 0
        desc_max_chars = 42 if has_langs else 62
        line1, line2 = [escape(l) for l in wrap_text(desc, max_chars=desc_max_chars)]

        # Icon / Image handling
        img_uri = get_base64_image(proj.get("image", ""))
        icon_x = cx + 20
        icon_y = cy + 54
        clip_id = f"iconClip{idx}"
        
        if img_uri:
            icon_svg = f"""
      <clipPath id="{clip_id}">
        <circle cx="{icon_x + 22}" cy="{icon_y + 22}" r="22" />
      </clipPath>
      <circle cx="{icon_x + 22}" cy="{icon_y + 22}" r="23" class="icon-ring" />
      <image href="{img_uri}" x="{icon_x}" y="{icon_y}" width="44" height="44" preserveAspectRatio="xMidYMid slice" clip-path="url(#{clip_id})" />"""
        else:
            icon_text = escape(proj.get("icon_text", title[:2].upper()))
            icon_bg = escape(proj.get("icon_bg", "#2563EB"))
            icon_svg = f"""
      <circle cx="{icon_x + 22}" cy="{icon_y + 22}" r="22" fill="{icon_bg}" fill-opacity="0.18" stroke="{icon_bg}" stroke-width="1.5" />
      <text x="{icon_x + 22}" y="{icon_y + 27}" text-anchor="middle" font-size="15" font-weight="700" fill="{icon_bg}">{icon_text}</text>"""

        # Tags / Pills rendering
        tags_svg = []
        pill_x = cx + 78
        pill_y = cy + 136
        for tag in tags:
            t_str = escape(str(tag))
            pw = max(44, len(t_str) * 7.8 + 20)
            tags_svg.append(
                f'<rect x="{pill_x:.1f}" y="{pill_y}" width="{pw:.1f}" height="22" rx="11" class="tag-pill" />'
                f'<text x="{pill_x + pw/2:.1f}" y="{pill_y + 15}" text-anchor="middle" class="tag-txt">{t_str}</text>'
            )
            pill_x += pw + 8

        # Languages + Donut rendering
        lang_section_svg = ""
        if has_langs:
            lang_list_items = []
            ly = cy + 92
            for l_item in langs:
                l_name = escape(str(l_item.get("name", "")))
                l_pct = int(round(float(l_item.get("percent", 0))))
                l_col = escape(str(l_item.get("color", "#a78bfa")))
                lang_list_items.append(
                    f'<circle cx="{cx + 358}" cy="{ly - 4}" r="3.5" fill="{l_col}" />'
                    f'<text x="{cx + 368}" y="{ly}" class="lang-txt">{l_name} <tspan class="lang-pct">{l_pct}%</tspan></text>'
                )
                ly += 20
            donut_svg = render_donut(cx + 492, cy + 108, langs)
            lang_section_svg = "\n      ".join(lang_list_items) + "\n      " + donut_svg

        card_block = f"""
    <!-- Card {idx + 1}: {title} -->
    <g>
      <rect x="{cx}" y="{cy}" width="{card_w}" height="{card_h}" rx="12" class="proj-card" />
      <line x1="{cx}" y1="{cy + 36}" x2="{cx + card_w}" y2="{cy + 36}" class="card-div" />
      
      <!-- Repo Header -->
      <circle cx="{cx + 20}" cy="{cy + 19}" r="2.5" fill="#22D3EE" />
      <a href="https://github.com/{repo}" target="_blank" rel="noopener noreferrer">
        <text x="{cx + 30}" y="{cy + 23}" class="repo-path">{repo}</text>
      </a>
      <circle cx="{cx + card_w - 20}" cy="{cy + 19}" r="4" class="status-dot" />

      <!-- Project Avatar / Icon -->
      {icon_svg}

      <!-- Title & Description -->
      <a href="https://github.com/{repo}" target="_blank" rel="noopener noreferrer">
        <text x="{cx + 78}" y="{cy + 71}" class="proj-title">{title}<tspan fill="#22D3EE">_</tspan></text>
      </a>
      <text x="{cx + 78}" y="{cy + 94}" class="proj-desc">{line1}</text>
      <text x="{cx + 78}" y="{cy + 113}" class="proj-desc">{line2}</text>

      <!-- Tech Stack Pills -->
      {" ".join(tags_svg)}

      <!-- Bottom Meta (Stars & Updated) -->
      <text x="{cx + 78}" y="{cy + 184}" class="meta-star">★ <tspan class="meta-val">{stars}</tspan></text>
      <text x="{cx + 122}" y="{cy + 184}" class="meta-upd">{updated}</text>

      <!-- Right Column: Languages & Donut -->
      {lang_section_svg}
    </g>"""
        cards_svg.append(card_block)

    svg_template = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_w}" height="{total_h}" viewBox="0 0 {total_w} {total_h}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace" role="img" aria-label="Sayantan Pachal — projects.sh --all">
  <defs>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#2563EB">
        <animate attributeName="stop-color" values="#2563EB;#06B6D4;#10B981;#2563EB" dur="10s" repeatCount="indefinite" />
      </stop>
      <stop offset="0.5" stop-color="#06B6D4">
        <animate attributeName="stop-color" values="#06B6D4;#10B981;#2563EB;#06B6D4" dur="10s" repeatCount="indefinite" />
      </stop>
      <stop offset="1" stop-color="#10B981">
        <animate attributeName="stop-color" values="#10B981;#2563EB;#06B6D4;#10B981" dur="10s" repeatCount="indefinite" />
      </stop>
    </linearGradient>
    <filter id="glow8" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="6" />
    </filter>
    <clipPath id="winClip">
      <rect x="2" y="2" width="{total_w - 4}" height="{total_h - 4}" rx="16" />
    </clipPath>
  </defs>

  <style>
    /* Light Mode (Default) */
    .bg-win {{ fill: #F8FAFC; }}
    .bg-head {{ fill: #F1F5F9; }}
    .win-div {{ stroke: rgba(15, 23, 42, 0.10); }}
    .hdr-main {{ fill: #0891B2; font-size: 14px; font-weight: 700; letter-spacing: 2px; }}
    .hdr-cmd {{ fill: #64748B; font-size: 13px; }}
    .proj-card {{ fill: #FFFFFF; stroke: rgba(8, 145, 178, 0.28); stroke-width: 1.2; }}
    .card-div {{ stroke: rgba(15, 23, 42, 0.08); stroke-width: 1; }}
    .repo-path {{ fill: #475569; font-size: 12px; }}
    .status-dot {{ fill: #94A3B8; opacity: 0.5; }}
    .icon-ring {{ fill: #0F172A; stroke: rgba(8, 145, 178, 0.35); stroke-width: 1.2; }}
    .proj-title {{ fill: #0F172A; font-size: 18px; font-weight: 700; }}
    .proj-desc {{ fill: #475569; font-size: 11.5px; }}
    .tag-pill {{ fill: rgba(124, 58, 237, 0.08); stroke: rgba(124, 58, 237, 0.35); stroke-width: 1; }}
    .tag-txt {{ fill: #6D28D9; font-size: 10.5px; font-weight: 600; }}
    .meta-star {{ fill: #0891B2; font-size: 11.5px; font-weight: 600; }}
    .meta-val {{ fill: #0F172A; }}
    .meta-upd {{ fill: #64748B; font-size: 11.5px; }}
    .lang-txt {{ fill: #334155; font-size: 11px; font-weight: 600; }}
    .lang-pct {{ fill: #64748B; font-weight: 400; }}
    .donut-track {{ stroke: #E2E8F0; }}
    .donut-pct {{ fill: #0F172A; font-size: 11.5px; font-weight: 700; }}

    /* Dark Mode (Auto-detected) */
    @media (prefers-color-scheme: dark) {{
      .bg-win {{ fill: #070B14; }}
      .bg-head {{ fill: #0B1120; }}
      .win-div {{ stroke: rgba(148, 163, 184, 0.12); }}
      .hdr-main {{ fill: #22D3EE; }}
      .hdr-cmd {{ fill: #64748B; }}
      .proj-card {{ fill: #0B111E; stroke: rgba(34, 211, 238, 0.22); stroke-width: 1.2; }}
      .card-div {{ stroke: rgba(148, 163, 184, 0.10); stroke-width: 1; }}
      .repo-path {{ fill: #94A3B8; }}
      .status-dot {{ fill: #475569; opacity: 0.7; }}
      .icon-ring {{ fill: #050811; stroke: rgba(34, 211, 238, 0.35); }}
      .proj-title {{ fill: #F8FAFC; }}
      .proj-desc {{ fill: #94A3B8; }}
      .tag-pill {{ fill: rgba(139, 92, 246, 0.15); stroke: rgba(167, 139, 250, 0.40); stroke-width: 1; }}
      .tag-txt {{ fill: #C4B5FD; }}
      .meta-star {{ fill: #22D3EE; }}
      .meta-val {{ fill: #CBD5E1; }}
      .meta-upd {{ fill: #64748B; }}
      .lang-txt {{ fill: #CBD5E1; }}
      .lang-pct {{ fill: #94A3B8; }}
      .donut-track {{ stroke: #1E293B; }}
      .donut-pct {{ fill: #F8FAFC; }}
    }}
  </style>

  <g clip-path="url(#winClip)">
    <rect x="2" y="2" width="{total_w - 4}" height="{total_h - 4}" class="bg-win" />
    <rect x="2" y="2" width="{total_w - 4}" height="58" class="bg-head" />
    <line x1="2" y1="60" x2="{total_w - 2}" y2="60" class="win-div" />

    <!-- Top Terminal Bar -->
    <text x="36" y="37" class="hdr-main">PROJECTS.LIST</text>
    <text x="195" y="37" class="hdr-cmd">./projects.sh --all</text>

    {"".join(cards_svg)}
  </g>

  <!-- Outer Glowing Frame -->
  <rect x="3" y="3" width="{total_w - 6}" height="{total_h - 6}" rx="15" fill="none" stroke="url(#accent)" stroke-width="2.5" opacity="0.55" filter="url(#glow8)" />
  <rect x="3" y="3" width="{total_w - 6}" height="{total_h - 6}" rx="15" fill="none" stroke="url(#accent)" stroke-width="1.4" />
</svg>"""

    os.makedirs("assets", exist_ok=True)
    out_file = os.path.join("assets", "projects.svg")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(svg_template)
    print(f"Successfully generated {out_file} from projects.json")

if __name__ == "__main__":
    build_projects_svg()