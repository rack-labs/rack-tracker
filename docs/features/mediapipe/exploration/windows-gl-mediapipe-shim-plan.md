# Windows GL MediaPipe Shim Plan

## Purpose

This memo defines the smallest compatibility shim between the repo-owned
Windows GL adapter and the MediaPipe GPU helper path.

The goal is not to re-create all of `gl_context`.

The goal is to satisfy the minimum call path needed by Stage 2:

- `GpuResources`
- `GlCalculatorHelper`
- `ImageCloneCalculator`
- `ImageToTensorCalculator`

## Observed Dependency Shape

From the current local fork:

- `GlCalculatorHelper` needs `GpuResources`
- `GpuResources` exposes `gl_context()`
- `GlCalculatorHelper::RunInGlContext()` delegates to `gl_context()->Run(...)`
- `GlCalculatorHelper` also depends on `gpu_buffer_pool()`

This means the first shim target is not "all GPU helpers".

It is:

- a Windows adapter-backed execution context
- a minimal `GpuResources`-like owner
- enough pool/context exposure for early GPU upload and preprocessing

## Minimum Shim Boundary

The shim should own only:

- adapter initialization
- adapter-backed synchronous GL execution
- a minimal resource owner object for Stage 2
- the future hook point for a real GPU buffer pool bridge

The shim should not own:

- graph services policy
- full `GlContext` API parity
- task graph behavior
- inference behavior

## First Interface

The first compatibility shim should expose:

- `Initialize()`
- `Shutdown()`
- `RunInGlContext(std::function<absl::Status()>)`
- `IsInitialized()`
- a future placeholder for `GpuBufferPool` integration

## Implementation Rule

Stage 2 does not need the full historical `GpuResources` shape on day one.

It needs:

- an adapter-backed execution object
- an object boundary where `GpuResources` replacement can grow later

So the first shim may deliberately return `Unimplemented` for pool-facing
behavior that is not yet wired.

That is acceptable as long as:

- the ownership boundary is correct
- the missing pieces are explicit

## Next Concrete Step

After this shim skeleton exists, the next real work item is:

- decide whether to replace `GpuResources` directly
- or add a Windows-only alternate code path that lets
  `GlCalculatorHelper` use the shim-backed execution object

The repo should prefer the smaller change set that gets Stage 2 to initialize
honestly without reviving the old `gl_context` port path.
