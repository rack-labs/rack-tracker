# Windows GL Context Smoke Test Plan

## 1. Purpose

This document defines the first executable validation target for the redesigned
GPU-first MediaPipe C++ worker on Windows.

The purpose of this smoke test is narrow:

- prove that a repo-owned Windows GL platform layer can start
- prove that it can acquire a current GL context on a worker-owned thread
- prove that minimal GL work can execute successfully

This test does not prove pose inference yet.

It only proves that the platform prerequisite is alive.

## 2. Why This Comes First

The current local MediaPipe GL path is blocked on Windows before worker graph
complexity even matters.

So the first useful binary is not a pose worker skeleton.

The first useful binary is a standalone Windows GL context smoke test with no
pose-specific runtime dependencies.

If this binary does not pass, any worker implementation effort above it is
premature.

## 3. Scope

The smoke test should be:

- Windows only
- standalone
- independent from the full pose worker
- independent from task-layer pose targets
- as small as possible

It may live under a dedicated package such as:

`poseLandmarker_Python/cpp_worker/platform/windows_gl/`

## 4. Test Goal

The binary should prove all of the following in one run:

1. initialize the repo-owned Windows GL platform layer
2. create the primary GL context
3. start or bind the intended GL worker thread
4. make the context current on that thread
5. execute a minimal GL command sequence successfully
6. report a structured success result
7. shut down cleanly

If any of those fail, the test fails.

## 5. Explicit Non-Goals

This smoke test must not try to do too much.

It must not include:

- image decoding
- MediaPipe pose graphs
- detector inference
- landmark inference
- TFLite model loading
- JSON worker protocol compatibility with the final worker
- Python integration work

Those belong to later stages.

## 6. Proposed Binary Shape

Recommended target names:

- package: `//poseLandmarker_Python/cpp_worker/platform/windows_gl`
- binary: `windows_gl_context_smoke_test`

Recommended files:

- `windows_gl_platform.h`
- `windows_gl_platform.cc`
- `windows_gl_context_smoke_test.cc`
- `BUILD.bazel`

If helper files are needed, keep them under the same package unless they are
clearly reusable.

## 7. Minimal Runtime Contract

The smoke test binary should expose a very small contract.

### Input

No required external input in the first version.

Optional flags can be added later for:

- verbose logging
- alternate context creation mode
- alternate pixel format / profile

But the default path should be fixed and deterministic.

### Output

The test should print a short structured result, for example:

- initialization success/failure
- context creation success/failure
- make-current success/failure
- minimal GL command success/failure
- shutdown success/failure

This can be plain text in stage 1. JSON is optional.

## 8. Required Implementation Behavior

The test runtime must exercise the exact primitives the later worker will rely
on.

### Platform bootstrap

The platform layer must:

- initialize any required window/class/runtime state
- create any hidden surface or hidden window required for a valid GL context
- create the GL context using the chosen Windows strategy

### GL worker thread

The platform layer must:

- create or bind a dedicated worker thread for GL execution
- move or create the active context according to the chosen ownership model
- ensure that the test GL work runs on the same model intended for the worker

### GL command execution

The smoke test should run a very small command sequence, such as:

- make context current
- query basic GL identity/version strings
- clear or bind minimal state
- flush and return success

The exact commands are flexible, but they must prove that a live current
context exists and can execute non-trivial GL work.

## 9. Success Criteria

The smoke test passes only if all of these are true:

1. the process exits with success
2. the GL thread starts reliably
3. the context is successfully made current on the intended thread
4. the test can query valid GL identity/version information
5. at least one minimal GL command sequence completes successfully
6. shutdown completes without hanging

If the test passes only once but not repeatedly, it is not yet good enough.

## 10. Failure Diagnostics

The smoke test should fail loudly and specifically.

Minimum diagnostics:

- which stage failed
- whether failure happened before or after thread start
- whether context creation or make-current failed
- whether GL identity/version query failed
- whether shutdown hung or returned an error

The binary should not collapse all failures into one generic "GPU init failed"
message.

## 11. Out-Of-Scope Dependencies

This binary should avoid:

- MediaPipe task-layer targets
- image preprocessing calculators
- inference calculators
- model resources
- Python-facing worker protocol code

If one of these becomes necessary for the smoke test, the test is too wide.

## 12. What Passing This Test Actually Proves

If this test passes, we can claim only this:

- the repo-owned Windows GL platform layer can create and manage a live GL
  runtime on Windows

We still cannot claim:

- MediaPipe GL helpers work on top of it
- `image_to_tensor` works on top of it
- TFLite GPU inference works on top of it
- pose inference works on top of it

Those require later tests.

## 13. Next Stage After Success

If the smoke test passes reliably, the immediate next artifact should be:

- `image -> GL upload -> image_to_tensor` smoke test

That is the first stage that proves the MediaPipe-side GPU preprocessing path
can sit on the owned Windows GL runtime.

Only after that should we attempt:

- single-model GPU inference
- detector + landmark chain

## 14. Kill Criteria

Stop and reconsider the OpenGL worker direction if any of these become true
during stage 1:

- stable context creation requires broad changes across unrelated MediaPipe GPU
  packages
- the owned platform layer cannot provide a reliable current-context model
- repeated init/shutdown is unstable
- the only working route depends on reviving the old incompatible
  `mediapipe/gpu:gl_context` unchanged

If these happen, the Windows GL path is not a bounded prerequisite anymore.

## 15. Practical Conclusion

The correct next implementation target is not the pose worker.

The correct next implementation target is a tiny standalone binary that answers
one question cleanly:

"Can this repo own a stable Windows GL runtime at all?"

If the answer is yes, the redesign can move to MediaPipe-side GPU preprocessing.
If the answer is no, the OpenGL plan should be reconsidered before more worker
design effort is spent.
