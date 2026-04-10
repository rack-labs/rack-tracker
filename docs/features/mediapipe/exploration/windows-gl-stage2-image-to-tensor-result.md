# Windows GL Stage 2 Image-To-Tensor Result

## Summary

Stage 2 build succeeded, but Stage 2 runtime did not.

The standalone MediaPipe preprocessing smoke test binary builds on Windows:

- `//poseLandmarker_Python/cpp_worker/platform/windows_gl:windows_gl_image_to_tensor_smoke_test`

But at runtime the graph fails during `ImageCloneCalculator` initialization
with:

- `ImageCloneCalculator: GPU processing is disabled in build flags`

## What Passed

- repo-owned Windows GL platform layer initializes
- Stage 2 smoke test binary compiles and links inside the local
  `mediapipe-forked` workspace
- `ImageCloneCalculator` and `ImageToTensorCalculator` can be linked into the
  same binary target on Windows

## What Failed

The graph fails before any real GPU preprocessing work starts.

Observed runtime result:

- `platform_initialize: ok`
- `graph_initialize: fail`
- `ValidatedGraphConfig Initialization failed`
- `ImageCloneCalculator: GPU processing is disabled in build flags`

## Root Cause

The current local `mediapipe/gpu/BUILD` still treats Windows as
`disable_gpu`.

Relevant local behavior:

- `selects.config_setting_group(name = "disable_gpu", ...)`
- that group explicitly matches `@platforms//os:windows`
- calculators like `ImageCloneCalculator` use `MEDIAPIPE_DISABLE_GPU` guarded
  paths and reject `output_on_gpu: true` when GPU is disabled

So Stage 2 is currently blocked before the graph can test:

- CPU image to GPU upload
- GL-backed image preprocessing
- `image_to_tensor` on the intended Windows GPU path

## Practical Meaning

This is an important result.

It means:

- Stage 1 proved the repo can own a Windows GL runtime
- Stage 2 proved the current local MediaPipe graph layer still refuses Windows
  GPU usage at the build-policy/runtime-contract level

So the next blocker is no longer hypothetical.

It is now concrete:

- Windows must stop matching the current `disable_gpu` path for the relevant
  MediaPipe GPU stack
- and the repo must still provide a real Windows GL backend/context model for
  the helpers that were previously disabled

## Next Design Gate

Before Stage 2 can pass, the repo must decide one of these:

1. Patch the local MediaPipe GPU build policy so Windows no longer maps to
   `disable_gpu`, then port the missing GL support needed by the calculators.
2. Keep Windows disabled in the shared MediaPipe GPU layer and build a more
   isolated worker-owned GPU preprocessing path that does not rely on the
   current disabled calculator contract.

Given the current redesign direction, option 1 is the more direct path.

## Recommendation

Do not move to Stage 3 inference yet.

The correct next step is:

- a narrow patch/design pass on `mediapipe/gpu/BUILD` and the Windows GL helper
  ownership boundary so Stage 2 can initialize a GPU graph honestly on Windows
