from __future__ import annotations

import json
import logging
from time import perf_counter

import anthropic

from config import ANTHROPIC_API_KEY, LLM_FEEDBACK_ENABLED, LLM_FEEDBACK_MODEL
from service.llm_prompt_payload import LlmPromptPayloadService


logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a strength coach specializing in barbell movements.
You will be provided with biomechanical analysis data from a squat session in JSON format.

Respond strictly in the following JSON format. Output JSON only — no explanation, no markdown:
{
  "overallComment": "Overall assessment of the session (1-2 sentences)",
  "highlights": ["Observation 1", "Observation 2"],
  "corrections": ["Correction 1", "Correction 2"],
  "coachCue": "One short, immediately actionable cue for the next set"
}

Rules:
- highlights: up to 4 items, positive or neutral factual observations
- corrections: up to 4 items, only when a real issue exists; empty array if none
- coachCue: one concise, immediately executable sentence
- Base all statements only on data provided; do not fabricate facts
- Respond entirely in English
"""


class LlmFeedbackService:
    def __init__(self) -> None:
        self._prompt_payload = LlmPromptPayloadService()
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if LLM_FEEDBACK_ENABLED else None

    def build_prompt_payload(self, analysis: dict) -> dict:
        return self._prompt_payload.build(analysis)

    def estimate_prompt_tokens(self, analysis: dict, payload: dict) -> dict:
        diagnostics = self._prompt_payload.estimate_tokens(analysis, payload)
        logger.info(
            "coach_prompt_payload tokens: payload=%s original=%s saved=%s reduction=%.2f",
            diagnostics["payloadApproxTokens"],
            diagnostics["originalAnalysisApproxTokens"],
            diagnostics["savedApproxTokens"],
            diagnostics["reductionRatio"],
        )
        return diagnostics

    def generate(self, analysis: dict, payload: dict | None = None) -> tuple[dict, dict]:
        """Returns (feedback_dict, call_metrics_dict)."""
        coach_payload = payload or self.build_prompt_payload(analysis)

        if not LLM_FEEDBACK_ENABLED or self._client is None:
            logger.info("LLM_FEEDBACK_ENABLED=False — using rule-based feedback")
            feedback = self._generate_rule_based(coach_payload)
            call_metrics = {"enabled": False, "model": "rule-based-analysis-grounded", "fallbackApplied": False, "inputTokens": 0, "outputTokens": 0, "latencyMs": 0.0}
            return feedback, call_metrics

        try:
            return self._generate_llm(coach_payload)
        except Exception as exc:
            logger.warning("LLM call failed (%s: %s) — falling back to rule-based", type(exc).__name__, exc)
            feedback = self._generate_rule_based(coach_payload)
            call_metrics = {"enabled": True, "model": LLM_FEEDBACK_MODEL, "fallbackApplied": True, "inputTokens": 0, "outputTokens": 0, "latencyMs": 0.0}
            return feedback, call_metrics

    # ------------------------------------------------------------------
    # LLM path
    # ------------------------------------------------------------------

    def _generate_llm(self, payload: dict) -> tuple[dict, dict]:
        user_message = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        started = perf_counter()
        message = self._client.messages.create(
            model=LLM_FEEDBACK_MODEL,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        latency_ms = (perf_counter() - started) * 1000.0

        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        try:
            feedback = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM returned non-JSON response: {raw[:200]}") from exc

        feedback_dict = {
            "version": "v3",
            "model": LLM_FEEDBACK_MODEL,
            "overallComment": str(feedback.get("overallComment", "")),
            "highlights": list(feedback.get("highlights", [])),
            "corrections": list(feedback.get("corrections", [])),
            "coachCue": str(feedback.get("coachCue", "")),
        }
        call_metrics = {
            "enabled": True,
            "model": LLM_FEEDBACK_MODEL,
            "fallbackApplied": False,
            "inputTokens": message.usage.input_tokens,
            "outputTokens": message.usage.output_tokens,
            "latencyMs": round(latency_ms, 3),
        }
        return feedback_dict, call_metrics

    # ------------------------------------------------------------------
    # Rule-based fallback (기존 로직 보존)
    # ------------------------------------------------------------------

    def _generate_rule_based(self, coach_payload: dict) -> dict:
        summary = coach_payload.get("sessionSummary", {})
        body_profile = coach_payload.get("bodyProfile", {})
        ground_ref = coach_payload.get("groundContact", {})
        kpis = coach_payload.get("kpis", [])
        issues = coach_payload.get("issueHighlights", [])

        kpi_map = self._build_kpi_map(kpis)
        issue_codes = {str(issue.get("code") or "") for issue in issues}

        exercise_type = str(coach_payload.get("exerciseType") or "unknown")
        rep_count = int(summary.get("repCount") or 0)
        frame_count = int(summary.get("frameCount") or 0)
        sampled_fps = float(summary.get("sampledFps") or 0.0)
        bodyweight_kg = self._as_float(summary.get("bodyweightKg"))
        external_load_kg = self._as_float(summary.get("externalLoadKg"))
        bar_placement_resolved = str(
            summary.get("barPlacementResolved")
            or ground_ref.get("barPlacementResolved")
            or "unknown"
        )
        detection_ratio = float(summary.get("detectionRatio") or 0.0)

        load_phrase = self._format_load_phrase(bodyweight_kg, external_load_kg)
        overview_bits = [
            exercise_type,
            f"{rep_count} reps" if rep_count else "no stable reps",
            f"{frame_count} sampled frames" if frame_count else None,
            f"{sampled_fps:.1f} FPS" if sampled_fps else None,
            load_phrase,
            f"bar placement resolved as {bar_placement_resolved}",
        ]
        overall_comment = ". ".join(bit for bit in overview_bits if bit) + "."

        highlights = self._build_highlights(
            rep_count=rep_count,
            detection_ratio=detection_ratio,
            bar_placement_resolved=bar_placement_resolved,
            bodyweight_kg=bodyweight_kg,
            external_load_kg=external_load_kg,
            kpi_map=kpi_map,
            body_profile=body_profile,
            ground_ref=ground_ref,
            issue_codes=issue_codes,
        )
        corrections = self._build_corrections(issue_codes, kpi_map, ground_ref)
        coach_cue = self._build_coach_cue(issue_codes, kpi_map, bar_placement_resolved)

        return {
            "version": "v2",
            "model": "rule-based-analysis-grounded",
            "overallComment": overall_comment,
            "highlights": highlights,
            "corrections": corrections,
            "coachCue": coach_cue,
        }

    def _build_kpi_map(self, kpis: list[dict]) -> dict[str, float]:
        result: dict[str, float] = {}
        for kpi in kpis:
            key = str(kpi.get("key") or "")
            if not key:
                continue
            try:
                result[key] = float(kpi.get("value") or 0.0)
            except (TypeError, ValueError):
                result[key] = 0.0
        return result

    def _build_highlights(
        self,
        *,
        rep_count: int,
        detection_ratio: float,
        bar_placement_resolved: str,
        bodyweight_kg: float | None,
        external_load_kg: float | None,
        kpi_map: dict[str, float],
        body_profile: dict,
        ground_ref: dict,
        issue_codes: set[str],
    ) -> list[str]:
        highlights: list[str] = []

        if rep_count:
            highlights.append(f"Detected {rep_count} reps with detection ratio {detection_ratio:.2f}.")
        else:
            highlights.append("Rep segmentation did not produce a stable repetition block.")

        if bodyweight_kg is not None or external_load_kg is not None:
            highlights.append(self._format_load_phrase(bodyweight_kg, external_load_kg))

        highlights.append(f"Resolved bar placement mode: {bar_placement_resolved}.")

        femur_to_torso_ratio = self._as_float(body_profile.get("femurToTorsoRatio"))
        if femur_to_torso_ratio is not None:
            highlights.append(f"Body profile femur-to-torso ratio is {femur_to_torso_ratio:.3f}.")

        if "cop_analysis_unavailable" not in issue_codes:
            highlights.append(self._format_cop_summary(kpi_map, ground_ref))

        if "structural_asymmetry_noted" in issue_codes:
            highlights.append("Structural asymmetry was detected and should be separated from movement imbalance.")

        return highlights

    def _build_corrections(
        self,
        issue_codes: set[str],
        kpi_map: dict[str, float],
        ground_ref: dict,
    ) -> list[str]:
        corrections: list[str] = []

        if "no_reps_detected" in issue_codes:
            corrections.append("Check the camera angle and full-body visibility so the squat cycle can be segmented.")
        if "low_detection_ratio" in issue_codes:
            corrections.append("Improve lighting, reduce occlusion, and keep the whole body in frame.")
        if "excessive_trunk_lean" in issue_codes:
            corrections.append("Brace earlier and keep the chest from drifting forward out of the hole.")
        if "movement_load_imbalance" in issue_codes:
            corrections.append("Watch for side-to-side balance shift and keep pressure more even through both feet.")
        if "insufficient_depth" in issue_codes:
            corrections.append("Reach a lower bottom position before reversing the rep.")
        if "depth_inconsistency" in issue_codes:
            corrections.append("Keep the bottom depth consistent from rep to rep.")
        if "tempo_inconsistency" in issue_codes:
            corrections.append("Use a steadier descent and ascent tempo.")
        if "cop_anterior_overload" in issue_codes:
            corrections.append("Keep pressure closer to midfoot instead of drifting forward onto the toes.")
        if "cop_posterior_instability" in issue_codes:
            corrections.append("Avoid rocking back; keep pressure centered instead of drifting toward the heels.")
        if "cop_lateral_asymmetry" in issue_codes:
            corrections.append("Reduce left-right pressure bias at the bottom position.")
        if "bar_forward_of_midfoot" in issue_codes:
            corrections.append("Keep the estimated bar path closer to the midfoot through the full rep.")

        if not corrections:
            ratio = kpi_map.get("knee_hip_moment_ratio", 0.0)
            view_type = str(ground_ref.get("viewType") or "unknown")
            if view_type == "sagittal" and ratio > 1.0:
                corrections.append("Reduce unnecessary forward pressure if you want a less knee-dominant pattern.")
            elif view_type == "sagittal" and ratio and ratio < 1.0:
                corrections.append("Maintain trunk control if you want to avoid an overly hip-dominant pattern.")

        return corrections

    def _build_coach_cue(
        self,
        issue_codes: set[str],
        kpi_map: dict[str, float],
        bar_placement_resolved: str,
    ) -> str:
        if "cop_anterior_overload" in issue_codes or "bar_forward_of_midfoot" in issue_codes:
            return "Midfoot pressure and bar balance first."
        if "movement_load_imbalance" in issue_codes or "cop_lateral_asymmetry" in issue_codes:
            return "Drive evenly through both feet."
        if "excessive_trunk_lean" in issue_codes:
            return "Brace hard and keep the chest from collapsing."
        if "insufficient_depth" in issue_codes:
            return "Sit to a consistent bottom before standing up."

        ratio = kpi_map.get("knee_hip_moment_ratio", 0.0)
        if ratio > 1.5:
            return "Current pattern is knee-dominant; keep the knees and pressure path organized."
        if ratio and ratio < 0.5:
            return "Current pattern is hip-dominant; keep the torso rigid through the bottom."
        if bar_placement_resolved == "low_bar":
            return "Keep the bar stacked over midfoot with a rigid back angle."
        if bar_placement_resolved == "high_bar":
            return "Stay tall while keeping pressure centered over midfoot."
        return "Use the quantified analysis as the source of truth for detailed coaching."

    def _format_cop_summary(self, kpi_map: dict[str, float], ground_ref: dict) -> str:
        view_type = str(ground_ref.get("viewType") or "unknown")
        if view_type == "sagittal":
            return (
                "CoP sagittal metrics: "
                f"bottom {kpi_map.get('cop_bottom_ap', 0.0):.3f}, "
                f"anterior shift {kpi_map.get('cop_anterior_shift', 0.0):.3f}, "
                f"knee/hip moment ratio {kpi_map.get('knee_hip_moment_ratio', 0.0):.3f}."
            )
        if view_type == "frontal":
            return (
                "CoP frontal metrics: "
                f"bottom {kpi_map.get('cop_bottom_ml', 0.0):.3f}, "
                f"consistency {kpi_map.get('cop_ml_consistency', 0.0):.3f}."
            )
        return "CoP directional analysis was not reliable enough for interpretation."

    def _format_load_phrase(
        self,
        bodyweight_kg: float | None,
        external_load_kg: float | None,
    ) -> str | None:
        parts: list[str] = []
        if bodyweight_kg is not None:
            parts.append(f"bodyweight {bodyweight_kg:.1f} kg")
        if external_load_kg is not None:
            parts.append(f"external load {external_load_kg:.1f} kg")
        if not parts:
            return None
        return ", ".join(parts)

    def _as_float(self, value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
