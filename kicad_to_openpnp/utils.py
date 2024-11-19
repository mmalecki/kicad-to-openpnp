from os import getenv, path
from typing import Dict
import json
import sexpdata

def _load_templating_vars():
    model_dir = getenv('KICAD8_3DMODEL_DIR', '/usr/share/kicad/3dmodels')
    footprint_dir = getenv('KICAD8_FOOTPRINT_DIR', '/usr/share/kicad/footprints')

    kicad_env_vars = {
        'KICAD8_3DMODEL_DIR': model_dir,
        'KICAD8_FOOTPRINT_DIR': footprint_dir
    }
    try:
        with open(f"{getenv("HOME")}/.config/kicad/8.0/kicad_common.json") as f:
            kicad_env_vars.update(json.loads(f.read())["environment"]["vars"])
    finally:
        return kicad_env_vars

def _template_path(p: str, v: Dict[str, str]):
    for var, value in v.items():
        p = p.replace("${" + var + "}", value)
    return p

def _s_exp_find_row(sym: sexpdata.Symbol, table):
    return next((row for row in table if row[0] == sym), None)
