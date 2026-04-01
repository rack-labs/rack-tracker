# Windows GL Helper Wiring Patch Plan

## Purpose

This memo defines the first real wiring plan for replacing the old
`GpuResources -> GlContext` path on Windows with the repo-owned
`adapter -> shim -> replacement` path.

The goal is not to rewire all MediaPipe GPU code.

The goal is to rewire just enough for Stage 2 bring-up.

## Confirmed Wiring Points

From the current local fork, the early helper path depends on these calls:

- `GlCalculatorHelper::Open()`
- `GpuResources::gl_context(...)`
- `GlCalculatorHelper::RunInGlContext(...)`
- `GpuResources::gpu_buffer_pool()`
- `GpuResources::PrepareGpuNode(...)`

This means the first wiring patch should focus on:

1. execution-context replacement
2. node-preparation replacement
3. explicit handling of the still-missing buffer-pool bridge

## Recommended Wiring Strategy

Do not replace `kGpuService` globally first.

Instead:

- add a Windows-only alternate execution path
- keep the non-Windows path untouched
- make the alternate path explicit and narrow

## Patch Surface

### Primary patch candidates

- `mediapipe/gpu/gl_calculator_helper.h`
- `mediapipe/gpu/gl_calculator_helper.cc`
- `mediapipe/gpu/gpu_shared_data_internal.h`
- `mediapipe/gpu/gpu_shared_data_internal.cc`

### Worker-owned bridge package

- `poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gpu_resources_replacement.*`
- `poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_mediapipe_shim.*`
- `poseLandmarker_Python/cpp_worker/platform/windows_gl/windows_gl_adapter.*`

## First Wiring Objective

The first wiring patch should let Windows do this:

- initialize a Windows-owned execution object
- route `RunInGlContext(...)` through that object
- route `PrepareGpuNode(...)` through that object

The first wiring patch does not need to solve full pooled texture interop yet.

## Minimum Alternate Path

The Windows-only helper path should conceptually look like this:

- `GlCalculatorHelper::Open()`
- detect Windows experimental path
- obtain Windows-owned replacement object
- use replacement object for:
  - initialization
  - node preparation
  - GL execution

If the replacement object is unavailable, fail clearly.

## Buffer Pool Policy

Buffer pool integration is the one place where scope can easily explode.

So the first patch must keep the rule explicit:

- if Stage 2 can initialize and run until it truly needs pooled GPU storage,
  stop there first
- only add buffer-pool bridge behavior when the next blocker proves it is
  necessary

This avoids rebuilding all of `GpuBufferMultiPool` prematurely.

## First Failure We Want

The first successful wiring patch is not one that finishes inference.

It is one that changes the failure mode from:

- compile failure in `pthread/gl_context`

to something later and more informative, ideally:

- missing Windows GPU buffer pool bridge
- missing texture-view interop
- missing helper-specific compatibility function

That would mean the replacement path is actually in control.

## Suggested Step Order

1. add a Windows-only bridge header in the worker package
2. patch `GlCalculatorHelper` to call the bridge on Windows experimental path
3. patch `PrepareGpuNode` to delegate to the replacement object on the same
   path
4. leave buffer-pool methods as explicit `Unimplemented` until needed
5. rebuild Stage 2 and observe the next blocker

## Practical Conclusion

The next implementation patch should target `GlCalculatorHelper` first, not the
entire GPU service stack.

That is the shortest path to getting the replacement wiring under real build
pressure.
