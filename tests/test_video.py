import json
import math

import pytest

from scenario_uncertainty import video

K = [[2749.0, 0.0, 1920.0], [0.0, 2749.0, 1080.0], [0.0, 0.0, 1.0]]


def _per_frame():
    # Frame 0 is the reference (no estimate), frame 3 was filled from its neighbours
    return {"inliers": [None, 400, 380, None, 390], "inlier_ratio": [None, 0.9, 0.85, None, 0.88],
            "reproj_err_px": [None, 0.3, 0.4, None, 0.5], "corner_disp_px": [0.0, 0.1, 0.2, 0.3, 0.1],
            "filled": [False, False, False, True, False]}


def _document():
    calib = video.calibration_section("calib.json", (3840, 2160), (3840, 2160), K, [0.1, -0.2, 0, 0, 0.05],
                                      new_k=K, roi=(19, 16, 3802, 2129), alpha=1, rms_px=0.57, n_images=40)
    stab = video.stabilization_section(_per_frame(), reference_frame=0, transform="homography", detector="sift",
                                       smoothing={"type": "gaussian", "sigma_frames": 3}, failed=0)
    return video.build("VIDr_x_D.mp4", tool="vidrectify/2.3.3", frame_index=video.frame_index(5),
                       calibration=calib, stabilization=stab)


def test_summary_counts_and_rms():
    summary = _document()["stabilization"]["summary"]
    assert summary["filled"]["value"] == 1
    assert summary["failed"]["value"] == 0
    assert summary["reproj_err"]["value"] == pytest.approx(math.sqrt((0.09 + 0.16 + 0.25) / 3))
    assert summary["reproj_err"]["n"] == 3


def test_document_validates_against_schema():
    video.validate(_document())


def test_write_read_round_trip(tmp_path):
    path = video.sidecar_path(tmp_path / "VIDr_x_D.mp4")
    assert path.name == "VIDr_x_D.quality.json"
    video.write(path, _document())
    assert video.read(path) == json.loads(json.dumps(_document()))
    assert not list(tmp_path.glob("*.tmp"))


def test_unknown_version_is_ignored_with_warning(tmp_path):
    path = tmp_path / "x.quality.json"
    path.write_text(json.dumps({"schema": "scenario-uncertainty/video/2"}))
    with pytest.warns(UserWarning, match="unsupported schema"):
        assert video.read(path) is None
    assert video.read(tmp_path / "missing.quality.json") is None


def test_mismatched_per_frame_lengths_are_rejected():
    per_frame = _per_frame()
    per_frame["filled"] = per_frame["filled"][:-1]
    with pytest.raises(ValueError, match="differ in length"):
        video.stabilization_section(per_frame, reference_frame=0, transform="homography", detector="sift",
                                    smoothing={}, failed=0)


def test_calibration_flags_scaling_and_unknown_frame_offset():
    calib = video.calibration_section(None, (8064, 4536), (3840, 2160), K, [0.0] * 5)
    assert calib["K_scaled"] is True and calib["rms"] is None
    assert video.frame_index(10, offset_vs_srt=None)["aligned"] is None


def test_written_file_has_normal_permissions(tmp_path):
    import os
    import stat

    umask = os.umask(0o022)
    try:
        path = video.write(tmp_path / "x.quality.json", _document())
    finally:
        os.umask(umask)
    assert stat.S_IMODE(path.stat().st_mode) == 0o644
