import random


random.seed(42)

step = 256
cur = 128

bb_colors = {}
i = 0


def color_label(l: str) -> str:
    global cur, step
    if bb_colors.get(l) is None:
        cur = random.randint(0, 255)
        r = hex((cur + 192) % 256)[2:]
        g = hex((cur + 86) % 256)[2:]
        b = hex(cur % 256)[2:]

        if len(r) == 1:
            r = "0" + r
        if len(b) == 1:
            b = "0" + b
        if len(g) == 1:
            g = "0" + g

        bb_colors[l] = f"#{r}{g}{b}"

        # cur += step
        # if cur >= 256:
        #     step //= 2
        #     cur = step // 2

    return f'<B><font color="{bb_colors[l]}">{l}</font></B>'
