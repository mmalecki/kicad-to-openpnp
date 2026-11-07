import sys
from os import getenv, path
from typing import Dict
import json
import sexpdata
import pcbnew

_pcbnew_version = getenv('KICAD_VERSION', pcbnew.Version()).split('.')
_pcbnew_major = _pcbnew_version[0]
_pcbnew_minor = _pcbnew_version[1]

_ver_prefix = f'KICAD{_pcbnew_major}_'
_fp_dir = f'{_ver_prefix}FOOTPRINT_DIR'

# Default prefix: KiCad's bundled Python lives at <prefix>/bin/python.exe on
# Windows and macOS bundles, so derive the prefix from the running executable.
# Falls back to /usr for distro-packaged KiCad.
_exe_dir = path.dirname(sys.executable)
_kicad_prefix = getenv('KICAD_PREFIX', path.dirname(_exe_dir) if path.basename(_exe_dir).lower() == 'bin' else '/usr')

def config_dir():
    if sys.platform == 'win32':
        base = getenv('APPDATA') or path.expanduser('~')
        return path.join(base, 'kicad', f'{_pcbnew_major}.{_pcbnew_minor}')
    return path.join(path.expanduser('~'), '.config', 'kicad', f'{_pcbnew_major}.{_pcbnew_minor}')

def load_templating_vars():
    # Try to default the necessary ones
    model_dir = getenv(f'{_ver_prefix}3DMODEL_DIR', f'{_kicad_prefix}/share/kicad/3dmodels')
    footprint_dir = getenv(_fp_dir, f'{_kicad_prefix}/share/kicad/footprints')

    kicad_env_vars = {
        f'{_ver_prefix}3DMODEL_DIR': model_dir,
        _fp_dir: footprint_dir
    }
    try:
        with open(path.join(config_dir(), 'kicad_common.json')) as f:
            kicad_env_vars.update(json.loads(f.read())["environment"]["vars"])
    except Exception:
        pass
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
LIB_TYPE = sexpdata.Symbol('type')

def _parse_lib_table(filepath: str, kicad_env_vars: Dict[str, str]) -> Dict[str, str]:
    with open(filepath) as f:
        table = sexpdata.loads(f.read())
    paths = {}
    for item in table:
        if not isinstance(item, list) or item[0] != LIB:
            continue
        name_row = _s_exp_find_row(NAME, item)
        uri_row = _s_exp_find_row(URI, item)
        type_row = _s_exp_find_row(LIB_TYPE, item)
        if name_row is None or uri_row is None:
            continue
        if type_row is not None and type_row[1] == 'Table':
            # Nested library table (e.g. the stock KiCad libraries) — resolve
            # it and merge its entries.
            nested = template_path(uri_row[1], kicad_env_vars)
            if path.isfile(nested):
                try:
                    paths.update(_parse_lib_table(nested, kicad_env_vars))
                except Exception:
                    pass
            continue
        paths[name_row[1]] = template_path(uri_row[1], kicad_env_vars)
    return paths

def load_library_paths(kicad_env_vars: Dict[str, str], project_dir: str = None) -> Dict[str, str]:
    paths = {}
    try:
        paths = _parse_lib_table(path.join(config_dir(), 'fp-lib-table'), kicad_env_vars)
    except Exception:
        pass
    if project_dir is not None:
        project_table = path.join(project_dir, 'fp-lib-table')
        if path.isfile(project_table):
            vars_with_project = dict(kicad_env_vars)
            vars_with_project['KIPRJMOD'] = project_dir
            try:
                paths.update(_parse_lib_table(project_table, vars_with_project))
            except Exception:
                pass
    return paths

library_paths = load_library_paths(templating_vars)

def model_to_dimensions(filename: str, rotation=(0, 0, 0)):
    # Lazy imports: OCP is a heavy dependency only needed when a STEP model
    # actually has to be measured.
    from OCP.STEPControl import STEPControl_Reader
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.Bnd import Bnd_Box
    from OCP.BRepBndLib import BRepBndLib

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
    width = xmax - xmin
    length = ymax - ymin
    # The bounding box is measured in the model's own frame. If the model is
    # rotated by a right angle about Z inside the footprint, width and length
    # swap. m_Rotation is exposed differently across pcbnew versions, so
    # accept both indexable tuples and objects with a `z` attribute.
    rot_z = 0
    try:
        rot_z = rotation[2]
    except Exception:
        rot_z = getattr(rotation, 'z', 0)
    if round(rot_z) % 180 == 90:
        width, length = length, width
    return {
        "width": width,
        "length": length,
        "height" : zmax - zmin
    }

def load_library_footprint(lib: str, name: str, project_dir: str = None):
    paths = library_paths
    if project_dir is not None:
        paths = load_library_paths(templating_vars, project_dir)
    if lib in paths:
        return pcbnew.FootprintLoad(paths[lib], name)
    else: # Fall back to stock footprint directory
        return pcbnew.FootprintLoad(path.join(templating_vars[_fp_dir], f'{lib}.pretty'), name)

def include_footprint(fp: pcbnew.FOOTPRINT):
    return not fp.IsDNP() and not fp.IsExcludedFromPosFiles() and fp.GetTypeName() == 'SMD'
