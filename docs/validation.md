# CharUco integration validation

## Source baseline

- Application baseline: `4bc7dc70af8a5e3ecee49502562bd1dfac0af4a1`
- CharUco reference: `3c7d790205685029af3fba74c3876d71b91b1a40`
- Release: `1.1.0`

## Executed checks

- Python 3.12 with OpenCV 4.14.0: all 95 Python tests passed
- Python 3.12 with OpenCV 4.8.1: all 95 Python tests passed
- Both environments passed backend lifecycle smoke tests, static checks and the 14-file core manifest verification through `npm test`
- Renderer DOM checks passed for board controls, parameter persistence, language switching and clearing failed or rejected solver results
- Modified Python modules passed Python 3.8 grammar checks; a Python 3.8 runtime was not available locally
- `git diff --check` passed

The regression suite covers partial CharUco observations, ID correspondence, even-row pattern compatibility, variable corner counts, intrinsic recovery, synthetic hand-eye recovery through the full BA runner, positive-depth pose checks, immutable collection settings, ROS pose freshness and stability, high-rate pose streams, reconnect behavior and concurrent collection operations

Final review identified and resolved four issues: configuration changes racing capture, same-source reconnect being rejected, rejected solver requests retaining displayed results, and high-rate pose history retaining too little time for stability checks

## Validation limits

Real cameras, robots, ROS deployments and physical calibration accuracy have not been validated in this environment

Renderer checks exercised the DOM rather than pixel-level browser screenshots, and a desktop installer was not built

Automatic capture uses host receipt timestamps and requires a stationary robot; it does not establish hardware exposure synchronization for a moving robot

See `charuco-integration.md` for board dimensions, collection requirements and data compatibility
