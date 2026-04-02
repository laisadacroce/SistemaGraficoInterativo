def window_to_viewport(x_w, y_w, window, viewport):
    """
    Transforms a point from window (world) coordinates to viewport (screen) coordinates.

    window:   (x_min, y_min, x_max, y_max) — the world rectangle we're looking at.
    viewport: (x_min, y_min, x_max, y_max) — the screen rectangle we draw into.

    Uses uniform scaling to avoid distortion.
    """
    wx_min, wy_min, wx_max, wy_max = window
    vx_min, vy_min, vx_max, vy_max = viewport

    # Scale factors for x and y
    sx = (vx_max - vx_min) / (wx_max - wx_min)
    sy = (vy_max - vy_min) / (wy_max - wy_min)

    # Use the smaller scale factor to maintain aspect ratio
    s = min(sx, sy)

    # Center the result in the viewport (the axis with leftover space gets centered)
    used_width = (wx_max - wx_min) * s
    used_height = (wy_max - wy_min) * s
    offset_x = vx_min + ((vx_max - vx_min) - used_width) / 2
    offset_y = vy_min + ((vy_max - vy_min) - used_height) / 2

    x_vp = (x_w - wx_min) * s + offset_x
    y_vp = (wy_max - y_w) * s + offset_y
    return x_vp, y_vp