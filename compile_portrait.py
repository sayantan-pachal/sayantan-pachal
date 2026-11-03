from PIL import Image

def image_to_svg_paths(image_path, width=300, height=340, slices=24):
    img = Image.open(image_path).convert("L").resize((width, height), Image.Resampling.LANCZOS)
    # Apply Floyd-Steinberg dithering to 1-bit monochrome
    dithered = img.convert("1")
    pixels = dithered.load()

    slice_paths = [[] for _ in range(slices)]
    for y in range(height):
        x = 0
        while x < width:
            if pixels[x, y] > 128:  # Bright pixel
                run_start = x
                while x < width and pixels[x, y] > 128:
                    x += 1
                run_len = x - run_start
                bucket = (y + run_start) % slices
                slice_paths[bucket].append(f"M{run_start} {y}h{run_len}v1h-{run_len}z")
            else:
                x += 1

    svg_groups = ['<g id="portraitMatrix" fill="#A78BFA" shape-rendering="crispEdges">']
    for i, cmds in enumerate(slice_paths):
        delay = round(0.20 + (i / slices) * 1.9, 2)
        d_str = "".join(cmds)
        svg_groups.append(
            f'  <g opacity="0">'
            f'<animate attributeName="opacity" values="0;1" dur="0.9s" begin="{delay}s" fill="freeze" />'
            f'<path d="{d_str}" /></g>'
        )
    svg_groups.append("</g>")
    return "\n".join(svg_groups)

if __name__ == "__main__":
    # Pass your portrait photo path and paste the output over <g id="portraitMatrix">...</g>
    print(image_to_svg_paths("portrait.jpg"))
