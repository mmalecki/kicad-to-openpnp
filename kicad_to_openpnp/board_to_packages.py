#!/usr/bin/env python3
import re
import argparse
import pcbnew

from xml.etree.ElementTree import Element, fromstring, tostring, indent

from .footprint_to_package import footprint_to_package
from .kicad_utils import load_library_footprint
from .xml_utils import extend_by_id
from .const import INDENT

def board_to_packages(board):
    footprints = board.GetFootprints()
    packages = {}
    for footprint in footprints:
        id = footprint.GetFPIDAsString() 

        fpid = footprint.GetFPID()
        lib = fpid.GetFullLibraryName()
        name = fpid.GetUniStringLibItemName()

        # We cannot reuse the footprint we just read in from the board,
        # since that gets us positions relative to the board.
        # Read in the library one.
        if id not in packages and not footprint.IsDNP() and not footprint.IsExcludedFromPosFiles():
            packages[id] = footprint_to_package(load_library_footprint(lib, name))
    
    p = Element('openpnp-packages')
    p.extend(packages.values())
    return p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--board', '-b', type=str, required=True,
                        help='KiCad board file')
    parser.add_argument('--join', '-j', help='Join with given packages file. Existing packages are given precedence.', type=str, default=None)
    parser.add_argument('--pretty', '-p', help='Pretty print the output? Default is to output with OpenPnP formatting settings', action='store_true')

    args = parser.parse_args()

    board = pcbnew.LoadBoard(args.board)
    packages = board_to_packages(board)

    if args.join is not None:
        with open(args.join) as join:
            packages = extend_by_id(fromstring(join.read()), packages)

    indent(packages, space=INDENT)

    out = tostring(packages, encoding='unicode')
    # Try to get as close to OpenPnP formatting as possible.
    if not args.pretty:
        out = re.sub(r' />$', '/>', out, flags=re.MULTILINE)
    print(out)

if __name__ == "__main__":
    main()
