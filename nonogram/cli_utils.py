import matplotlib
import cmasher  # noqa: F401
import rich.color

EMBER_COLORMAP = matplotlib.colormaps["cmr.ember"]
HORIZON_COLORMAP = matplotlib.colormaps["cmr.horizon"]


def ember_colormap(value: float) -> rich.color.Color:
    rgba = EMBER_COLORMAP(value)
    return rich.color.Color.from_rgb(
        255 * rgba[0],
        255 * rgba[1],
        255 * rgba[2],
    )


def horizon_colormap(value: float) -> rich.color.Color:
    rgba = HORIZON_COLORMAP(value)
    return rich.color.Color.from_rgb(
        255 * rgba[0],
        255 * rgba[1],
        255 * rgba[2],
    )
