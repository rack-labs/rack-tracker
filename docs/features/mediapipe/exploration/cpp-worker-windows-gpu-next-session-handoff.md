# C++ Worker Windows GPU Next Session Handoff

## 1. Current Goal

Bring up the redesigned Windows GPU-first C++ worker far enough to pass:

- Stage 1: Windows GL runtime smoke test
- Stage 2: `image -> GPU upload -> ImageToTensorCalculator`

The current session reached:

- Stage 1: passed
- Stage 2: build and runtime investigation completed, but not passed

2026-03-31 follow-up:

- Stage 2 build now fails later than the original `gl_context/pthread` barrier
- current first hard failure is `org_tensorflow` GL portability header include
  on `EGL/egl.h`

## 2. What Is Already Proven

### Stage 1 is real

A repo-owned Windows GL runtime exists and works.

Verified result:

- hidden-window GL bootstrap works
- GL worker thread model works
- make-current works
- minimal GL commands run
- shutdown works

Relevant files:

- [windows_gl_platform.h](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_platform.h)
- [windows_gl_platform.cc](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_platform.cc)
- [windows_gl_context_smoke_test.cc](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_context_smoke_test.cc)

## 3. What Stage 2 Proved

Stage 2 used a standalone smoke test binary:

- [windows_gl_image_to_tensor_smoke_test.cc](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_image_to_tensor_smoke_test.cc)

This binary builds a minimal graph around:

- `ImageCloneCalculator(output_on_gpu=true)`
- `ImageToTensorCalculator`

Confirmed results from this session:

1. Before any MediaPipe GPU policy patch:
   - runtime failed with `ImageCloneCalculator: GPU processing is disabled in build flags`
2. After patching `mediapipe/gpu/BUILD` to remove Windows hard-disable:
   - build failed on `EGL/egl.h` in `mediapipe/gpu/gl_base.h`
3. After adding a narrow Windows branch in `gl_base.h`:
   - build failed on `pthread.h` in `mediapipe/gpu/gl_context.h`

Meaning:

- the next real blocker is `gl_context`
- not task graphs
- not worker protocol
- not runtime orchestration

Confirmed result from the 2026-03-31 follow-up build:

4. With the exploratory MediaPipe GPU enable patches still in place:
   - build now fails in
     `external/org_tensorflow/tensorflow/lite/delegates/gpu/gl/gl_texture_helper.cc`
   - concrete error:
     `portable_gl31.h: fatal error C1083: 'EGL/egl.h': No such file or directory`

5. After applying a narrow Windows portability probe to
   `portable_gl31.h` / `portable_egl.h`:
   - the `EGL/egl.h` failure disappears
   - the next failure is still in `gl_texture_helper.cc`
   - new concrete errors are missing modern GL identifiers such as:
     - `GL_RGBA_INTEGER`
     - `GL_RGBA8UI`
     - `GL_RGBA16F`
     - `GL_RGBA32F`
     - `GL_HALF_FLOAT`

Meaning of the follow-up result:

- the build has moved past the original `mediapipe/gpu/gl_context` include wall
- the next exposed blocker is TFLite GL portability, not `pthread`
- Stage 2 still cannot exercise the repo-owned helper replacement path until
  the TFLite GL portability layer stops assuming EGL/GLES headers on Windows
- even after removing the EGL hard-include, Windows desktop `gl/GL.h` still
  does not provide the modern GL/GLES symbol set expected by TFLite GL

## 4. External Fork Changes Made This Session

These were applied directly to `mediapipe-forked` via local patch scripts:

- [`patch_gpu_build_windows_experimental.ps1`](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/patch_gpu_build_windows_experimental.ps1)
  - removes Windows from `mediapipe/gpu:disable_gpu`
  - removes Windows `target_compatible_with` incompatibility from `gl_context`
- [`patch_gl_base_windows_experimental.ps1`](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/patch_gl_base_windows_experimental.ps1)
  - adds a narrow `_WIN32` branch in `mediapipe/gpu/gl_base.h`
  - switches that branch to `Windows.h` + `gl/GL.h`

These patches were exploratory and are not the final design.

They were used to force the next blocker to surface.

## 5. Repo-Owned Design Direction Chosen

Do not port the existing `mediapipe/gpu:gl_context` whole.

Chosen direction:

- Windows-specific replacement adapter
- Windows-specific MediaPipe shim
- Windows-specific `GpuResources` replacement boundary
- Windows-only helper bridge

Reason:

- the current `gl_context` path is `pthread`-centric
- local fork has no Windows `WGL` implementation
- full port would turn into maintaining a private Windows fork of MediaPipe GPU

## 6. Repo Files Added For The Replacement Path

### Design docs

- [windows-gl-adapter-minimum-interface.md](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/docs/features/mediapipe/windows-gl-adapter-minimum-interface.md)
- [windows-gl-mediapipe-shim-plan.md](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/docs/features/mediapipe/windows-gl-mediapipe-shim-plan.md)
- [windows-gpu-resources-replacement-plan.md](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/docs/features/mediapipe/windows-gpu-resources-replacement-plan.md)
- [windows-gl-helper-wiring-patch-plan.md](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/docs/features/mediapipe/windows-gl-helper-wiring-patch-plan.md)
- [windows-gl-stage2-image-to-tensor-result.md](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/docs/features/mediapipe/windows-gl-stage2-image-to-tensor-result.md)

### Code skeletons

- [windows_gl_adapter.h](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_adapter.h)
- [windows_gl_adapter.cc](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_adapter.cc)
- [windows_gl_mediapipe_shim.h](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_mediapipe_shim.h)
- [windows_gl_mediapipe_shim.cc](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_mediapipe_shim.cc)
- [windows_gpu_resources_replacement.h](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gpu_resources_replacement.h)
- [windows_gpu_resources_replacement.cc](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gpu_resources_replacement.cc)
- [windows_gl_helper_bridge.h](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_helper_bridge.h)
- [windows_gl_helper_bridge.cc](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_helper_bridge.cc)

## 7. Important Constraint For Next Session

Do not spend the next session patching random task-layer files.

The next correct patch surface is narrow:

- `mediapipe/gpu/gl_calculator_helper.h`
- `mediapipe/gpu/gl_calculator_helper.cc`
- possibly `mediapipe/gpu/gpu_shared_data_internal.h`
- possibly `mediapipe/gpu/gpu_shared_data_internal.cc`

The immediate goal is to create a Windows-only alternate helper path that does
not touch the old `pthread` `gl_context` path.

Follow-up qualification:

- that remains the correct MediaPipe-side direction
- but Stage 2 build pressure currently reaches a TFLite GL portability blocker
  before helper wiring can be validated end-to-end

## 8. First Patch To Attempt Next Session

Start with `GlCalculatorHelper`, not `GpuService` global replacement.

Target behavior:

- on Windows experimental path, helper initialization should route through the
  repo-owned bridge:
  - `WindowsGlHelperBridge`
  - `WindowsGpuResourcesReplacement`
  - `WindowsGlMediapipeShim`
  - `WindowsGlAdapter`

What to change first:

1. patch `gl_calculator_helper.cc`
2. add a Windows-only alternate path inside:
   - `Open()`
   - `RunInGlContext(...)`
3. do not try to solve full `gpu_buffer_pool()` integration in the same patch

Desired outcome:

- Stage 2 failure moves past `pthread/gl_context`
- new failure, if any, should be later and more informative

2026-03-31 update:

- that outcome has effectively already happened for the current exploratory
  build state
- the newly exposed failure is `portable_gl31.h -> EGL/egl.h`
- so the shortest next exploratory patch is now the TFLite GL portability
  boundary, then helper wiring

## 9. Expected Next Blockers

After helper wiring, the next likely blocker is one of:

- missing Windows GPU buffer pool bridge
- missing texture-view interop
- missing `GlContext`-shaped compatibility method expected by helper code
- desktop GL vs GLES compatibility assumptions in converter code

Those are acceptable next blockers.

They are better than failing in `pthread.h`.

New earlier blocker now observed before those:

- TensorFlow Lite GL portability assumes EGL/GLES headers on Windows
- likely first patch files:
  - `tensorflow/lite/delegates/gpu/gl/portable_gl31.h`
  - `tensorflow/lite/delegates/gpu/gl/portable_egl.h`
- after that patch, the next blocker is a missing modern GL enum/function
  surface, not helper wiring yet

Only after that should the next blocker return to helper wiring, texture interop,
or buffer-pool integration.

## 10. Useful Commands

### Rebuild Stage 1

```powershell
& 'C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\build-windows-gl-smoke-test.ps1' -TargetName 'windows_gl_context_smoke_test'
```

### Rebuild Stage 2

```powershell
& 'C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\build-windows-gl-smoke-test.ps1' -TargetName 'windows_gl_image_to_tensor_smoke_test'
```

### Reapply external fork exploratory patches if needed

```powershell
& 'C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\patch_gpu_build_windows_experimental.ps1'
& 'C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\patch_gl_base_windows_experimental.ps1'
```

### Apply the next exploratory TFLite GL portability patch

```powershell
& 'C:\Users\neighbor\Documents\Code\Github\rack-tracker-forked\poseLandmarker_Python\cpp_worker\patch_tflite_portable_gl_windows_experimental.ps1'
```

### Rebuild after the portability probe

Expected current failure:

- `gl_texture_helper.cc` missing modern GL identifiers like `GL_RGBA8UI`
  because Windows SDK `gl/GL.h` is too old for the TFLite GL path

## 11. Success Condition For The Next Session

Do not define success as "build the full worker".

Define success as:

- `GlCalculatorHelper` no longer hard-depends on the old Windows-blocked
  `gl_context` path for the Stage 2 bring-up route

If that happens, the session is moving in the correct direction.

2026-03-31 status note:

- the current exploratory build appears to satisfy that success condition at the
  compile-frontier level
- the next success condition is narrower:
  `org_tensorflow` GL portability no longer hard-fails on `EGL/egl.h`
