# Windows GpuResources Replacement Plan

## Purpose

This memo defines the minimum Windows-only replacement boundary for the current
MediaPipe `GpuResources` path.

The goal is not to replace every historical GPU feature.

The goal is to replace just enough of this path:

- `GpuResources`
- `GlCalculatorHelper`
- Stage 2 preprocessing bring-up

## Why This Is The Next Step

The current blocker chain is now explicit:

1. Windows GPU hard-disable in `mediapipe/gpu/BUILD`
2. EGL/GLES header assumption in `gl_base.h`
3. `pthread` dependency in `gl_context`

The third blocker is the decisive one.

At this point, further progress requires a Windows-owned object that can stand
in for the narrow parts of `GpuResources` that `GlCalculatorHelper` actually
needs.

## Observed Minimum Contract

From the current local fork, the early helper path needs only a few things:

- a way to initialize GPU execution state
- a way to run code on the GL context
- a way to expose a GL context-like execution owner
- eventually, a buffer-pool boundary for texture-backed buffers

The early Stage 2 path does not require the full legacy `GpuResources` surface.

## Replacement Strategy

Use a Windows-only replacement object rather than porting the full current
`GpuResources` implementation.

Recommended shape:

- keep the existing name and types untouched for now
- introduce a Windows-owned alternate resource owner in the worker tree
- wire MediaPipe helper integration toward that object behind a Windows-only
  path

This keeps the blast radius smaller.

## Minimum Replacement Interface

The Windows replacement object should expose only:

- `Initialize()`
- `Shutdown()`
- `RunInGlContext(...)`
- `PrepareGpuNode(...)`
- `IsInitialized()`

Optional placeholders:

- `GetGpuBufferPool()`
- `GetSharedExecutionContext()`

These placeholders may initially return `Unimplemented`.

## What Must Stay Out

The replacement object must not absorb:

- graph construction logic
- task APIs
- worker protocol behavior
- model loading
- inference orchestration

If the object starts carrying those responsibilities, the boundary is wrong.

## Integration Sequence

Use this order.

1. define the Windows replacement type
2. make it own the existing adapter/shim
3. route a Windows-only helper path through it
4. re-run Stage 2
5. only then add buffer-pool behavior if Stage 2 proves it is required

## Immediate Goal

The first success condition is not full pose inference.

It is:

- `ImageCloneCalculator` and `ImageToTensorCalculator` initialize against a
  Windows-owned execution object without touching the old `pthread`-based
  `gl_context`

## Practical Conclusion

The next real implementation unit is a tiny Windows-owned
`GpuResources replacement` object that wraps the current adapter/shim and
becomes the future hook point for MediaPipe helper integration.
