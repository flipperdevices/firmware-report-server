

def time_it(func):
    """decorator to time a function"""

    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f"Function {func.__name__}{args} {kwargs} Took {total_time:.4f} seconds")
        return result

    return timeit_wrapper


def cache_it():
    """decorator to cache a function result"""
    d = {}

    def decorator(func):
        def new_func(param):
            if param not in d:
                d[param] = func(param)
            return d[param]

        return new_func

    return decorator


def minify_path(path: str):
    """Minify path to be more readable"""
    if "arm-none-eabi/" in path:
        return path.rsplit("arm-none-eabi/", 1)[1]
    else:
        return path.replace("build/f7-firmware-D/", "")


def flipper_path(lib, obj_name):
    """Make a readable path given that we have libraries"""
    lib = minify_path(lib)
    obj_name = minify_path(obj_name)
    if lib:
        lib = lib.rsplit(".a", 1)[0]
        lib = lib.rsplit("/lib", 1)
        lib = "/".join(lib)
        path = f"{lib}/{obj_name}"
    else:
        path = f"{obj_name}"
    return path

