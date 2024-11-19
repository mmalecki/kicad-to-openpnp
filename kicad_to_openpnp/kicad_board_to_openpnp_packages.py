#!/usr/bin/env python3
import sys
from os import getenv, path

import argparse
import pcbnew
import sexpdata

from xml.etree.ElementTree import Element, tostring, indent

from .kicad_footprint_to_openpnp_package import footprint_to_package
from .utils import _s_exp_find_row, _template_path, _load_templating_vars

INDENT = '  '
LIB = sexpdata.Symbol('lib')
URI = sexpdata.Symbol('uri')
NAME = sexpdata.Symbol('name')

kicad_env_vars = _load_templating_vars()
library_paths = {}

try:
    with open(f"{getenv("HOME")}/.config/kicad/8.0/fp-lib-table") as f:
        table = sexpdata.loads(f.read())
        libs = [item for item in table if item[0] == LIB]
        library_paths = { _s_exp_find_row(NAME, item)[1]: _template_path(_s_exp_find_row(URI, item)[1], kicad_env_vars) for item in libs }
except:
    pass

def board_to_packages(board):
    footprints = board.GetFootprints()
    packages = {}
    for footprint in footprints:
        id = footprint.GetFPIDAsString() 

        id_ = footprint.GetFPID()
        lib = id_.GetFullLibraryName()
        name = id_.GetUniStringLibItemName()

        # We cannot reuse the footprint we just read in from the board,
        # since that gets us positions relative to the board.
        # Read in the library one.
        if id not in packages and not footprint.IsDNP() and not footprint.IsExcludedFromPosFiles():
            packages[id] = footprint_to_package(pcbnew.FootprintLoad(library_paths[lib], name))
    
    p = Element('openpnp-packages')
    p.extend(packages.values())
    return p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--board', '-b', type=str, required=True,
                        help='KiCad board file')
    parser.add_argument('--pretty', '-p', help='Pretty print the output?', action='store_true')

    args = parser.parse_args()

    board = pcbnew.LoadBoard(args.board)
    package = board_to_packages(board)

    if args.pretty:
        indent(package, space=INDENT)
    print(tostring(package, encoding='unicode'))


if __name__ == "__main__":
    main()
