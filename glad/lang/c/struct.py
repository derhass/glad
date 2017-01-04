from glad.lang.c.generator import CGenerator

class CStructGenerator(CGenerator):
    NAME = 'c-struct'
    NAME_LONG = 'C/C++ Struct'

    def generate_parts(self, types, features, extensions, enums, functions, fs, es):
        self.generate_header()
        self.generate_types(types)
        write = set()
        self.generate_features_phase1(write, features)
        self.generate_extensions_phase1(write, extensions, enums, functions)

	# sort functions alphabetically (?!)
	funclist=sorted(write)

        f = self._f_h
	# header: define the struct
        f.write('struct GLADDispatchTable_s {\n')
        for func in funclist:
            self.write_function_pointer_decl(f, func)
        f.write('};\n')

        f = self._f_c
	# C code: define the function pointers
        for func in funclist:
            self.write_function(f, func)

	# generate the loader code
        self.generate_loader(fs, es)

    # re-purposed to write only the function pointer type declaration
    def write_function_prototype(self, fobj, func):
        fobj.write('typedef {} (APIENTRYP PFN{}PROC)({});\n'.format(
            func.proto.ret.to_c(), func.proto.name.upper(),
            ', '.join(param.type.raw for param in func.params))
        )

    def write_function_pointer_decl(self, fobj, func):
        fobj.write('\tPFN{}PROC {};\n'.format(func.proto.name.upper(),
                                              func.proto.name[2:]))

    def write_api_header(self, f):
        for api in self.api:
            if api == 'glx':
                f.write('GLAPI int gladLoad{}Loader(GLADDispatchTable *dispatch, GLADloadproc, Display *dpy, int screen);\n\n'.format(api.upper()))
            elif api == 'wgl':
                f.write('GLAPI int gladLoad{}Loader(GLADDispatchTable *dispatch, GLADloadproc, HDC hdc);\n\n'.format(api.upper()))
            else:
                f.write('GLAPI int gladLoad{}Loader(GLADDispatchTable *dispatch, GLADloadproc);\n\n'.format(api.upper()))

    def generate_loader(self, features, extensions):
        f = self._f_c

        if self.spec.NAME in ('egl', 'wgl'):
            features = {'egl': [], 'wgl': []}

        written = set()
        for api, version in self.api.items():
            for feature in features[api]:
                f.write('static void load_{}(GLADDispatchTable *dispatch, GLADloadproc load) {{\n'
                        .format(feature.name))
                if self.spec.NAME in ('gl', 'glx', 'wgl'):
                    f.write('\tif(!GLAD_{}) return;\n'.format(feature.name))
                for func in feature.functions:
                    f.write('\tdispatch->{0} = (PFN{1}PROC)load("{2}");\n'
                            .format(func.proto.name[2:], func.proto.name.upper(),func.proto.name))
                f.write('}\n')

            for ext in extensions[api]:
                if len(list(ext.functions)) == 0 or ext.name in written:
                    continue

                f.write('static void load_{}(GLADDispatchTable *dispatch, GLADloadproc load) {{\n'
                        .format(ext.name))
                if self.spec.NAME in ('gl', 'glx', 'wgl'):
                    f.write('\tif(!GLAD_{}) return;\n'.format(ext.name))
                if ext.name == 'GLX_SGIX_video_source': f.write('#ifdef _VL_H_\n')
                if ext.name == 'GLX_SGIX_dmbuffer': f.write('#ifdef _DM_BUFFER_H_\n')
                for func in ext.functions:
                    # even if they were in written we need to load it
                    f.write('\tdispatch->{0} = (PFN{1}PROC)load("{2}");\n'
                            .format(func.proto.name[2:], func.proto.name.upper(), func.proto.name))
                if ext.name in ('GLX_SGIX_video_source', 'GLX_SGIX_dmbuffer'):
                    f.write('#else\n')
                    f.write('\t(void)load;\n')
                    f.write('#endif\n')
                f.write('}\n')

                written.add(ext.name)

            f.write('static int find_extensions{}(GLADDispatchTable *dispatch) {{\n'.format(api.upper()))
            if self.spec.NAME in ('gl', 'glx', 'wgl'):
                f.write('\tif (!get_exts(dispatch)) return 0;\n')
                for ext in extensions[api]:
                    f.write('\tGLAD_{0} = has_ext("{0}");\n'.format(ext.name))
                f.write('\tfree_exts();\n')
            f.write('\treturn 1;\n')
            f.write('}\n\n')

            if api == 'glx':
                f.write('static void find_core{}(const GLADDispatchTable *dispatch, Display *dpy, int screen) {{\n'.format(api.upper()))
            elif api == 'wgl':
                f.write('static void find_core{}(const GLADDispatchTable *dispatch, HDC hdc) {{\n'.format(api.upper()))
            else:
                f.write('static void find_core{}(const GLADDispatchTable *dispatch) {{\n'.format(api.upper()))

            self.loader.write_find_core(f)
            if self.spec.NAME in ('gl', 'glx', 'wgl'):
                for feature in features[api]:
                    f.write('\tGLAD_{} = (major == {num[0]} && minor >= {num[1]}) ||'
                            ' major > {num[0]};\n'.format(feature.name, num=feature.number))
            if self.spec.NAME == 'gl':
                f.write('\tif (GLVersion.major > {0} || (GLVersion.major >= {0} && GLVersion.minor >= {1})) {{\n'.format(version[0], version[1]))
                f.write('\t\tmax_loaded_major = {0};\n'.format(version[0]))
                f.write('\t\tmax_loaded_minor = {0};\n'.format(version[1]))
                f.write('\t}\n')
            f.write('}\n\n')

            if api == 'glx':
                f.write('int gladLoad{}Loader(GLADDispatchTable *dispatch, GLADloadproc load, Display *dpy, int screen) {{\n'.format(api.upper()))
            elif api == 'wgl':
                f.write('int gladLoad{}Loader(GLADDispatchTable *dispatch, GLADloadproc load, HDC hdc) {{\n'.format(api.upper()))
            else:
                f.write('int gladLoad{}Loader(GLADDispatchTable *dispatch, GLADloadproc load) {{\n'.format(api.upper()))

            self.loader.write_begin_load(f)

            if api == 'glx':
                f.write('\tfind_core{}(dispatch, dpy, screen);\n'.format(api.upper()))
            elif api == 'wgl':
                f.write('\tfind_core{}(dispatch. hdc);\n'.format(api.upper()))
            else:
                f.write('\tfind_core{}(dispatch);\n'.format(api.upper()))

            for feature in features[api]:
                f.write('\tload_{}(dispatch, load);\n'.format(feature.name))
            f.write('\n\tif (!find_extensions{}(dispatch)) return 0;\n'.format(api.upper()))
            for ext in extensions[api]:
                if len(list(ext.functions)) == 0:
                    continue
                f.write('\tload_{}(dispatch, load);\n'.format(ext.name))

            self.loader.write_end_load(f)
            f.write('}\n\n')

        self.loader.write_header_end(self._f_h)

