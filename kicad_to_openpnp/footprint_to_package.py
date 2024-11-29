#!/usr/bin/env python3
import sys
from os import path

import argparse
import pcbnew

from xml.etree.ElementTree import Element, SubElement, tostring, indent

from .kicad_utils import template_path, model_to_dimensions, load_library_footprint, templating_vars
from .const import INDENT, UNITS

OPENPNP_PACKAGE_VERSION = '1.1'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--library', '-l', type=str, required=True,
                        help='KiCad library directory containing the footprint (*.pretty)')
    parser.add_argument('--footprint', '-f', type=str, required=True,
                        help='Footprint name')
    parser.add_argument('--pretty', '-p', help='Pretty print the output?', action='store_true')

    args = parser.parse_args()

    # TODO: -f <library>:<footprint>
    package = footprint_to_package(load_library_footprint(args.library, args.footprint))

    if args.pretty:
        indent(package, space=INDENT)
    print(tostring(package, encoding='unicode'))


def to_milis(x):
    return x / 1000_000

def footprint_model_to_dimensions(model: pcbnew.FP_3DMODEL):
    filename = template_path(model.m_Filename, templating_vars)
    if filename.endswith(".wrl"):
        # TODO: handle WRL natively, but for now, many stock 3D models ship with both:
        step = filename.replace(".wrl", ".step")
        if path.isfile(step):
            filename = step

    if filename.endswith(".step"):
        print(f"analyzing model {filename} for dimensions", file=sys.stderr)
        try:
            return model_to_dimensions(filename, rotation=model.m_Rotation)
        except Exception as e:
            print(f"error while analyzing {filename}: {e}", file=sys.stderr)
            return None

    else:
        print(f"unable to analyze {filename}, only .step files are supported", file=sys.stderr)
        return None

def footprint_to_package(footprint: pcbnew.FOOTPRINT):
    pads = footprint.Pads()
    id = footprint.GetFPID().GetUniStringLibItemName()

    pkg = Element('package')
    pkg.set('version', OPENPNP_PACKAGE_VERSION)
    pkg.set('description', footprint.GetLibDescription())
    pkg.set('id', id)

    fp = SubElement(pkg, 'footprint')
    fp.set('units', UNITS)

    models = footprint.Models()
    # TODO: footprint name-based heretics: https://klc.kicad.org/footprint/f2/f2.2.html
    dimensions = footprint_model_to_dimensions(models[0]) if models.size() > 0 else None

    if dimensions is not None:
        fp.set('body-width', str(dimensions["width"]))
        fp.set('body-height', str(dimensions["length"]))
    else:
        print(f"no dimensions found for {id}", file=sys.stderr)

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
