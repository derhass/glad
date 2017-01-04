from glad.lang.c.loader.egl import EGLCLoader
from glad.lang.c.loader.gl import OpenGLCLoader
from glad.lang.c.loader.gl_struct import OpenGLCStructLoader
from glad.lang.c.loader.glx import GLXCLoader
from glad.lang.c.loader.wgl import WGLCLoader

from glad.lang.c.generator import CGenerator
from glad.lang.c.debug import CDebugGenerator
from glad.lang.c.struct import CStructGenerator


_specs = {
    'egl': EGLCLoader,
    'gl': OpenGLCLoader,
    'gl_struct': OpenGLCStructLoader,
    'glx': GLXCLoader,
    'wgl': WGLCLoader
}

_generators = {
    'c': CGenerator,
    'c-debug': CDebugGenerator,
    'c-struct': CStructGenerator
}


def get_generator(name, spec):
    gen = _generators.get(name)
    if name == 'c-struct':
        spec = spec + '_struct'
    loader = _specs.get(spec)

    return gen, loader

