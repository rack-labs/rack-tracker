# Windows GL Adapter Minimum Interface

## Purpose

This memo defines the minimum interface for a Windows-specific GL adapter that
replaces the current `mediapipe/gpu:gl_context` path for the worker bring-up.

The goal is narrow:

- unblock Stage 2 preprocessing on Windows
- avoid porting the whole existing `gl_context` design
- keep ownership inside a worker-oriented Windows adapter boundary

## Why Replacement Wins

The current local `gl_context` path is a poor port target for this repo:

- public header depends on `pthread`
- implementation depends on `pthread`
- build rules explicitly treat Windows as unsupported
- there is no local Windows `WGL` backend implementation

So a direct port expands quickly into "maintain a private Windows fork of
MediaPipe GPU core".

The replacement adapter strategy is smaller:

- own Windows GL context creation
- own Windows GL thread model
- expose only the smallest compatibility surface needed by worker bring-up

## Minimum Responsibilities

The adapter must own:

- hidden-window or equivalent context bootstrap
- primary context creation
- optional shared context creation
- GL worker thread lifecycle
- make-current / release-current
- synchronous execution on the GL thread
- deterministic shutdown

The adapter must not own:

- pose graph logic
- model loading
- task APIs
- JSON worker protocol
- detector or landmark logic

## Minimum Interface

The initial interface can stay this small.

### Lifecycle

- `Initialize()`
- `Shutdown()`

### Execution

- `Run(std::function<absl::Status()>)`

### Introspection

- `IsInitialized()`
- `GetGlVersionString()`
- `GetVendorString()`
- `GetRendererString()`

### Native handles

Expose only if strictly required:

- `HGLRC`
- `HDC`
- shared context handle

## Compatibility Goal

The replacement adapter does not need to preserve all existing `gl_context`
behavior.

It only needs enough compatibility for the next bring-up loop:

1. `GlCalculatorHelper`-level initialization path
2. GPU image upload
3. `ImageToTensorCalculator`

If some historical `gl_context` capability is unrelated to those steps, it is
out of scope.

## Integration Strategy

Recommended integration order:

1. create a worker-owned Windows adapter package
2. provide a thin compatibility layer that MediaPipe-side helper code can call
3. rerun Stage 2
4. only expand interface if the next blocker proves it necessary

## Immediate Implementation Rule

Do not begin by copying the existing `gl_context` implementation.

Begin with:

- a tiny interface
- a tiny implementation
- one narrow call path

If the interface starts to mirror the whole existing `gl_context` API, the
replacement strategy has already failed.
