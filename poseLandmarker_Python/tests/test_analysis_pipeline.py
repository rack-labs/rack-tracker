from __future__ import annotations

from service.analysis_body_profile import BodyProfile
from service.analysis_cop import GroundRef, ViewInference, extract_cop
from service.analysis_events import detect_events
from service.analysis_features import FeatureSet
from service.analysis_issues import detect_issues
from service.analysis_kpis import KPI, calc_kpis
from service.analysis_preprocess import FrameData, JointData
from service.analysis_reps import RepSegment
from service.analysis_thresholds import build_personal_thresholds


def test_detect_issues_reports_low_detection_ratio() -> None:
    body_profile = _body_profile()
    ground_ref = _ground_ref(view_type="unknown", view_confidence=0.5)
    rep_segments = [_rep_segment()]
    kpis = _base_kpis()
    thresholds = build_personal_thresholds(
        body_profile,
        rep_segments,
        {kpi.key: kpi.value for kpi in kpis},
        ground_ref,
    )

    issues = detect_issues(
        rep_segments,
        kpis,
        body_profile,
        ground_ref,
        {"detectionRatio": 0.75},
        thresholds,
    )

    assert "low_detection_ratio" in {issue.code for issue in issues}


def test_detect_events_emits_pose_lost_and_recovered_with_rep_events() -> None:
    frames_raw = [
        {"frameIndex": 0, "timestampMs": 0.0, "poseDetected": True},
        {"frameIndex": 1, "timestampMs": 100.0, "poseDetected": False},
        {"frameIndex": 2, "timestampMs": 200.0, "poseDetected": False},
        {"frameIndex": 3, "timestampMs": 300.0, "poseDetected": True},
        {"frameIndex": 4, "timestampMs": 400.0, "poseDetected": True},
    ]
    rep_segments = [_rep_segment(start_ms=50.0, bottom_ms=200.0, end_ms=450.0)]

    events = detect_events(frames_raw, rep_segments)

    event_types = [event.type for event in events]
    assert "pose_lost" in event_types
    assert "pose_recovered" in event_types
    assert "rep_start" in event_types
    assert "rep_bottom" in event_types
    assert "rep_end" in event_types

    recovered = next(event for event in events if event.type == "pose_recovered")
    assert recovered.rep_index == 1
    assert recovered.metadata["missedFrameCount"] == 2
    assert recovered.metadata["lostDurationMs"] == 100.0


def test_extract_cop_nulls_bar_metrics_when_bar_confidence_low() -> None:
    frames = [_usable_frame(0.0), _usable_frame(100.0)]
    features = FeatureSet(
        timestamps_ms=[0.0, 100.0],
        joint_angles={},
        joint_velocities={},
        hip_heights=[0.5, 0.52],
        bar_path_x=[0.62, 0.64],
        load_ratios={},
        bar_placement_input="auto",
        bar_placement_resolved="high_bar",
        body_com_x=[0.5, 0.51],
        body_com_y=[0.4, 0.41],
        com_x=[0.5, 0.51],
        com_y=[0.4, 0.41],
        moment_arms={
            "left_ankle": [None, None],
            "right_ankle": [None, None],
            "left_knee": [None, None],
            "right_knee": [None, None],
            "left_hip": [None, None],
            "right_hip": [None, None],
        },
        bar_over_midfoot=[None, None],
        bar_y=[0.2, 0.2],
        bar_confidence=[0.4, 0.45],
        bar_com_offset=[0.12, 0.13],
    )

    ground_ref, updated = extract_cop(
        frames,
        features,
        ViewInference("sagittal", 0.9, {}),
        bodyweight_kg=100.0,
        external_load_kg=80.0,
    )

    assert ground_ref.view_type == "sagittal"
    assert updated.bar_over_midfoot == [None, None]
    assert updated.bar_com_offset == [None, None]
    assert updated.com_x == [0.5, 0.51]


def test_calc_kpis_cop_anterior_shift_uses_rep_descent_only() -> None:
    features = FeatureSet(
        timestamps_ms=[0.0, 100.0, 200.0, 300.0, 400.0],
        joint_angles={
            "trunk_lean_angle": [22.0, 24.0, 28.0, 24.0, 20.0],
        },
        joint_velocities={},
        hip_heights=[0.2, 0.3, 0.45, 0.3, 0.2],
        bar_path_x=[0.5, 0.5, 0.5, 0.5, 0.5],
        load_ratios={"load_ratio_knee": [0.02, 0.02, 0.02, 0.02, 0.02]},
        body_com_x=[0.5] * 5,
        body_com_y=[0.4] * 5,
        com_x=[0.5] * 5,
        com_y=[0.4] * 5,
        cop_ap_normalized=[0.1, 0.2, 0.3, 0.5, 0.0],
        cop_ml_normalized=[None] * 5,
        moment_arms={
            "left_ankle": [0.1] * 5,
            "right_ankle": [0.1] * 5,
            "left_knee": [0.2] * 5,
            "right_knee": [0.2] * 5,
            "left_hip": [0.3] * 5,
            "right_hip": [0.3] * 5,
        },
        bar_over_midfoot=[0.01] * 5,
        bar_y=[0.2] * 5,
        bar_confidence=[0.9] * 5,
        bar_com_offset=[0.01] * 5,
    )
    kpis = calc_kpis(
        features,
        [_rep_segment(start_ms=0.0, bottom_ms=200.0, end_ms=400.0)],
        _body_profile(),
        _ground_ref(view_type="sagittal", view_confidence=0.9),
    )

    kpi_map = {kpi.key: kpi.value for kpi in kpis}

    assert abs(kpi_map["cop_anterior_shift"] - 0.2) < 1e-9


def test_personal_thresholds_change_issue_decision() -> None:
    rep_segments = [_rep_segment(depth_angle_deg=100.0)]
    ground_ref = _ground_ref(view_type="unknown", view_confidence=0.5)
    kpis = _base_kpis()
    kpi_map = {kpi.key: kpi.value for kpi in kpis}

    short_femur_thresholds = build_personal_thresholds(
        _body_profile(femur_to_torso_ratio=0.76),
        rep_segments,
        kpi_map,
        ground_ref,
    )
    long_femur_thresholds = build_personal_thresholds(
        _body_profile(femur_to_torso_ratio=0.95),
        rep_segments,
        kpi_map,
        ground_ref,
    )

    short_femur_issues = detect_issues(
        rep_segments,
        kpis,
        _body_profile(femur_to_torso_ratio=0.76),
        ground_ref,
        {"detectionRatio": 0.95},
        short_femur_thresholds,
    )
    long_femur_issues = detect_issues(
        rep_segments,
        kpis,
        _body_profile(femur_to_torso_ratio=0.95),
        ground_ref,
        {"detectionRatio": 0.95},
        long_femur_thresholds,
    )

    assert "excessive_trunk_lean" in {issue.code for issue in short_femur_issues}
    assert "excessive_trunk_lean" not in {issue.code for issue in long_femur_issues}


def _base_kpis() -> list[KPI]:
    return [
        KPI("trunk_lean_excess", "", 9.0, "", ""),
        KPI("avg_load_ratio_knee", "", 0.05, "", ""),
        KPI("avg_depth_angle", "", 101.0, "", ""),
        KPI("depth_consistency", "", 0.9, "", ""),
        KPI("tempo_consistency", "", 0.9, "", ""),
        KPI("cop_bottom_ap", "", 0.0, "", ""),
        KPI("cop_bottom_ml", "", 0.0, "", ""),
        KPI("cop_ap_consistency", "", 0.9, "", ""),
        KPI("cop_ml_consistency", "", 0.9, "", ""),
        KPI("knee_hip_moment_ratio", "", 1.0, "", ""),
        KPI("bar_midfoot_offset", "", 0.01, "", ""),
    ]


def _body_profile(femur_to_torso_ratio: float = 0.8) -> BodyProfile:
    return BodyProfile(
        left_femur_len=0.4,
        right_femur_len=0.4,
        left_tibia_len=0.35,
        right_tibia_len=0.35,
        torso_len=0.5,
        left_upper_arm_len=0.25,
        right_upper_arm_len=0.25,
        femur_to_torso_ratio=femur_to_torso_ratio,
        tibia_to_femur_ratio=0.875,
        limb_asymmetry={"femur": 0.0, "tibia": 0.0, "upperArm": 0.0},
        joint_angle_baseline_deg={"knee": 0.0, "hip": 0.0},
        sample_frame_count=10,
    )


def _ground_ref(view_type: str = "unknown", view_confidence: float = 0.0) -> GroundRef:
    return GroundRef(
        ground_y=1.0,
        mid_foot_x=0.5,
        foot_width=0.2,
        sagittal_foot_length=0.1,
        left_foot_vec=(0.05, 0.0),
        right_foot_vec=(0.05, 0.0),
        sample_frame_count=5,
        view_type=view_type,
        view_confidence=view_confidence,
        bar_placement_input="auto",
        bar_placement_resolved="high_bar",
        bodyweight_kg=100.0,
        external_load_kg=80.0,
        total_system_mass_kg=180.0,
    )


def _rep_segment(
    start_ms: float = 0.0,
    bottom_ms: float = 200.0,
    end_ms: float = 500.0,
    depth_angle_deg: float = 100.0,
) -> RepSegment:
    return RepSegment(
        rep_index=1,
        start_ms=start_ms,
        end_ms=end_ms,
        bottom_ms=bottom_ms,
        phase_eccentric_ms=200.0,
        phase_concentric_ms=300.0,
        depth_angle_deg=depth_angle_deg,
    )


def _usable_frame(timestamp_ms: float) -> FrameData:
    joints = {
        "left_ankle": _joint("left_ankle", 0.4, 1.0),
        "right_ankle": _joint("right_ankle", 0.6, 1.0),
        "left_knee": _joint("left_knee", 0.42, 0.75),
        "right_knee": _joint("right_knee", 0.58, 0.75),
        "left_hip": _joint("left_hip", 0.45, 0.5),
        "right_hip": _joint("right_hip", 0.55, 0.5),
        "left_shoulder": _joint("left_shoulder", 0.45, 0.2),
        "right_shoulder": _joint("right_shoulder", 0.55, 0.2),
        "left_heel": _joint("left_heel", 0.36, 1.0),
        "right_heel": _joint("right_heel", 0.56, 1.0),
        "left_foot_index": _joint("left_foot_index", 0.46, 1.0),
        "right_foot_index": _joint("right_foot_index", 0.66, 1.0),
    }
    return FrameData(
        frame_index=int(timestamp_ms // 100.0),
        timestamp_ms=timestamp_ms,
        pose_detected=True,
        joints=joints,
        is_usable=True,
    )


def _joint(name: str, x: float, y: float) -> JointData:
    return JointData(
        name=name,
        x=x,
        y=y,
        z=0.0,
        visibility=0.99,
        presence=0.99,
        is_reliable=True,
    )
