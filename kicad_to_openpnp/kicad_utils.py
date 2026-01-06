from os import getenv, path
from typing import Dict
import json
import sexpdata
import pcbnew

from OCP.STEPControl import STEPControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

_pcbnew_version = getenv('KICAD_VERSION', pcbnew.Version()).split('.')
_pcbnew_major = _pcbnew_version[0]
_pcbnew_minor = _pcbnew_version[1]

_ver_prefix = f'KICAD{_pcbnew_major}_'
_fp_dir = f'{_ver_prefix}FOOTPRINT_DIR'

_kicad_prefix = getenv('KICAD_PREFIX', '/usr')

def load_templating_vars():
    # Try to default the necessary ones
    model_dir = getenv(f'{_ver_prefix}3DMODEL_DIR', f'{_kicad_prefix}/share/kicad/3dmodels')
    footprint_dir = getenv(_fp_dir, f'{_kicad_prefix}/share/kicad/footprints')

    kicad_env_vars = {
        f'{_ver_prefix}3DMODEL_DIR': model_dir,
        _fp_dir: footprint_dir
    }
    try:
        with open(f"{getenv("HOME")}/.config/kicad/{_pcbnew_major}.{_pcbnew_minor}/kicad_common.json") as f:
            kicad_env_vars.update(json.loads(f.read())["environment"]["vars"])
    finally:
        return kicad_env_vars

def _s_exp_find_row(sym: sexpdata.Symbol, table):
    return next((row for row in table if row[0] == sym), None)

def template_path(p: str, v: Dict[str, str]):
    for var, value in v.items():
        p = p.replace("${" + var + "}", value)
    return p

templating_vars = load_templating_vars()

URI = sexpdata.Symbol('uri')
NAME = sexpdata.Symbol('name')
LIB = sexpdata.Symbol('lib')
def load_library_paths(kicad_env_vars: Dict[str, str]):
    with open(f"{getenv("HOME")}/.config/kicad/{_pcbnew_major}.{_pcbnew_minor}/fp-lib-table") as f:
        table = sexpdata.loads(f.read())
        libs = [item for item in table if item[0] == LIB]
        return { _s_exp_find_row(NAME, item)[1]: template_path(_s_exp_find_row(URI, item)[1], kicad_env_vars) for item in libs }

library_paths = {}

try:
    library_paths = load_library_paths(templating_vars)
except:
    pass

def model_to_dimensions(filename: str, rotation=(0, 0, 0)):
    reader = STEPControl_Reader()
    status = reader.ReadFile(filename)
    if status != IFSelect_RetDone:
        raise RuntimeError("Failed to read STEP file")
    reader.TransferRoots()
    shape = reader.OneShape()

    bbox = Bnd_Box()
    bbox.SetGap(0.0)

    lib = BRepBndLib()
    lib.AddOptimal_s(shape, bbox)

    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    return {
        "width": xmax - xmin,
        "length": ymax - ymin,
        "height" : zmax - zmin
    }

def load_library_footprint(lib: str, name: str):
    if lib in library_paths:
        return pcbnew.FootprintLoad(library_paths[lib], name)
    else: # Fall back to stock footprint directory
        return pcbnew.FootprintLoad(path.join(templating_vars[_fp_dir], f'{lib}.pretty'), name)

def include_footprint(fp: pcbnew.FOOTPRINT):
    return not fp.IsDNP() and not fp.IsExcludedFromPosFiles() and fp.GetTypeName() == 'SMD'
