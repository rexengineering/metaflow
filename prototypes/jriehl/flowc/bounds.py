import ast
import os.path
import collections
from typing import Dict, Iterator, List, Mapping, NamedTuple, Optional, Union

from PIL import ImageFont

from .bpmn2 import dc


FONT_PATH = os.path.join(
    os.path.dirname(__file__), 'data', 'LibreBaskerville-Regular.ttf'
)
FONT : Dict[int, ImageFont.ImageFont] = {
    14: ImageFont.truetype(FONT_PATH, 14)
}
OrderedDictOrListThereof = Union[
    collections.OrderedDict, List[collections.OrderedDict]
]


def get_font(pt_size: int) -> ImageFont.ImageFont:
    global FONT
    result = FONT.get(pt_size)
    if not result:
        result = FONT[pt_size] = ImageFont.truetype(FONT_PATH, pt_size)
    return result


class Bounds(NamedTuple):
    x: float
    y: float
    width: float
    height: float

    @classmethod
    def from_minmax(cls, min_x, min_y, max_x, max_y):
        if min_x > max_x or min_y > max_y:
            raise ValueError(
                'A "minimum" value is greater than an input "max" value.'
            )
        return cls(min_x, min_y, max_x - min_x, max_y - min_y)

    @classmethod
    def from_iter(cls, iter: Iterator[Optional['Bounds']]) -> Optional['Bounds']:
        bounds = list(
            filter(lambda boundary: isinstance(boundary, Bounds), iter)
        )
        if len(bounds) > 0:
            min_x = min(boundary.x for boundary in bounds)
            max_x = max(boundary.x + boundary.width for boundary in bounds)
            min_y = min(boundary.y for boundary in bounds)
            max_y = max(boundary.y + boundary.height for boundary in bounds)
            return cls.from_minmax(min_x, min_y, max_x, max_y)
        return None

    @classmethod
    def from_svg(
            cls,
            tag: str,
            elems: OrderedDictOrListThereof) -> Optional['Bounds']:
        target_method_name = f'from_{tag}'
        if hasattr(cls, target_method_name):
            target_method = getattr(cls, target_method_name)
            if isinstance(elems, list):
                return cls.from_iter(target_method(elem) for elem in elems)
            return target_method(elems)
        return None

    @classmethod
    def from_g(cls, contents: collections.OrderedDict) -> 'Bounds':
        result = cls.from_iter(cls.from_svg(tag, elems) for tag, elems in contents.items())
        assert result is not None
        return result

    @classmethod
    def from_ellipse(cls, ellipse: Mapping[str, str]):
        cx = ast.literal_eval(ellipse['@cx'])
        cy = ast.literal_eval(ellipse['@cy'])
        rx = ast.literal_eval(ellipse['@rx'])
        ry = ast.literal_eval(ellipse['@ry'])
        min_x = cx - rx
        max_x = cx + rx
        min_y = cy - ry
        max_y = cy + ry
        return cls.from_minmax(min_x, min_y, max_x, max_y)

    @classmethod
    def from_polygon(cls, polygon: Mapping[str, str]):
        points = [
            ast.literal_eval(point_str)
            for point_str in polygon['@points'].split()
        ]
        xs, ys = zip(*points)
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        return cls.from_minmax(min_x, min_y, max_x, max_y)

    @classmethod
    def from_text(cls, text: Mapping[str, str]):
        font_family = text['@font-family']
        assert 'serif' in font_family, \
            f'Unsupported font family "{font_family}"'
        font_size = int(ast.literal_eval(text['@font-size']))
        width, height = get_font(font_size).getsize(text['#text'])
        x = ast.literal_eval(text['@x']) - (width/2)
        y = ast.literal_eval(text['@y']) - (height/2)
        return cls(x, y, width, height)

    def to_dc_bounds(self):
        return dc.Bounds(
            x=self.x, y=self.y, width=self.width, height=self.height
        )
