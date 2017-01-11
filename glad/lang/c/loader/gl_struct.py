from glad.lang.c.loader.gl import OpenGLCLoader
from glad.lang.c.loader import LOAD_OPENGL_DLL_H, LOAD_OPENGL_GLAPI_H

LOAD_OPENGL_DLL = '''
%(pre)s void* %(proc)s(const char *namez, void *arg);

#ifdef _WIN32
#include <windows.h>

typedef void* (APIENTRYP PFNWGLGETPROCADDRESSPROC_PRIVATE)(const char*);

typedef struct {
	HMODULE libGL;
	PFNWGLGETPROCADDRESSPROC_PRIVATE gladGetProcAddressPtr;
} GLADGLLibrary;

%(pre)s
int %(init)s(GLADGLLibrary *gl) {
    gl->libGL = LoadLibraryW(L"opengl32.dll");
    if(gl->libGL != NULL) {
        gl->gladGetProcAddressPtr = (PFNWGLGETPROCADDRESSPROC_PRIVATE)GetProcAddress(
                gl->libGL, "wglGetProcAddress");
        return gl->gladGetProcAddressPtr != NULL;
    }

    return 0;
}

%(pre)s
void %(terminate)s(GLADGLLibrary *gl) {
    if(gl->libGL != NULL) {
        FreeLibrary(gl->libGL);
        gl->libGL = NULL;
    }
}
#else
#include <dlfcn.h>

typedef void* (APIENTRYP PFNGLXGETPROCADDRESSPROC_PRIVATE)(const char*);

typedef struct {
	void* libGL;
#ifndef __APPLE__
	PFNGLXGETPROCADDRESSPROC_PRIVATE gladGetProcAddressPtr;
#endif
} GLADGLLibrary;

%(pre)s
int %(init)s(GLADGLLibrary *gl) {
#ifdef __APPLE__
    static const char *NAMES[] = {
        "../Frameworks/OpenGL.framework/OpenGL",
        "/Library/Frameworks/OpenGL.framework/OpenGL",
        "/System/Library/Frameworks/OpenGL.framework/OpenGL",
        "/System/Library/Frameworks/OpenGL.framework/Versions/Current/OpenGL"
    };
#else
    static const char *NAMES[] = {"libGL.so.1", "libGL.so"};
#endif

    unsigned int index = 0;
    for(index = 0; index < (sizeof(NAMES) / sizeof(NAMES[0])); index++) {
        gl->libGL = dlopen(NAMES[index], RTLD_NOW | RTLD_GLOBAL);

        if(gl->libGL != NULL) {
#ifdef __APPLE__
            return 1;
#else
            gl->gladGetProcAddressPtr = (PFNGLXGETPROCADDRESSPROC_PRIVATE)dlsym(gl->libGL,
                "glXGetProcAddressARB");
            return gl->gladGetProcAddressPtr != NULL;
#endif
        }
    }

    return 0;
}

%(pre)s
void %(terminate)s(GLADGLLibrary *gl) {
    if(gl->libGL != NULL) {
        dlclose(gl->libGL);
        gl->libGL = NULL;
    }
}
#endif

%(pre)s
void* %(proc)s(const char *namez, void *v_gl) {
    GLADGLLibrary *gl=(GLADGLLibrary*)v_gl;
    void* result = NULL;
    if(gl->libGL == NULL) return NULL;

#ifndef __APPLE__
    if(gl->gladGetProcAddressPtr != NULL) {
        result = gl->gladGetProcAddressPtr(namez);
    }
#endif
    if(result == NULL) {
#ifdef _WIN32
        result = (void*)GetProcAddress(gl->libGL, namez);
#else
        result = dlsym(gl->libGL, namez);
#endif
    }

    return result;
}

static void* load_proc_wrapper(const char *name, void *arg)
{
	return ((GLADloadproc)arg)(name);
}
'''

_OPENGL_LOADER = \
    LOAD_OPENGL_DLL % {'pre':'static', 'init':'open_gl',
                       'proc':'get_proc', 'terminate':'close_gl'} + '''
int gladLoadGL(GLADFeatures *features, GLADDispatchTable *dispatch) {
    int status = 0;
    GLADGLLibrary gl;

    if(open_gl(&gl)) {
        status = gladLoadGLLoaderEXT(features, dispatch, get_proc, &gl);
    }
    close_gl(&gl);

    return status;
}
'''

_OPENGL_HAS_EXT = '''
#if defined(GL_ES_VERSION_3_0) || defined(GL_VERSION_3_0)
#define _GLAD_IS_SOME_NEW_VERSION 1
#endif

typedef struct {
	const char *exts;
	int num_exts_i;
	const char **exts_i;
} GLADExtensionContext;

static void
gladExtensionContextInit(GLADExtensionContext *ctx)
{
	ctx->exts=NULL;
	ctx->num_exts_i=0;
	ctx->exts_i=NULL;
}

static int get_exts(GLADExtensionContext *ctx, const GLADFeatures *features, const GLADDispatchTable *dispatch) {
#ifdef _GLAD_IS_SOME_NEW_VERSION
    if(features->maxLoadedGLVersion.major < 3) {
#endif
        ctx->exts = (const char *)dispatch->GetString(GL_EXTENSIONS);
#ifdef _GLAD_IS_SOME_NEW_VERSION
    } else {
        int index;

        ctx->num_exts_i = 0;
        dispatch->GetIntegerv(GL_NUM_EXTENSIONS, &ctx->num_exts_i);
        if (ctx->num_exts_i > 0) {
            ctx->exts_i = (const char **)realloc((void *)ctx->exts_i, ctx->num_exts_i * sizeof(*ctx->exts_i) );
        }

        if (ctx->exts_i == NULL) {
            return 0;
        }

        for(index = 0; index < ctx->num_exts_i; index++) {
            ctx->exts_i[index] = (const char*)dispatch->GetStringi(GL_EXTENSIONS, index);
        }
    }
#endif
    return 1;
}

static void free_exts(GLADExtensionContext *ctx) {
    if (ctx->exts_i != NULL) {
        free((char **)ctx->exts_i);
        ctx->exts_i = NULL;
    }
    ctx->num_exts_i=0;
    ctx->exts=NULL;
}

static int has_ext(const GLADExtensionContext *ctx, const GLADFeatures *features, const char *ext) {
#ifdef _GLAD_IS_SOME_NEW_VERSION
    if(features->maxLoadedGLVersion.major < 3) {
#endif
        const char *extensions;
        const char *loc;
        const char *terminator;
        extensions = ctx->exts;
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

        for(index = 0; index < ctx->num_exts_i; index++) {
            const char *e = ctx->exts_i[index];

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
typedef void* (* GLADloadprocwitharg)(const char *name, void *);
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
        fobj.write('\tGLADExtensionContext ctx;\n')
        fobj.write('\tgladExtensionContextInit(&ctx);\n')
        fobj.write('\tfeatures->GLVersion.major = 0; features->GLVersion.minor = 0;\n')
        fobj.write('\tfeatures->GLVersion.major = 0; features->GLVersion.minor = 0;\n')
        fobj.write('\tdispatch->GetString = (PFNGLGETSTRINGPROC)load("glGetString", arg);\n')
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
