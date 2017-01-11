from glad.lang.c.loader.gl import OpenGLCLoader
from glad.lang.c.loader import LOAD_OPENGL_DLL, LOAD_OPENGL_DLL_H, LOAD_OPENGL_GLAPI_H


_OPENGL_LOADER = \
    LOAD_OPENGL_DLL % {'pre':'static', 'init':'open_gl',
                       'proc':'get_proc', 'terminate':'close_gl'} + '''
int gladLoadGL(GLADFeatures *features, GLADDispatchTable *dispatch) {
    int status = 0;

    if(open_gl()) {
        status = gladLoadGLLoader(features, dispatch, &get_proc);
        close_gl();
    }

    return status;
}
'''

_OPENGL_HAS_EXT = '''
#if defined(GL_ES_VERSION_3_0) || defined(GL_VERSION_3_0)
#define _GLAD_IS_SOME_NEW_VERSION 1
#endif

static const char *exts = NULL;
static int num_exts_i = 0;
static const char **exts_i = NULL;

static int get_exts(const GLADFeatures *features, const GLADDispatchTable *dispatch) {
#ifdef _GLAD_IS_SOME_NEW_VERSION
    if(features->maxLoadedGLVersion.major < 3) {
#endif
        exts = (const char *)dispatch->GetString(GL_EXTENSIONS);
#ifdef _GLAD_IS_SOME_NEW_VERSION
    } else {
        int index;

        num_exts_i = 0;
        dispatch->GetIntegerv(GL_NUM_EXTENSIONS, &num_exts_i);
        if (num_exts_i > 0) {
            exts_i = (const char **)realloc((void *)exts_i, num_exts_i * sizeof *exts_i);
        }

        if (exts_i == NULL) {
            return 0;
        }

        for(index = 0; index < num_exts_i; index++) {
            exts_i[index] = (const char*)dispatch->GetStringi(GL_EXTENSIONS, index);
        }
    }
#endif
    return 1;
}

static void free_exts(void) {
    if (exts_i != NULL) {
        free((char **)exts_i);
        exts_i = NULL;
    }
}

static int has_ext(const GLADFeatures *features, const char *ext) {
#ifdef _GLAD_IS_SOME_NEW_VERSION
    if(features->maxLoadedGLVersion.major < 3) {
#endif
        const char *extensions;
        const char *loc;
        const char *terminator;
        extensions = exts;
        if(extensions == NULL || ext == NULL) {
            return 0;
        }

        while(1) {
            loc = strstr(extensions, ext);
            if(loc == NULL) {
                return 0;
            }

            terminator = loc + strlen(ext);
            if((loc == extensions || *(loc - 1) == ' ') &&
                (*terminator == ' ' || *terminator == '\\0')) {
                return 1;
            }
            extensions = terminator;
        }
#ifdef _GLAD_IS_SOME_NEW_VERSION
    } else {
        int index;

        for(index = 0; index < num_exts_i; index++) {
            const char *e = exts_i[index];

            if(strcmp(e, ext) == 0) {
                return 1;
            }
        }
    }
#endif

    return 0;
}
'''


_OPENGL_HEADER_START = '''
#ifndef __glad_h_
#define __glad_h_
'''

_OPENGL_HEADER_INCLUDE_ERROR = '''
#ifdef __{0}_h_
#error {1} header already included, remove this include, glad already provides it
#endif
#define __{0}_h_
'''

_OPENGL_HEADER = '''
#if defined(_WIN32) && !defined(APIENTRY) && !defined(__CYGWIN__) && !defined(__SCITECH_SNAP__)
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN 1
#endif
#include <windows.h>
#endif

#ifndef APIENTRY
#define APIENTRY
#endif
#ifndef APIENTRYP
#define APIENTRYP APIENTRY *
#endif

#ifdef __cplusplus
extern "C" {
#endif

struct gladGLversionStruct {
    int major;
    int minor;
};

typedef void* (* GLADloadproc)(const char *name);
''' + LOAD_OPENGL_GLAPI_H + '''
'''

_OPENGL_HEADER_LOADER = '''
typedef struct GLADFeatures_s GLADFeatures;
typedef struct GLADDispatchTable_s GLADDispatchTable;

GLAPI int gladLoadGL(GLADFeatures *features, GLADDispatchTable *dispatch);
''' + LOAD_OPENGL_DLL_H

_OPENGL_HEADER_END = '''
#ifdef __cplusplus
}
#endif

#endif
'''

_FIND_VERSION = '''
    /* Thank you @elmindreda
     * https://github.com/elmindreda/greg/blob/master/templates/greg.c.in#L176
     * https://github.com/glfw/glfw/blob/master/src/context.c#L36
     */
    int i, major, minor;

    const char* version;
    const char* prefixes[] = {
        "OpenGL ES-CM ",
        "OpenGL ES-CL ",
        "OpenGL ES ",
        NULL
    };

    version = (const char*) dispatch->GetString(GL_VERSION);
    if (!version) return;

    for (i = 0;  prefixes[i];  i++) {
        const size_t length = strlen(prefixes[i]);
        if (strncmp(version, prefixes[i], length) == 0) {
            version += length;
            break;
        }
    }

/* PR #18 */
#ifdef _MSC_VER
    sscanf_s(version, "%d.%d", &major, &minor);
#else
    sscanf(version, "%d.%d", &major, &minor);
#endif

    features->GLVersion.major = major; features->GLVersion.minor = minor;
    features->maxLoadedGLVersion.major = major; features->maxLoadedGLVersion.minor = minor;
'''


class OpenGLCStructLoader(OpenGLCLoader):
    def write(self, fobj):
        if not self.disabled and 'gl' in self.apis:
            fobj.write(_OPENGL_LOADER)

    def write_begin_load(self, fobj):
        fobj.write('\tfeatures->GLVersion.major = 0; features->GLVersion.minor = 0;\n')
        fobj.write('\tdispatch->GetString = (PFNGLGETSTRINGPROC)load("glGetString");\n')
        fobj.write('\tif(dispatch->GetString == NULL) return 0;\n')
        fobj.write('\tif(dispatch->GetString(GL_VERSION) == NULL) return 0;\n')

    def write_end_load(self, fobj):
        fobj.write('\treturn features->GLVersion.major != 0 || features->GLVersion.minor != 0;\n')

    def write_find_core(self, fobj):
        fobj.write(_FIND_VERSION)

    def write_find_core_end(self, fobj):
        fobj.write(_FIND_VERSION)

    def write_has_ext(self, fobj):
        fobj.write(_OPENGL_HAS_EXT)

    def write_header(self, fobj):
        fobj.write(_OPENGL_HEADER_START)
        written = set()
        for api, hname, name in [
            ('gl', 'gl', 'OpenGL'), ('gles1', 'gl', 'OpenGL ES 1'),
            ('gles2', 'gl2', 'OpenGL ES 2'), ('gles2', 'gl3', 'OpenGL ES 3')
        ]:
            if api in self.apis and hname not in written:
                fobj.write(_OPENGL_HEADER_INCLUDE_ERROR.format(hname, name))
                written.add(hname)

        fobj.write(_OPENGL_HEADER)
        if not self.disabled and 'gl' in self.apis:
            fobj.write(_OPENGL_HEADER_LOADER)

    def write_header_end(self, fobj):
        fobj.write(_OPENGL_HEADER_END)
