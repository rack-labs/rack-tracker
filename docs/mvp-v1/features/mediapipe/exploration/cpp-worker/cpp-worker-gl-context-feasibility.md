# MediaPipe C++ Worker Windows GL Context Feasibility

## 1. Purpose

This memo answers the next blocking question for the redesigned GPU-first C++
worker:

"Can the current local `//mediapipe/gpu:gl_context` path be used on Windows for
the OpenGL/GL-based MediaPipe GPU worker with a bounded change?"

Short answer:

- not as-is
- not with a simple Bazel flag flip
- only with an owned Windows GL platform adaptation layer or a dedicated fork of
  the GL context/runtime support layer

This memo is a feasibility filter, not an implementation plan.

## 2. Inputs Reviewed

The conclusion below is based on the local fork under
`C:\Users\neighbor\Documents\Code\Github\mediapipe-forked\mediapipe\gpu`:

- `BUILD`
- `gl_context.h`
- `gl_context.cc`
- `gl_context_eagl.cc`
- `gl_context_egl.cc`
- `gl_context_nsgl.cc`
- `gl_context_webgl.cc`

## 3. Current Finding

The current local `mediapipe/gpu` GL path is structurally non-Windows.

That is not just a policy choice in the build file. The implementation also
assumes platform/runtime pieces that are missing on Windows in the local fork.

## 4. Evidence

### Build-level incompatibility is explicit

The local `mediapipe/gpu/BUILD` does two important things:

- `//mediapipe/gpu:disable_gpu` includes `@platforms//os:windows`
- `//mediapipe/gpu:gl_context` is marked incompatible on Windows

The BUILD comment also states that `gl_context` uses `pthread` and is therefore
not compatible with Windows in its current form.

Implication:

- the current fork is intentionally preventing this target from entering a
  Windows build

### Header-level pthread dependency is direct

`gl_context.h` directly includes `pthread.h`.

Implication:

- this is not a small implementation-only portability issue
- the public GL context interface itself currently assumes pthread-backed
  synchronization/thread ownership support

### Implementation-level pthread usage is real, not incidental

`gl_context.cc` uses pthread APIs directly, including:

- `pthread_setname_np`
- `pthread_create`
- `pthread_detach`
- `pthread_join`
- `pthread_equal`
- `pthread_self`

Implication:

- a Windows port would need either:
  - a real portability layer for the thread/runtime model
  - or a rewritten Windows-specific context execution model

### No Windows GL backend exists in the local fork

The local fork contains platform-specific variants for:

- EGL
- EAGL
- NSGL
- WebGL

It does not contain a Windows-specific implementation such as a `WGL` backend.

Implication:

- even if pthread usage were abstracted away, the local fork still lacks the
  actual Windows GL context backend needed for the normal desktop Windows path

## 5. What This Means For The Worker Redesign

The current OpenGL/GL decision remains valid as a target architecture choice,
but it is not yet a buildable runtime choice with the current local MediaPipe GL
stack.

In practical terms:

- the worker redesign is not blocked by pose graph complexity first
- it is blocked by the absence of a Windows-owned GL platform layer first

That changes the sequencing.

We should not draft the first real worker `BUILD.bazel` around
`//mediapipe/gpu:gl_context` as though it were already a usable Windows
primitive.

## 6. Bounded Salvage Options

There are only two realistic bounded directions if `OpenGL/GL` remains the
chosen Windows GPU path.

### Option A: Owned Windows GL context adapter

Create a repo-owned Windows GL platform layer that replaces the missing parts of
the current `gl_context` dependency chain for the worker's narrow use case.

Likely ownership areas:

- Windows thread/runtime abstraction for the GL worker thread
- Windows GL context creation and sharing strategy
- context current/make-current lifecycle
- texture/buffer interop assumptions used by the selected calculators

Pros:

- keeps the worker redesign narrow and explicit
- avoids dragging the full task-layer graph back into scope

Cons:

- this is no longer "reuse MediaPipe GPU support as-is"
- platform work becomes a real deliverable in phase 1

### Option B: Fork and port `mediapipe/gpu:gl_context`

Treat the local MediaPipe GL support layer as a component that must be ported to
Windows for this repo.

Likely ownership areas:

- replace or abstract pthread assumptions
- add a Windows-specific GL backend
- update BUILD compatibility rules
- verify downstream GL helper/calculator targets against the new backend

Pros:

- aligns more closely with existing MediaPipe GPU helper usage

Cons:

- wider blast radius
- higher maintenance burden
- easy to drift back toward the same "private Windows fork" problem that caused
  the reset

## 7. Current Recommendation

Do not assume the current `gl_context` target can be "unblocked" with a small
patch.

Treat Windows GL context support as a dedicated prerequisite workstream for the
GPU-first redesign.

Recommended decision:

- keep `OpenGL/GL-based MediaPipe GPU` as the desired worker runtime direction
- explicitly add `Windows GL platform layer feasibility and ownership boundary`
  as the next design gate
- do not begin full worker graph or worker target implementation until that gate
  is resolved

## 8. Design Gate

Before phase-1 implementation begins, answer these exactly:

1. Will this repo own a Windows GL context layer outside the current
   `mediapipe/gpu:gl_context` target?
2. If not, which exact local fork files will be ported and permanently owned?
3. What is the minimum supported Windows GL profile for the tensor conversion
   path?
4. Which current candidate calculators require the existing MediaPipe GL helper
   stack unchanged?
5. Can the worker keep GPU upload and preprocessing on a bounded platform layer
   without importing the whole current GL context architecture?

If these are unanswered, the redesign is still underspecified.

## 9. Practical Conclusion

For the current repo state, the OpenGL redesign should be treated as:

- architecturally plausible
- implementation-blocked on Windows platform support
- not ready for the first concrete worker build target yet

The next useful artifact is not a worker executable patch.

The next useful artifact is a narrow `Windows GL platform layer` design memo
that decides whether the repo will:

- own a new adapter layer
- or own a targeted port of the existing MediaPipe GL context stack
