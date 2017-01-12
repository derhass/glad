_API_NAMES = {
    'egl': 'EGL',
    'gl': 'OpenGL',
    'gles1': 'OpenGL ES',
    'gles2': 'OpenGL ES',
    'glx': 'GLX',
    'wgl': 'WGL',
}


def api_name(api):
    api = api.lower()
    return _API_NAMES[api]

def calc_alias_dict(funclist):
    # keep a dictionary, store the set of aliases known for each function
    # initialize it to identity, each function aliases itself
    alias=dict([func.proto.name,set([func.proto.name])] for func in funclist)
    # now, add all further aliases
    for func in funclist:
        if func.alias is not None:
            # aliasses is the set of all aliasses known for this function
            aliasses = alias[func.proto.name]
            aliasses.add(func.alias)
            # unify all alias sets of all aliased functions
            new_aliasses=set()
            missing_funcs=set()
            for aliased_func in aliasses:
                try:
                    new_aliasses.update(alias[aliased_func])
                except KeyError:
                    #print '{} aliases missing function {}'.format(func.proto.name, aliased_func)
                    missing_funcs.add(aliased_func)
            # remove all missing functions
            new_aliasses = new_aliasses - missing_funcs
            # add the alias set to all aliased functions
            for func in new_aliasses:
                alias[func]=new_aliasses
    # clean up the alias dict: remove entries where the set contains only one element
    for func in funclist:
        if len(alias[func.proto.name]) < 2:
            del alias[func.proto.name]
    return alias

