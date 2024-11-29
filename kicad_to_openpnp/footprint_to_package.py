#!/usr/bin/env python3
import sys
from os import getenv, path

import argparse
import pcbnew

from xml.etree.ElementTree import Element, SubElement, tostring, indent

from .utils import _template_path, _load_templating_vars, model_to_dimensions
from .const import INDENT, UNITS

OPENPNP_PACKAGE_VERSION = '1.1'

footprint_dir = getenv('KICAD8_FOOTPRINT_DIR', '/usr/share/kicad/footprints')

kicad_env_vars = _load_templating_vars()
print(f"loaded environment variables: {kicad_env_vars}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--library', '-l', type=str, required=True,
                        help='KiCad library file containing the footprint (*.pretty)')
    parser.add_argument('--footprint', '-f', type=str, required=True,
                        help='Footprint name')
    parser.add_argument('--pretty', '-p', help='Pretty print the output?', action='store_true')

    args = parser.parse_args()

    # TODO: -f <library>:<footprint>
    if not args.library.endswith('.pretty') and '/' not in args.library:
        library = path.join(footprint_dir, f'{args.library}.pretty')
    else:
        library = args.library
    footprint = pcbnew.FootprintLoad(library, args.footprint)
    package = footprint_to_package(footprint)

    if args.pretty:
        indent(package, space=INDENT)
    print(tostring(package, encoding='unicode'))


def to_milis(x):
    return x / 1000_000

def footprint_model_to_dimensions(model: pcbnew.FP_3DMODEL):
    filename = _template_path(model.m_Filename, kicad_env_vars)
    if filename.endswith(".wrl"):
        # TODO: handle WRL natively, but for now, many stock 3D models ship with both:
        step = filename.replace(".wrl", ".step")
        if path.isfile(step):
            filename = step

    if filename.endswith(".step"):
        print(f"analyzing model {filename} for dimensions", file=sys.stderr)
        try:
            return model_to_dimensions(filename)
        except Exception as e:
            print(f"error while analyzing {filename}: {e}", file=sys.stderr)
            return None

    else:
        print(f"unable to analyze {filename}, only .step files are supported", file=sys.stderr)
        return None

def footprint_to_package(footprint: pcbnew.FOOTPRINT):
    pads = footprint.Pads()

    pkg = Element('package')
    pkg.set('version', OPENPNP_PACKAGE_VERSION)
    pkg.set('description', footprint.GetLibDescription())
    pkg.set('id', footprint.GetFPID().GetUniStringLibItemName())

    fp = SubElement(pkg, 'footprint')
    fp.set('units', UNITS)

    models = footprint.Models()
    # TODO: footprint name-based heretics: https://klc.kicad.org/footprint/f2/f2.2.html
    dimensions = footprint_model_to_dimensions(models[0]) if models.size() > 0 else None

    if dimensions is not None:
        fp.set('body-width', str(dimensions["width"]))
        fp.set('body-height', str(dimensions["length"]))

    for pad in pads:
        if pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue

        p = SubElement(fp, 'pad', name=pad.GetName())
        p.set('width', str(to_milis(pad.GetSizeX())))
        p.set('height', str(to_milis(pad.GetSizeY())))
        p.set('x', str(to_milis(pad.GetX())))
        p.set('y', str(to_milis(pad.GetY())))

        p.set('roundness', str(0))
        p.set('rotation', str(pad.GetOrientationDegrees()))

        shape = pad.GetShape()
        if shape == pcbnew.PAD_SHAPE_ROUNDRECT:
            p.set('roundness', str(pad.GetRoundRectRadiusRatio()))
        elif shape == pcbnew.PAD_SHAPE_CIRCLE:
            p.set('roundness', str(100))

    return pkg

if __name__ == "__main__":
    main()
