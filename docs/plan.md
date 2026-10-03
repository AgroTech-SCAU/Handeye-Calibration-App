# CharUco integration and calibration correctness

Base: Handeye-Calibration-App 4bc7dc70af8a5e3ecee49502562bd1dfac0af4a1.
Algorithm reference: yjjy25/vison_sys 3c7d790205685029af3fba74c3876d71b91b1a40.

## Approved scope
Preserve chessboard and Electron/Python architecture. Add configurable CharUco detection,
ID-bound object/image points, partial-view intrinsic and hand-eye sampling and variable-point BA.
Use metres internally and per-corner 2D RMS in pixels. Reject invalid/ambiguous PnP poses.
Lock board, image dimensions and intrinsics within each collection; save immutable snapshots.
Automatic ROS capture must reject stale frames/poses, excessive receipt-time difference and
motion; receipt times are not hardware exposure timestamps. Manual capture requires a stopped robot.
Keep legacy chessboard YAML readable. Record intentional core edits with a local release baseline.

## Implementation plan
- [x] Regression tests: partial/rotated detection, ID validation, PnP depth, RMS, session locking,
  resolution mismatch, variable-point BA recovering known transforms, real bridge CharUco roundtrip.
- [x] Shared calibration_board.py provides BoardSpec, immutable Detection, sample_object_points,
  reprojection_rms and solve_board_pose. Engine consumes these without changing hand-eye equations.
- [x] BA and quality gate reconstruct each frame's points; BA uses bound collection intrinsics.
  Explicit BA failure must be returned to GUI; never report a fallback as successful BA.
- [x] Bridge validates configuration transactionally, locks acquisition settings, tracks frame and
  pose receipt time, checks stability, and previews IDs. Renderer exposes bilingual board controls.
- [x] Update README, USER_GUIDE, resource packaging, integrity manifest, CI and migration notes.
- [x] Run full Python suite, npm lifecycle/static/core checks, renderer smoke when available;
  independent code review; package source ZIP excluding dependencies and temporary data.

## Review focus
Even-row legacy boards, nonfinite/duplicate IDs, external intrinsics replacement, automatic
capture after reconnect, stale result after failed BA and packaged Python import roots.
