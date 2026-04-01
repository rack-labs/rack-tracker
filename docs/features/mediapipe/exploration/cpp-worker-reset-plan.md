# MediaPipe C++ Worker Reset Plan

## 1. Purpose

This document replaces the current patch-chasing direction for the C++ worker.

The previous approach tried to keep the existing MediaPipe Tasks C++ API path
alive on Windows/MSVC by patching the next failing source file. That approach
has already proven unstable:

- the worker build kept pulling broad task and calculator graphs
- runtime-unrelated build surfaces stayed in scope for too long
- even after graph slimming, unavoidable runtime files still required repeated
  MSVC-specific patches
- progress was real, but the architecture was converging on "maintain a private
  Windows fork of MediaPipe Tasks" instead of "ship a narrow pose worker"

The reset goal is to change the ownership boundary.

The new goal is:

- keep Python responsible for job orchestration, frame extraction, result
  mapping, and API responses
- keep the worker responsible only for local pose inference on extracted frames
- stop depending on the full MediaPipe Tasks C++ API stack for the runtime path
- own a minimal worker graph and a minimal Bazel target surface
- make GPU the primary runtime target rather than a later optional add-on

## 2. Decision

We will no longer treat `//mediapipe/tasks/c/vision/pose_landmarker` or
`//mediapipe/tasks/cc/vision/pose_landmarker` as the primary implementation
surface for the worker.

Instead, the worker will be redesigned around a repo-owned minimal inference
path with explicit boundaries:

- input: extracted frame file paths from Python
- runtime: worker-owned MediaPipe graph or worker-owned direct calculator chain
- output: JSON shaped for the existing Python pipeline
- Windows GPU backend: OpenGL/GL-based MediaPipe GPU path

This means the worker stops being "a thin wrapper over MediaPipe PoseLandmarker"
and becomes "a narrow pose inference executable that happens to use selected
MediaPipe building blocks".

## 3. Non-Goals

The reset plan does not attempt to solve these in phase 1:

- live stream mode
- segmentation masks
- multi-pose output
- world-landmark completeness beyond what Python currently needs
- generic task reuse
- reuse of the official PoseLandmarker task API as-is

If a feature expands the graph significantly, it is out of scope for phase 1.

## 4. Hard Scope Boundary

Phase 1 worker contract:

- platform: Windows only
- input source: extracted image files only
- running mode: image-per-frame only
- Windows GPU backend: OpenGL/GL-based MediaPipe GPU
- delegate policy: GPU first, CPU fallback allowed only as an explicit fallback
  path
- model count: exactly two local TFLite assets
  - pose detector
  - pose landmarks detector
- pose count: exactly one
- output: 33 normalized landmarks only

Explicit exclusions:

- `.task` bundle parsing
- model asset bundle resources
- task API factories
- task runners
- task graph options proto layering
- segmentation branches
- smoothing branches
- tracking branches
- flow limiter and async task APIs
- CPU-only and XNNPACK-first detours unless they are required as explicit
  fallback targets
- DirectML-first redesigns or multi-backend support in phase 1

## 5. New Architecture

### Python side

Python remains the owner of:

- video decode and frame extraction
- frame path generation
- process lifecycle
- timeout management
- benchmark aggregation
- result schema mapping
- fallback selection between backends

No major Python architecture change is required beyond selecting the new worker
binary and payload contract.

### Worker side

The worker owns only:

- stdin JSON parsing
- model path validation
- image loading
- minimal pose detector inference
- minimal landmark detector inference
- JSON serialization

### MediaPipe usage model

The worker should use one of these, in priority order:

1. worker-owned minimal graph under a repo-owned package
2. worker-owned direct calculator composition without task-layer wrappers
3. direct TFLite invocation plus only the MediaPipe utility calculators still
   needed for preprocessing/postprocessing

The worker should not depend on the task-layer APIs if the same runtime work can
be expressed with a smaller owned surface.

## 6. Target Repo Shape

Recommended new package root:

`poseLandmarker_Python/cpp_worker/min_graph/`

Recommended owned targets:

- `worker_models_config.h` or JSON config for two model assets
- `worker_graph.cc`
- `worker_graph.h`
- `worker_preprocessing.cc`
- `worker_postprocessing.cc`
- `worker_main.cc`
- `BUILD.bazel`

Recommended Bazel target:

- `//mediapipe/tasks/c/vision/pose_landmarker/worker:min_pose_worker`

But the implementation should not depend on
`//mediapipe/tasks/c/vision/pose_landmarker:pose_landmarker_lib`.

The binary target name may stay the same for Python compatibility, but its deps
must be replaced.

## 7. Required Dependency Strategy

The new worker must depend only on targets that are runtime-essential for this
owned pipeline.

Allowed dependency categories:

- image container types
- tensor container types
- image-to-tensor preprocessing
- TFLite inference runner needed for GPU execution on Windows
- GPU delegate initialization and minimal GPU buffer/origin types required by
  the worker-owned graph
- OpenGL/GL context and helper targets required by the chosen MediaPipe GPU
  path on Windows
- postprocessing calculators needed for detections and landmarks
- minimal formatting/proto types required by those calculators

Disallowed by default:

- task-layer factories
- model bundle helpers
- task runner abstractions
- language generator paths
- general-purpose task graphs not owned by the worker
- optional delegate variants compiled unconditionally

Rule:

If a dependency exists only because a task-layer convenience API pulls it in,
remove the convenience API instead of patching the dependency.

## 8. Model Strategy

Do not use the packaged `.task` bundle in phase 1.

Phase 1 should use explicit local model assets:

- detector model path
- landmarks model path

Reason:

- avoids task bundle parsing and asset bundle resource code
- removes task-layer model resource helpers from the build graph
- makes the worker's runtime contract explicit

Python should pass these paths directly, or the worker should resolve them from
its own config.

## 9. Graph Strategy

The current worker still inherits too much graph structure from:

- pose detector task graph
- pose landmarks detector task graph
- task-layer graph wrappers

The new graph must be explicit and narrow:

1. load image from file
2. upload or adapt image into the OpenGL/GL-based GPU input path
3. preprocess for detector
4. run detector inference
5. decode detector outputs to one ROI
6. preprocess ROI for landmark model
7. run landmark inference
8. decode landmarks
9. serialize 33 normalized landmarks

Anything outside that path is a candidate for removal.

## 10. Build Rules

Phase 1 build rules:

- GPU first by default
- OpenGL/GL-based MediaPipe GPU is the only GPU backend in phase 1
- no implicit CPU-only build path as the main target
- CPU fallback must be isolated behind a separate target or a clearly isolated
  branch
- no XNNPACK-specific CPU variant as the primary implementation path
- no DirectML or alternate GPU backend branch in the primary target
- no task-layer wrapper library deps
- no fallback patch scripts for unrelated codegen or task bundles

If a Bazel target introduces unrelated surfaces, split the target or replace it
with a smaller owned target.

## 11. Implementation Phases

### Phase 0: Decision lock

Deliverable:

- this reset plan approved

Exit criteria:

- agreement that patch-chasing the current task-layer build is stopped

### Phase 1: Minimal owned worker spec

Deliverables:

- exact worker input schema
- exact worker output schema
- exact model asset layout
- exact OpenGL/GL MediaPipe GPU runtime contract for Windows
- exact binary path used by Python

Exit criteria:

- no `.task` bundle dependency in the phase 1 spec
- GPU-first runtime explicitly accepted
- OpenGL/GL selected as the only phase 1 Windows GPU backend
- CPU fallback policy explicitly documented

### Phase 2: Minimal Bazel surface design

Deliverables:

- new owned package layout
- target-by-target dependency list
- rationale for each dependency

Exit criteria:

- every dependency is runtime-essential
- task-layer API deps are absent unless proven unavoidable

### Phase 3: Smoke-build worker skeleton

Deliverables:

- worker binary builds on Windows
- binary accepts stdin JSON
- binary validates image/model paths

Exit criteria:

- executable exists
- no MediaPipe Tasks API dependency in the binary target

### Phase 4: Detector + landmark runtime

Deliverables:

- one frame GPU inference works
- JSON result contains 33 landmarks

Exit criteria:

- known test frame produces valid output
- requested GPU path is actually used on Windows
- Python can parse the worker result

### Phase 5: Python integration

Deliverables:

- `cpp_worker_client.py` updated for the new payload
- feature flag wiring updated
- smoke end-to-end path works

Exit criteria:

- one benchmark job runs end-to-end through the C++ worker path

## 12. Kill Criteria

Stop the redesign and reconsider if any of these become true:

- the new worker still requires `pose_landmarker_lib`
- the new worker still requires task API factory headers
- the new worker still requires model asset bundle helpers
- the new worker still pulls large unrelated task graphs
- Windows/MSVC patch count starts growing across unrelated packages again
- GPU remains nominally "supported" but the real runtime still collapses back
  to CPU as the default path

If any of those happen, the design is not narrow enough.

## 13. Recommended Immediate Next Tasks

1. Freeze the current patch-chasing branch as historical context only.
2. Define the phase 1 worker contract around two explicit TFLite model paths
   and the OpenGL/GL MediaPipe GPU backend.
3. Inventory the exact OpenGL/GL helper, context, and calculator targets needed
   for the worker-owned Windows GPU path.
4. Inventory which calculators are truly required for:
   - detector preprocessing
   - detector decoding
   - landmark preprocessing
   - landmark decoding
   - the OpenGL/GL GPU path
5. Draft a new owned `BUILD.bazel` for the minimal worker package without any
   dependency on the current task-layer pose landmarker targets.
6. Update Python integration assumptions so the worker no longer expects a
   `.task` bundle.

## 14. Recommendation

Do not spend more time trying to finish the current build by patching
`pose_detector_graph.cc`, then the next file after that.

That path may eventually build, but it does not satisfy the actual engineering
goal. The actual goal is a maintainable worker with a narrow owned runtime
surface.

This reset plan should be treated as the new source of truth for the C++ worker
direction.
