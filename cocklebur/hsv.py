# http://www.cs.rit.edu/~ncs/color/t_convert.html

def HSVtoRGB(h, s, v):
    v = float(v)
    if not s:
        # achromatic (grey)
        return v, v, v
    h *= 6.0                    # sector 0 to 5
    i = int(h)
    f = h - i                   # factorial part of h
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    if i == 0:
        return v, t, p
    elif i == 1:
        return q, v, p
    elif i == 2:
        return p, v, t
    elif i == 3:
        return p, q, v
    elif i == 4:
        return t, p, v
    elif i == 5:
        return v, p, q
    else:
        raise ValueError('Hue outside 0<1 range')
