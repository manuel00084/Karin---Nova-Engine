from setuptools import setup, Extension
import numpy as np
import sys

extra_compile_args = ["/O2", "/arch:AVX2", "/fp:fast"]
if sys.platform == "win32":
    extra_compile_args = ["/O2", "/arch:AVX2", "/fp:fast", "/D__AVX2__=1"]

simd_math = Extension(
    "render.simd.simd_math",
    sources=["render/simd/simd_math.c"],
    include_dirs=[np.get_include()],
    extra_compile_args=extra_compile_args,
    define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
)

setup(
    name="render-simd",
    version="1.0.0",
    description="SIMD math for Karin VTuber renderer",
    ext_modules=[simd_math],
    package_dir={"": "."},
)
