import sys
import logging, colorlog

logging.addLevelName(logging.INFO, 'info')
logging.addLevelName(logging.WARNING, 'warning')
logging.addLevelName(logging.ERROR, 'error')

def get_logger(name):
    formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s: %(message)s',
        log_colors={
		'debug':    'cyan',
		'info':     'green',
		'warning':  'yellow',
		'error':    'red',
		'critical': 'red,bg_white',
	},
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.addHandler(handler)
    logger.setLevel('info')
    return logger

def pcbnew_error(logger):
    logger.error('Failed to import pcbnew. Make sure you installed `kicad-to-openpnp` with access to system site packages:')
    logger.error('  pipx install --system-site-packages kicad-to-openpnp')
    sys.exit(1)

def parse_id_map(spec):
    id_map = {}
    if spec:
        for pair in spec.split(','):
            old, new = pair.split('=')
            id_map[old.strip()] = new.strip()
    return id_map
