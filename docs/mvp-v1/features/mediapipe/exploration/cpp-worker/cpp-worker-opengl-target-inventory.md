# MediaPipe C++ Worker OpenGL Target Inventory

## 1. Purpose

This document turns the reset plan into a concrete dependency inventory for the
Windows `OpenGL/GL-based MediaPipe GPU` direction.

It is not a final `BUILD.bazel`.

It is a filtering document that answers one question first:

"Which targets are even allowed into the first owned GPU worker design?"

## 2. Scope

This inventory is for the redesigned worker described in
[cpp-worker-reset-plan.md](/C:/Users/neighbor/Documents/Code/Github/rack-tracker-forked/docs/mvp-v1/features/mediapipe/exploration/cpp-worker/cpp-worker-reset-plan.md).

Assumptions:

- Windows only
- GPU-first
- OpenGL/GL-based MediaPipe GPU path only
- image-per-frame only
- two explicit local TFLite models
- one pose only
- no `.task` bundle
- no task-layer API ownership

## 3. Current Constraint

The current upstream/forked `mediapipe/gpu` package still explicitly treats
Windows as incompatible for the normal GL path in several places.

Observed examples from the local fork:

- `//mediapipe/gpu:disable_gpu` includes `@platforms//os:windows`
- `//mediapipe/gpu:gl_context` is marked incompatible on Windows
- large parts of the current GL support assume pthread/EGL-style infra that is
  not ready for Windows as-is

That means this inventory is not claiming "the current GL stack already works on
Windows". It is defining the smallest candidate surface we should evaluate and
adapt, instead of dragging the whole task-layer build with it.

## 4. Inventory Method

Targets were filtered using the local fork under:

- `mediapipe/calculators/tensor`
- `mediapipe/tasks/cc/components/processors`
- `mediapipe/gpu`

The filter rule was:

- keep targets that look directly relevant to an owned GPU preprocessing or GPU
  inference path
- mark targets as `candidate`, `conditional`, or `exclude`
- prefer narrow runtime primitives over task-layer wrappers

## 5. Candidate Core GPU Targets

These are the first-pass targets that look structurally relevant to the owned
 OpenGL worker path.

### GPU context and helper layer

- `//mediapipe/gpu:gl_base`
- `//mediapipe/gpu:gl_base_hdr`
- `//mediapipe/gpu:egl_base`
- `//mediapipe/gpu:gl_context`
- `//mediapipe/gpu:gl_calculator_helper`
- `//mediapipe/gpu:gpu_service`
- `//mediapipe/gpu:graph_support`

Reason:

- these are the basic OpenGL context/helper/service primitives used by the
  MediaPipe GL calculators and GPU tensor conversion path

### GPU buffer layer

- `//mediapipe/gpu:gpu_buffer`
- `//mediapipe/gpu:gpu_buffer_format`
- `//mediapipe/gpu:gpu_buffer_storage`
- `//mediapipe/gpu:gpu_buffer_storage_image_frame`
- `//mediapipe/gpu:gl_texture_buffer`
- `//mediapipe/gpu:gl_texture_view`
- `//mediapipe/gpu:gl_texture_buffer_pool`
- `//mediapipe/gpu:gpu_buffer_multi_pool`

Reason:

- these appear to be the minimum GPU image/texture transport primitives behind
  GL-based MediaPipe image processing

### GPU origin and protocol layer

- `//mediapipe/gpu:gpu_origin_cc_proto`
- `//mediapipe/gpu:gpu_origin_proto`
- `//mediapipe/gpu:gpu_origin_utils`

Reason:

- image preprocessing and tensor conversion already depend on `gpu_origin`
  configuration

## 6. Candidate Tensor / Preprocessing Targets

These look like the most relevant GPU-side preprocessing path candidates.

### Preferred entry point candidates

- `//mediapipe/calculators/tensor:image_to_tensor_calculator`
- `//mediapipe/calculators/tensor:image_to_tensor_calculator_cc_proto`
- `//mediapipe/calculators/tensor:image_to_tensor_converter`
- `//mediapipe/tasks/cc/components/processors:image_preprocessing_graph`

Reason:

- this is the smallest currently visible "image -> model tensor" path that
  already understands GPU origin and calculator graph wiring

### GPU-specific converter candidates

- `//mediapipe/calculators/tensor:image_to_tensor_calculator_gpu_deps`
- `//mediapipe/calculators/tensor:image_to_tensor_converter_gl_buffer`
- `//mediapipe/calculators/tensor:image_to_tensor_converter_gl_texture`

Reason:

- the existing tensor preprocessing path fans into these targets for non-CPU
  image conversion on GL platforms

### Lower-level tensor conversion candidates

- `//mediapipe/calculators/tensor:tensor_converter_calculator`
- `//mediapipe/calculators/tensor:tensor_converter_gl30`
- `//mediapipe/calculators/tensor:tensor_converter_gl31`

Reason:

- if `image_preprocessing_graph` is still too wide, these may be better
  building blocks for a worker-owned narrower preprocessing chain

## 7. Candidate Detector / Landmark Runtime Targets

These are not yet the final target set. They are the likely runtime families we
must inspect next.

### Detector-side candidates

- `//mediapipe/calculators/tensor:inference_calculator`
- `//mediapipe/calculators/tensor:inference_calculator_cc_proto`
- `//mediapipe/calculators/tensor:tensors_to_detections_calculator`
- `//mediapipe/calculators/tensor:tensors_to_detections_calculator_cc_proto`
- `//mediapipe/calculators/tflite:ssd_anchors_calculator`
- `//mediapipe/calculators/tflite:ssd_anchors_calculator_cc_proto`
- `//mediapipe/calculators/util:non_max_suppression_calculator`
- `//mediapipe/calculators/util:non_max_suppression_calculator_cc_proto`
- `//mediapipe/calculators/util:detections_to_rects_calculator`
- `//mediapipe/calculators/util:detections_to_rects_calculator_cc_proto`
- `//mediapipe/calculators/util:alignment_points_to_rects_calculator`
- `//mediapipe/calculators/util:rect_transformation_calculator`
- `//mediapipe/calculators/util:rect_transformation_calculator_cc_proto`

### Landmark-side candidates

- `//mediapipe/calculators/tensor:tensors_to_floats_calculator`
- `//mediapipe/calculators/tensor:tensors_to_landmarks_calculator`
- `//mediapipe/calculators/tensor:tensors_to_landmarks_calculator_cc_proto`
- `//mediapipe/calculators/util:landmark_letterbox_removal_calculator`
- `//mediapipe/calculators/util:landmark_projection_calculator`
- `//mediapipe/calculators/util:landmarks_to_detection_calculator`
- `//mediapipe/calculators/util:refine_landmarks_from_heatmap_calculator`
- `//mediapipe/calculators/util:refine_landmarks_from_heatmap_calculator_cc_proto`
- `//mediapipe/calculators/util:visibility_copy_calculator`
- `//mediapipe/calculators/util:visibility_copy_calculator_cc_proto`
- `//mediapipe/calculators/util:world_landmark_projection_calculator`

Reason:

- these are the calculators already visible on the current worker runtime path
  after graph slimming, but they should now be re-used directly rather than via
  task-layer wrappers

## 8. Conditional Targets

These are not phase-1 defaults, but may still be required depending on the
 exact owned graph shape.

- `//mediapipe/gpu:image_frame_to_gpu_buffer_calculator`
- `//mediapipe/gpu:gpu_buffer_to_image_frame_calculator`

Reason:

- only needed if the owned graph explicitly crosses CPU image frame and GPU
  buffer boundaries using calculator nodes instead of direct worker-side setup

- `//mediapipe/calculators/tensor:image_to_tensor_converter_opencv`

Reason:

- this is phase-1 fallback material, not part of the intended GPU-first path

- `//mediapipe/calculators/tensor:inference_calculator_cpu`
- `//mediapipe/calculators/tensor:inference_calculator_xnnpack`

Reason:

- these may exist only as isolated CPU fallback branches

## 9. Exclude By Default

These should stay out of the primary worker target unless later proven
unavoidable.

### Task-layer wrappers

- `//mediapipe/tasks/c/vision/pose_landmarker:pose_landmarker_lib`
- `//mediapipe/tasks/cc/vision/pose_landmarker`
- `//mediapipe/tasks/cc/vision/pose_landmarker:pose_landmarker_graph`
- `//mediapipe/tasks/cc/vision/pose_landmarker:pose_landmarks_detector_graph`
- `//mediapipe/tasks/cc/vision/pose_detector:pose_detector_graph`

Reason:

- these are exactly the wrappers that widened the graph and pushed the build
  back into patch-chasing

### Task infra

- task API factories
- task runners
- model asset bundle resources
- model task graph wrappers
- task graph proto layering helpers

Reason:

- all of these are convenience layers, not the owned runtime surface

### Non-GL GPU backends

- WebGPU targets under `//mediapipe/gpu/webgpu/...`
- Metal targets
- DirectML-specific branches if introduced separately

Reason:

- phase 1 allows only one Windows GPU backend: OpenGL/GL MediaPipe GPU

### Non-phase-1 feature branches

- segmentation calculators
- smoothing calculators
- stream tracking path
- multi-pose loop path

Reason:

- these are explicit scope exclusions from the reset plan

## 10. Known Risk Areas

These are the main technical risks before any implementation starts.

### Risk 1: Windows GL context incompatibility

The local `mediapipe/gpu` BUILD already marks normal `gl_context` as
incompatible on Windows.

Implication:

- phase 1 may require an owned Windows GL context adaptation layer
- or a minimal fork of the GL support layer
- or a decision that the current GL target set is not salvageable on Windows

This is the first thing that must be verified.

### Risk 2: `image_preprocessing_graph` may still be too wide

Even if we stop using the task-layer pose graph, the preprocessing graph may
still pull more than we want.

Implication:

- we may need to drop from `image_preprocessing_graph` to a worker-owned
  narrower calculator chain

### Risk 3: GPU-first may still require CPU boundary crossings

If file loading starts on CPU image frames and the graph then uploads to GPU,
some CPU image plumbing will remain unavoidable.

Implication:

- the correct target boundary is "GPU-first runtime", not "GPU-only source tree"

### Risk 4: OpenGL ES vs desktop GL mismatch

Several tensor converter paths are keyed on `MEDIAPIPE_OPENGL_ES_VERSION`.

Implication:

- Windows support may require a clear compatibility story for desktop GL vs the
  GLES-oriented assumptions in the current code

## 11. Recommended Next Investigation Order

1. Verify whether `//mediapipe/gpu:gl_context` can be made Windows-compatible
   with a bounded owned change.
2. Confirm the smallest target set needed to get:
   - file image
   - GPU upload
   - image-to-tensor conversion
3. Confirm whether `image_to_tensor_calculator` is acceptable as phase-1
   preprocessing, or whether it must be replaced with a narrower worker-owned
   composition.
4. Define the exact detector-side and landmark-side direct calculator chain
   without any dependency on task-layer pose graphs.
5. Draft the first minimal `BUILD.bazel` around only the candidate targets that
   survive steps 1-4.

## 12. Practical Conclusion

The current best candidate starting set for the OpenGL redesign is:

- `//mediapipe/gpu:gl_context`
- `//mediapipe/gpu:gl_calculator_helper`
- `//mediapipe/gpu:gpu_service`
- `//mediapipe/gpu:gpu_buffer`
- `//mediapipe/gpu:gpu_origin_utils`
- `//mediapipe/calculators/tensor:image_to_tensor_calculator`
- `//mediapipe/calculators/tensor:image_to_tensor_converter_gl_buffer`
- `//mediapipe/calculators/tensor:inference_calculator`
- direct detector/landmark postprocessing calculators

The current best candidate exclusions are:

- all task-layer pose landmarker targets
- `.task` bundle support
- segmentation/tracking/smoothing branches
- WebGPU/Metal/DirectML alternatives

This inventory should be used as the input document for the first worker-owned
GPU `BUILD.bazel` draft.

