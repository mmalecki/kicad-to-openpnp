#!/usr/bin/env python3
from os import getenv, path

import argparse
import pcbnew
import cadquery

from xml.etree.ElementTree import Element, SubElement, tostring, indent

OPENPNP_PACKAGE_VERSION = '1.1'
UNITS = 'Millimeters'
INDENT = '  '

# TODO: attempt to resolve env vars based on .config/kicad/8.0/kicad_common'
footprint_dir = getenv('KICAD8_FOOTPRINT_DIR', '/usr/share/kicad/footprints')
model_dir = getenv('KICAD8_3DMODEL_DIR', '/usr/share/kicad/3dmodels')

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


def Package(footprint: pcbnew.FOOTPRINT):
    pkg = Element('package')
    pkg.set('version', OPENPNP_PACKAGE_VERSION)
    pkg.set('description', footprint.GetLibDescription())
    pkg.set('id', footprint.GetFPIDAsString())
    return pkg

def to_milis(x):
    return x / 1000_000

def footprint_models_to_dimensions(model: pcbnew.FP_3DMODEL):
    filename = model.m_Filename.replace('${KICAD8_3DMODEL_DIR}', model_dir)
    if filename.endswith(".wrl"):
        # TODO: handle WRL natively, but for now, many stock 3D models ship with both:
        if path.isfile(filename.replace(".wrl", ".step")):
            filename = filename.replace(".wrl", ".step")

    if filename.endswith(".step"):
        print(f"analyzing model {filename} for dimensions")
        bb = cadquery.importers.importStep(filename).val().BoundingBox()
        return {
                "width": bb.xmax - bb.xmin,
                "height": bb.ymax - bb.ymin
        }
    else:
        print("unable to analyze {filename}, only .step files are supported")
        return None

def footprint_to_package(footprint: pcbnew.FOOTPRINT):
    pads = footprint.Pads()

    pkg = Package(footprint)

    fp = SubElement(pkg, 'footprint')
    fp.set('units', UNITS)

    models = footprint.Models()
    # TODO: footprint name-based heretics: https://klc.kicad.org/footprint/f2/f2.2.html
    dimensions = footprint_models_to_dimensions(models[0]) if models[0] is not None else None

    # TODO: estimate based on component's 3D model
    if dimensions is not None:
        fp.set('body-width', str(dimensions["width"]))
        fp.set('body-height', str(dimensions["height"]))

    for pad in pads:
        p = SubElement(fp, 'pad', name=pad.GetName())
        p.set('width', str(to_milis(pad.GetSizeX())))
        p.set('height', str(to_milis(pad.GetSizeY())))
        p.set('x', str(to_milis(pad.GetX())))
        p.set('y', str(to_milis(pad.GetY())))

        p.set('roundness', str(0))
        p.set('rotation', str(pad.GetOrientationDegrees())) # TBD

        shape = pad.GetShape()
        if shape == pcbnew.PAD_SHAPE_ROUNDRECT:
            p.set('roundness', str(pad.GetRoundRectRadiusRatio()))
        elif shape == pcbnew.PAD_SHAPE_CIRCLE:
            p.set('roundness', str(100))

        # TODO: ovals

    return pkg

if __name__ == "__main__":
    main()
