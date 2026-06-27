@echo off
echo Building render.simd.simd_math with AVX2+FMA3...
python setup.py build_ext --inplace
if %ERRORLEVEL% EQU 0 (
    echo Build successful.
) else (
    echo Build failed. Trying with /O2 only...
    python setup.py build_ext --inplace --compiler=msvc
)
