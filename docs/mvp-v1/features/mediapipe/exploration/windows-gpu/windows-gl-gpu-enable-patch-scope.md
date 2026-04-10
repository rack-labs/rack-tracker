# Windows GL GPU Enable Patch Scope

## 1. Purpose

This memo defines the narrowest patch scope required to move the redesign from:

- `Windows GL runtime exists`

to:

- `MediaPipe GPU preprocessing can initialize on Windows`

It is based on the actual Stage 2 result:

- Stage 2 binary builds
- Stage 2 runtime fails at graph initialization
- failure message: `ImageCloneCalculator: GPU processing is disabled in build flags`

## 2. Current Blocker

The immediate blocker is not the worker-owned Windows GL runtime anymore.

The immediate blocker is the shared MediaPipe GPU policy and platform model:

- `mediapipe/gpu/BUILD` maps Windows into `disable_gpu`
- graph calculators that request GPU reject Windows at runtime because the
  effective build flags still say GPU is disabled

This means Stage 2 is blocked before any real GPU upload or
`image_to_tensor` execution starts.

## 3. Evidence

### Build policy

In [`mediapipe/gpu/BUILD`](/C:/Users/neighbor/Documents/Code/Github/mediapipe-forked/mediapipe/gpu/BUILD):

- `selects.config_setting_group(name = "disable_gpu", ...)`
- that group explicitly includes `@platforms//os:windows`

Implication:

- any target using `//mediapipe/gpu:disable_gpu` treats Windows as GPU-disabled

### Runtime contract

[`image_clone_calculator.cc`](/C:/Users/neighbor/Documents/Code/Github/mediapipe-forked/mediapipe/calculators/image/image_clone_calculator.cc)
rejects `output_on_gpu: true` when GPU is disabled.

Implication:

- even a valid Windows GL runtime cannot be used by the graph while the shared
  build contract still says GPU is disabled

### Platform header model

[`gl_base.h`](/C:/Users/neighbor/Documents/Code/Github/mediapipe-forked/mediapipe/gpu/gl_base.h)
currently routes non-Apple platforms through:

- `EGL`
- `GLES2/GLES3`

There is no Windows `WGL` path in this header.

Implication:

- removing Windows from `disable_gpu` is necessary, but still not sufficient

### GL profile model

[`port.h`](/C:/Users/neighbor/Documents/Code/Github/mediapipe-forked/mediapipe/framework/port.h)
drives `MEDIAPIPE_OPENGL_ES_VERSION`.

Today:

- if GPU is disabled, it becomes `0`
- on normal non-Apple, non-WebGPU platforms it becomes `31`

But the existing Windows path still lacks a matching GL header/backend model.

Implication:

- once Windows is no longer forced into `disable_gpu`, the repo must decide
  what OpenGL ES compatibility story Windows desktop GL will use

## 4. What Must Change

To make Stage 2 meaningful, the repo must patch four layers together.

### Layer A: GPU policy gate

Patch scope:

- `mediapipe/gpu/BUILD`

Required change:

- Windows must stop matching the current broad `disable_gpu` group for the
  owned Windows GL path

Important constraint:

- this should be narrow and intentional
- do not globally pretend all historical MediaPipe GPU targets are suddenly
  Windows-ready

Recommended shape:

- split the current `disable_gpu` policy into:
  - explicit `disable_gpu_flag`
  - legacy unsupported platforms
  - a new Windows-owned experimental GPU path gate

### Layer B: Windows GL backend surface

Patch scope:

- current `gl_context` ownership boundary
- or a repo-owned adapter that replaces it for the worker path

Required change:

- provide a Windows GL backend/context model instead of the current
  `pthread + EGL` assumption

This includes:

- context creation
- current-context management
- worker-thread execution model
- resource sharing semantics

### Layer C: GL header and loader model

Patch scope:

- `mediapipe/gpu/gl_base.h`
- any immediate transitive headers/helpers that assume `EGL + GLES`

Required change:

- add a Windows path that uses Windows desktop GL/WGL-friendly headers and
  declarations instead of the current Linux-style EGL/GLES includes

Without this, the policy gate can be lifted but the actual GL layer will still
be mismatched.

### Layer D: OpenGL ES compatibility contract

Patch scope:

- `mediapipe/framework/port.h`
- possibly selected GL converter targets that are guarded by
  `MEDIAPIPE_OPENGL_ES_VERSION`

Required change:

- define what Windows desktop GL means for the current MediaPipe GL converters

This matters because:

- `image_to_tensor_converter_gl_texture.cc` is gated on
  `MEDIAPIPE_OPENGL_ES_VERSION >= 300`
- `image_to_tensor_converter_gl_buffer.cc` is gated on
  `MEDIAPIPE_OPENGL_ES_VERSION >= 310`

So the repo must decide:

- whether Windows desktop GL 4.6 will be treated as satisfying the GLES 3.0/3.1
  contract for these targets
- or whether a narrower converter path will be used first

## 5. Recommended Minimal Enable Order

Do not patch everything at once.

Use this order.

### Step 1: Narrow policy unblocking

Goal:

- allow the owned Stage 2 path to stop inheriting `disable_gpu` on Windows

Deliverable:

- a narrow `mediapipe/gpu/BUILD` patch that no longer hard-disables Windows for
  the owned experimental path

Exit check:

- Stage 2 runtime no longer fails with `GPU processing is disabled in build flags`

### Step 2: Header/backend alignment

Goal:

- make the selected Windows GL path compile and initialize honestly

Deliverable:

- Windows GL backend/header path chosen and owned

Exit check:

- the calculators needed by Stage 2 can initialize GPU helpers without hitting
  missing platform assumptions immediately

### Step 3: Converter contract selection

Goal:

- choose the smallest converter path that matches the Windows GL capabilities

Recommended first target:

- prefer `gl_texture` before `gl_buffer` if the compute-shader / GLES 3.1
  compatibility story is not ready yet

Reason:

- `gl_texture` is gated at GLES 3.0
- `gl_buffer` is gated at GLES 3.1 and implies a wider compute-style contract

Exit check:

- Stage 2 can reach `ImageToTensorCalculator` execution on a real GPU-backed
  image path

## 6. What Should Not Happen

Avoid these mistakes.

- do not globally remove Windows from `disable_gpu` without an owned backend
  plan
- do not jump to Stage 3 inference while Stage 2 still dies in graph init
- do not treat desktop GL support as automatically equivalent to the current
  EGL/GLES assumptions without checking the guarded converter paths
- do not reintroduce task-layer graphs just to work around this policy gate

## 7. Immediate Practical Recommendation

The next useful implementation pass is:

1. patch `mediapipe/gpu/BUILD` so the owned Windows experimental path no longer
   maps directly to `disable_gpu`
2. introduce or wire the Windows GL backend/header path needed by that change
3. rerun Stage 2 and observe the next failure point

That is the shortest high-signal loop.

## 8. Conclusion

Stage 2 already proved something valuable:

- the first hard blocker is now known exactly

But that blocker is a bundle, not a single line:

- GPU policy gate
- Windows GL backend surface
- GL header model
- GLES compatibility contract

The repo should treat those four items as one patch scope for the next pass,
with the initial goal of making Stage 2 initialize honestly rather than
claiming full GPU inference yet.
