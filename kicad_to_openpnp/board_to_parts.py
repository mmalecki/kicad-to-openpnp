import re
import argparse
import pcbnew
from xml.etree.ElementTree import fromstring, Element, tostring, indent

from .footprint_to_package import footprint_model_to_dimensions
from .const import UNITS, INDENT
from .xml_utils import extend_by_id

def footprint_to_part(footprint: pcbnew.FOOTPRINT):
    part = Element('part')
    part.set('height-units', UNITS)
    part.set('package-id', footprint.GetFPID().GetUniStringLibItemName())
    part.set('speed', str(1.0))
    part.set('pick-retry-count', str(0))

    models = footprint.Models()
    # TODO: footprint name-based heretics: https://klc.kicad.org/footprint/f2/f2.2.html
    dimensions = footprint_model_to_dimensions(models[0]) if models.size() > 0 else None

    if dimensions is not None:
        part.set('height', str(dimensions["height"]))

    return part


def board_to_parts(board):
    footprints = board.GetFootprints()
    parts = {}
    for footprint in footprints:
        fpid = footprint.GetFPID() 
        value = footprint.GetValueAsString()

        id = f'{fpid.GetUniStringLibItemName()}-{value}'

        # There's no harm in using the body height from the 3D model on the board (as
        # opposed to the library). Even if it's changed from the default one, offset,
        # or resized, that's an explicit action by the user.
        if id not in parts and not footprint.IsDNP() and not footprint.IsExcludedFromPosFiles():
            parts[id] = footprint_to_part(footprint)
            parts[id].set('id', id)
    
    p = Element('openpnp-parts')
    p.extend(parts.values())
    return p

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--board', '-b', type=str, required=True,
                        help='KiCad board file')
    parser.add_argument('--pretty', '-p', help='Pretty print the output?', action='store_true')
    parser.add_argument('--join', '-j', help='Join with given parts file. Existing parts are given precedence.', type=str, default=None)

    args = parser.parse_args()

    board = pcbnew.LoadBoard(args.board)
    parts = board_to_parts(board)

    if args.join is not None:
        with open(args.join) as join:
            parts = extend_by_id(fromstring(join.read()), parts)

    indent(parts, space=INDENT)

    out = tostring(parts, encoding='unicode')
    if not args.pretty:
        out = re.sub(r' />$', '/>', out, flags=re.MULTILINE)
    print(out)

if __name__ == "__main__":
    main()
