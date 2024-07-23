from io import StringIO

from pip._vendor.rich.console import Console, RenderableType


def render_to_text(
    renderable: RenderableType,
    *,
    color: bool = False,
) -> str:
    with StringIO() as stream:
        console = Console(
            force_terminal=False,
            file=stream,
            color_system="truecolor" if color else None,
            soft_wrap=True,
        )
        console.print(renderable)
        return stream.getvalue()
