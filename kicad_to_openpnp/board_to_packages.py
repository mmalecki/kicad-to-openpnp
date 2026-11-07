#!/usr/bin/env python3
import re
import argparse
from os import path

from xml.etree.ElementTree import Element, fromstring, tostring, indent

from .footprint_to_package import footprint_to_package
from .kicad_utils import load_library_footprint, include_footprint
from .xml_utils import extend_by_id
from .cli_utils import get_logger, pcbnew_error, parse_id_map
from .const import INDENT, PRETTY_INDENT

logger = get_logger('board-to-packages')

try:
    import pcbnew
except:
    pcbnew_error(logger)


def board_to_packages(board, project_dir=None, id_map=None):
    id_map = id_map or {}
    footprints = board.GetFootprints()
    packages = {}
    for footprint in footprints:
        id = footprint.GetFPIDAsString() 

        fpid = footprint.GetFPID()
        lib = fpid.GetFullLibraryName()
        name = fpid.GetUniStringLibItemName()

        # Prefer the library copy of the footprint (clean local coordinates
        # plus description), but fall back to the board-embedded copy when the
        # library cannot be resolved (project-local libraries, etc.).
        if id not in packages and include_footprint(footprint):
            library_footprint = None
            try:
                library_footprint = load_library_footprint(lib, name, project_dir)
            except Exception:
                library_footprint = None
            if library_footprint is None:
                logger.warning(f'Unable to find library footprint for {lib}:{name}, using board-embedded footprint')
                library_footprint = footprint

            packages[id] = footprint_to_package(library_footprint)
            if name in id_map:
                packages[id].set('id', id_map[name])
    
    p = Element('openpnp-packages')
    p.extend(filter(lambda p: p is not None, packages.values()))
    return p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--board', '-b', type=str, required=True,
                        help='KiCad board file')
    parser.add_argument('--join', '-j', help='Join with given packages file. Existing packages are given precedence.', type=str, default=None)
    parser.add_argument('--id-map', type=str, default=None,
                        help='Rename footprint-derived package ids, e.g. C_0603=C0603,Pico_Module=Pico-Module-RM2')
    parser.add_argument('--pretty', '-p', help='Pretty print the output? Default is to output with OpenPnP formatting settings', action='store_true')

    args = parser.parse_args()

    board = pcbnew.LoadBoard(args.board)
    packages = board_to_packages(board, project_dir=path.dirname(path.abspath(args.board)), id_map=parse_id_map(args.id_map))

    if args.join is not None:
        with open(args.join) as join:
            packages = extend_by_id(fromstring(join.read()), packages)

    indent(packages, space=PRETTY_INDENT if args.pretty else INDENT)

    out = tostring(packages, encoding='unicode')
    # Try to get as close to OpenPnP formatting as possible.
    if not args.pretty:
        out = re.sub(r' />$', '/>', out, flags=re.MULTILINE)
    print(out)

if __name__ == "__main__":
    main()
