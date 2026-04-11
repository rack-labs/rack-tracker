# MediaPipe C++ Worker Windows GL Platform Layer Design

## 1. Purpose

This memo defines the narrowest acceptable ownership boundary for a
repo-owned `Windows GL platform layer` for the GPU-first C++ worker redesign.

It answers four questions:

1. What problem this layer actually solves
2. What this layer must own
3. What this layer must not own
4. What the first GPU viability smoke tests must prove

This document does not claim that GPU runtime is already working. It defines
the minimum platform work needed before that claim can be tested honestly.

## 2. Decision

The repo may own a new `Windows GL platform layer` as a bounded prerequisite
for the OpenGL/GL-based MediaPipe GPU worker.

This is acceptable only if the layer stays narrow:

- platform bootstrap only
- GL context lifecycle only
- GL thread ownership only
- resource sharing/current-context management only
- just enough integration surface for the selected MediaPipe GPU helpers and
  calculators

If the layer starts absorbing generic task/runtime behavior, the boundary is
wrong.

## 3. Why This Layer Exists

The current local MediaPipe GL stack does not give us a Windows-ready primitive
for the worker:

- the current `gl_context` target is blocked at BUILD level on Windows
- the public interface assumes `pthread`
- the implementation assumes a non-Windows thread/runtime model
- the local fork does not include a Windows `WGL` backend

So the problem is not "enable a hidden Windows flag".

The problem is:

- the worker needs a Windows-owned GL execution environment before the higher
  GPU path can even be tested

## 4. Layer Responsibility

The `Windows GL platform layer` should own only the platform primitives the
worker needs to run GL-backed preprocessing and inference.

### Required ownership

- Windows GL context creation
- shared context strategy for worker-owned GPU execution
- make-current / release-current lifecycle
- worker GL thread creation and shutdown model
- synchronization needed to safely hand work to the GL thread
- surface/pbuffer/hidden-window strategy if required by the chosen context
  creation path
- minimal error reporting for context creation/current/share failures

### Required integration boundary

The layer must expose a narrow API that lets the worker or worker-owned helper
code do these things:

- initialize the GPU runtime once
- acquire a usable current context on the worker thread
- run GL-backed upload/preprocess/inference work
- shut down cleanly

It should be possible to swap the implementation without rewriting the worker's
pose pipeline logic.

## 5. Explicit Non-Goals

The layer must not become a new home for unrelated runtime behavior.

It must not own:

- pose detector graph logic
- landmark graph logic
- JSON payload parsing
- model loading policy
- task API wrapper behavior
- segmentation/tracking/smoothing logic
- fallback backend orchestration
- Python process management

It also should not try to become a generic cross-platform MediaPipe GPU
abstraction. The scope is Windows-only and worker-only.

## 6. Candidate API Shape

The exact API can change, but the shape should stay this small.

### Initialization

- create platform/runtime object
- create primary GL context
- create or bind worker execution context

### Runtime

- run a closure or worker task on the GL thread with a current context
- expose any handles/adapters strictly required by MediaPipe GPU helpers
- report fatal platform errors in a worker-consumable form

### Shutdown

- stop GL thread
- release shared resources
- destroy contexts/surfaces in a deterministic order

If the first draft API needs many more responsibilities than this, the layer is
already too wide.

## 7. Dependency Policy

The platform layer should depend on:

- Windows platform primitives
- desktop OpenGL/WGL primitives
- the narrowest local utility layer needed for worker integration

It should not depend directly on:

- task-layer pose targets
- task runners
- model bundle helpers
- `.task` resource loading
- general MediaPipe graph wrappers

MediaPipe GPU helper/calculator deps should sit above this platform layer, not
inside it, unless a very specific adapter is unavoidable.

## 8. Success Criteria For The Layer Itself

The layer is not "done" when it compiles.

It is done only when all of these are true:

1. a worker-owned GL thread starts reliably on Windows
2. a current GL context can be acquired on that thread
3. a second task can reuse the same runtime without recreating everything
4. shutdown is deterministic and does not leak obvious context/thread state
5. failures are surfaced clearly enough for the worker to fail fast

If any of these fail, the layer is not yet a usable prerequisite.

## 9. GPU Viability Test Ladder

Owning the platform layer does not prove that the final worker can use GPU.

The repo should validate GPU viability in this exact order.

### Stage 1: Context smoke test

Prove:

- Windows GL platform layer initializes
- worker GL thread starts
- current context can be acquired
- minimal GL command execution succeeds

This only proves the platform layer is alive.

### Stage 2: Upload and preprocessing smoke test

Prove:

- CPU-loaded image can enter the GL path
- the selected MediaPipe GL preprocessing path can run
- `image -> GL upload -> image_to_tensor` completes without falling back
  silently to CPU

This is the first meaningful GPU-path proof.

### Stage 3: Single-model inference smoke test

Prove:

- one explicit TFLite model can run through the intended GPU-backed inference
  path on Windows
- output tensors are produced correctly

This is the first proof that the worker can do useful GPU work.

### Stage 4: Detector plus landmark chain

Prove:

- detector inference works
- ROI handoff works
- landmark inference works
- 33 normalized landmarks are serialized correctly

Only after this stage can the worker claim practical GPU functionality.

## 10. Failure Rules

The redesign should stop and reconsider the OpenGL direction if any of these
become true:

- the platform layer compiles, but MediaPipe GL helpers still require the old
  incompatible `gl_context` unchanged
- `image_to_tensor` cannot be made to use the owned Windows GL runtime without
  broad MediaPipe GPU fork work
- the first viable inference path still collapses to CPU as the normal runtime
- the required Windows GL work expands into a broad cross-cutting MediaPipe port

If these happen, the platform layer is no longer a bounded prerequisite. It has
become a de facto fork strategy again.

## 11. Recommended Next Implementation Order

1. Draft the exact interface of the repo-owned `Windows GL platform layer`.
2. Build a standalone context smoke test binary outside the full pose worker.
3. Validate `image -> GL upload -> image_to_tensor` on that runtime.
4. Validate one explicit model inference on the same runtime.
5. Only then draft the first real worker GPU target around detector and
   landmark inference.

This keeps the main risk on a short loop.

## 12. Practical Conclusion

Yes, the repo can choose to own a `Windows GL platform layer`.

If that layer works, it can unlock the ability to test and possibly use the
OpenGL/GL GPU path on Windows.

But that layer alone does not guarantee final GPU success.

It is a prerequisite gate, not the finish line.

The right engineering posture is:

- treat the layer as a bounded platform prerequisite
- prove GPU viability with staged smoke tests
- only then spend effort on the full pose worker graph
