import re
import argparse
import pcbnew
from xml.etree.ElementTree import fromstring, Element, tostring, indent

from .footprint_to_package import footprint_model_to_dimensions
from .const import UNITS, INDENT, PRETTY_INDENT
from .xml_utils import extend_by_id
from .kicad_utils import include_footprint
from .cli_utils import parse_id_map


def footprint_to_part(footprint: pcbnew.FOOTPRINT, id: str, package_id: str):
    part = Element('part')
    # Attributes in the same order OpenPnP writes them.
    part.set('id', id)
    part.set('height-units', UNITS)

    models = footprint.Models()
    # TODO: footprint name-based heretics: https://klc.kicad.org/footprint/f2/f2.2.html
    dimensions = footprint_model_to_dimensions(models[0]) if models.size() > 0 else None

    part.set('height', str(dimensions["height"]) if dimensions is not None else '0.0')
    part.set('through-board-depth-units', UNITS)
    part.set('through-board-depth', str(0.0))
    part.set('package-id', package_id)
    part.set('speed', str(1.0))
    part.set('pick-retry-count', str(0))

    return part


def board_to_parts(board, id_map=None):
    id_map = id_map or {}
    footprints = board.GetFootprints()
    parts = {}
    for footprint in footprints:
        fpid = footprint.GetFPID() 
        footprint_name = fpid.GetUniStringLibItemName()
        value = footprint.GetValueAsString()

        package_id = id_map.get(footprint_name, footprint_name)
        if value in ('', footprint_name):
            # The value field just repeats the footprint name (KiCad default
            # for generic symbols) — don't duplicate it in the part id.
            id = package_id
        else:
            id = f'{package_id}-{value}'

        # There's no harm in using the body height from the 3D model on the board (as
        # opposed to the library). Even if it's changed from the default one, offset,
        # or resized, that's an explicit action by the user.
        if id not in parts and include_footprint(footprint):
            parts[id] = footprint_to_part(footprint, id, package_id)
    
    p = Element('openpnp-parts')
    p.extend(parts.values())
    return p

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--board', '-b', type=str, required=True,
                        help='KiCad board file')
    parser.add_argument('--pretty', '-p', help='Pretty print the output?', action='store_true')
    parser.add_argument('--join', '-j', help='Join with given parts file. Existing parts are given precedence.', type=str, default=None)
    parser.add_argument('--id-map', type=str, default=None,
                        help='Rename footprint-derived part/package ids, e.g. C_0603=C0603,LED_0805=LED0805')

    args = parser.parse_args()

    board = pcbnew.LoadBoard(args.board)
    parts = board_to_parts(board, id_map=parse_id_map(args.id_map))

    if args.join is not None:
        with open(args.join) as join:
            parts = extend_by_id(fromstring(join.read()), parts)

    indent(parts, space=PRETTY_INDENT if args.pretty else INDENT)

    out = tostring(parts, encoding='unicode')
    # Try to get as close to OpenPnP formatting as possible.
    if not args.pretty:
        out = re.sub(r' />$', '/>', out, flags=re.MULTILINE)
    print(out)

if __name__ == "__main__":
    main()
