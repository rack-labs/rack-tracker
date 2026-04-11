# Windows GL Stage 2 Follow-up - 2026-03-31

## Result

Rebuilding Stage 2 on 2026-03-31 showed that the current failure is now
later than the original `mediapipe/gpu/gl_context` barrier.

Observed failing source:

- `external/org_tensorflow/tensorflow/lite/delegates/gpu/gl/gl_texture_helper.cc`

Observed compiler error:

- `portable_gl31.h(21): fatal error C1083: cannot open include file: 'EGL/egl.h': No such file or directory`

## Meaning

This is important because it changes the interpretation of the next blocker.

The current build no longer stops first on:

- `mediapipe/gpu/gl_context.h`
- `pthread.h`

It now stops inside the TensorFlow Lite GL portability layer that is pulled in
by MediaPipe's OpenGL image-to-tensor path.

That means:

1. the earlier exploratory `mediapipe/gpu/BUILD` and `gl_base.h` patches did
   move the failure frontier forward
2. the next blocker is not only MediaPipe helper wiring
3. the Stage 2 OpenGL preprocessing route still assumes an EGL/GLES portability
   layer inside TFLite GL

## Immediate Conclusion

Before the repo-owned Windows helper replacement can be meaningfully exercised
by Stage 2, the build must first get through the TFLite GL portability headers.

The narrowest next exploratory patch is:

- `tensorflow/lite/delegates/gpu/gl/portable_gl31.h`
- possibly `tensorflow/lite/delegates/gpu/gl/portable_egl.h`

Goal of that patch:

- replace hard EGL/GLES header assumptions with a Windows desktop GL probe path
- force the next concrete missing symbol or runtime assumption to surface

This is still exploratory, not a final architecture decision.

## What Happened After The Portability Probe

After applying
`poseLandmarker_Python/cpp_worker/patch_tflite_portable_gl_windows_experimental.ps1`
and rebuilding Stage 2, the `EGL/egl.h` include failure was replaced by a new,
more specific compile blocker in the same target:

- `external/org_tensorflow/tensorflow/lite/delegates/gpu/gl/gl_texture_helper.cc`

Observed missing identifiers include:

- `GL_RGBA_INTEGER`
- `GL_RGBA8UI`
- `GL_RGBA8_SNORM`
- `GL_RGBA8I`
- `GL_RGBA16UI`
- `GL_RGBA32UI`
- `GL_RGBA16I`
- `GL_RGBA32I`
- `GL_RGBA16F`
- `GL_RGBA32F`
- `GL_HALF_FLOAT`

Interpretation:

- the hard EGL header assumption is no longer the first blocker
- Windows SDK `gl/GL.h` only exposes old desktop OpenGL declarations
- the TFLite GL path expects a much newer GLES/OpenGL symbol surface

So the next blocker is no longer "find EGL headers".

It is:

- provide a real Windows-compatible GL extension header and loader strategy for
  the TFLite GL path
- or stop using the TFLite GL path for this Windows bring-up route

That is a materially different scope signal than the original `EGL/egl.h`
error.

## Recommended Next Step

Apply the repo-owned script:

- `poseLandmarker_Python/cpp_worker/patch_tflite_portable_gl_windows_experimental.ps1`

Then rebuild:

```powershell
& 'C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\build-windows-gl-smoke-test.ps1' -TargetName 'windows_gl_image_to_tensor_smoke_test'
```

Success is not "build passes".

Success is:

- the failure moves past hard `EGL/egl.h` include assumptions
- the next blocker becomes a more specific missing GL symbol, missing TFLite GL
  portability function, or a later MediaPipe helper/runtime integration error

## Follow-up Activities (2026-03-31 to 04-01)

After the portability probe, work continued through the Windows-specific helper
tree to align `gl_texture` path to the Windows driver. Additional actions:

- Added `poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_pthread_shim.h`
  and `patch_windows_gl_context_pthread_shim_experimental.ps1` so `mediapipe/gpu/gl_context.h`
  includes a shim instead of `pthread.h` on Windows.
- Introduced `poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_compat.h`
  and related scripts to define modern GL enums/loader helpers (`GL_R8`, `GL_RG16F`, etc.).
- Began defining WGL `PlatformGlContext` plus a new `windows_gl_stage2_symbol_probe`
  target to confirm the runtime exposes desktop GL functions; the last build still fails
  after the portability layer and the patched `mediapipe/calculators/tensor/BUILD`
  routes `image_to_tensor_calculator_gpu_deps` through `:image_to_tensor_converter_gl_texture`.

## Current Blocker Snapshot

- A full smoke build now reaches `mediapipe/gpu/gl_context.h` again; the same file
  needs a Windows branch that wires the WGL `context_`/`ContextBinding` fields plus
  associated `platform_gl.h` helpers so downstream helpers (`gpu_shared_data_internal`,
  `gl_calculator_helper`, `gpu_buffer_multi_pool`, `image_to_tensor_utils`) compile.
- The Windows-specific copies of `mediapipe/calculators/tensor/BUILD` and related scripts
  must keep the new GL texture converter dependency only in the `selects.with_or` block
  (no stray `copts` entry), otherwise Bazel treats the selector output as a compiler flag
  and downstream targets issue syntax errors.

## Next Hand-off Steps

1. Finish the Windows `HAS_WGL` body in `mediapipe/gpu/gl_context.h` (context storage,
   sync-token binding, `PlatformGlContext` accessor) and expose the Windows shim
   so `MediaPipe::GlContext` can be constructed without `pthread`.
2. Confirm `poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_stage2_symbol_probe`
   continues to find the same modern GL symbols (GL shader/texture/buffer APIs) at runtime.
3. Re-run `build-windows-gl-smoke-test.ps1 -TargetName windows_gl_image_to_tensor_smoke_test`
   once the `gl_context` changes are available in Bazel so that the compile frontier
   moves past `gl_context.h` and we only need to resolve any remaining GL enum definitions.
