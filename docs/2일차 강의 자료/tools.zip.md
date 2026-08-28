<!--
원본 파일: 2일차 강의 자료/tools.zip
원본 형식: ZIP 아카이브 (dogfight_dashboard + web_log_viewer 소스 코드 묶음)
변환 방식: 아카이브 내 텍스트 소스 파일을 하나도 빠짐없이 코드펜스로 그대로 수록 (verbatim)
          바이너리(.pyc), 미니파이 벤더 라이브러리(three.module.min.js), 서드파티 벤더(OrbitControls.js)는
          전문 수록 대신 파일 목록에만 표기 (사용자 콘텐츠가 아닌 제3자 라이브러리·컴파일 산출물)
변환일: 2026-07-14 · 원칙: 요약·의역 없이 있는 그대로 (verbatim)
-->

# tools.zip (대시보드 · 웹 로그 뷰어 소스 묶음)

> 이 파일은 `2일차 강의 자료/tools.zip` 아카이브를 텍스트로 펼친 것입니다. 아카이브에 담긴 **모든 프로젝트 소스 파일의 전체 내용**을 코드펜스로 그대로 수록했습니다. 컴파일 산출물(`.pyc`), 미니파이/서드파티 벤더 라이브러리(`three.module.min.js`, `OrbitControls.js`)는 사용자 콘텐츠가 아니므로 아래 파일 목록에만 표기하고 전문은 생략했습니다.

## 아카이브 파일 목록 (전체)

| 경로 | 크기(bytes) | 본문 수록 |
| --- | --- | --- |
| `dogfight_dashboard/__init__.py` | 58 | ✅ 전문 수록 |
| `dogfight_dashboard/__pycache__/__init__.cpython-311.pyc` | 257 | — (목록만) |
| `dogfight_dashboard/__pycache__/server.cpython-311.pyc` | 14931 | — (목록만) |
| `dogfight_dashboard/__pycache__/training_data.cpython-311.pyc` | 11342 | — (목록만) |
| `dogfight_dashboard/README.md` | 1178 | ✅ 전문 수록 |
| `dogfight_dashboard/server.py` | 9141 | ✅ 전문 수록 |
| `dogfight_dashboard/static/app.js` | 2100 | ✅ 전문 수록 |
| `dogfight_dashboard/static/index.html` | 4978 | ✅ 전문 수록 |
| `dogfight_dashboard/static/replay.js` | 23692 | ✅ 전문 수록 |
| `dogfight_dashboard/static/style.css` | 8808 | ✅ 전문 수록 |
| `dogfight_dashboard/static/training.js` | 18958 | ✅ 전문 수록 |
| `dogfight_dashboard/static/vendor/OrbitControls.js` | 32266 | — (목록만) |
| `dogfight_dashboard/static/vendor/three.module.min.js` | 674422 | — (목록만) |
| `dogfight_dashboard/static/vendor/THREE_LICENSE.txt` | 1081 | ✅ 전문 수록 |
| `dogfight_dashboard/training_data.py` | 6319 | ✅ 전문 수록 |
| `web_log_viewer/__init__.py` | 60 | ✅ 전문 수록 |
| `web_log_viewer/__pycache__/__init__.cpython-311.pyc` | 255 | — (목록만) |
| `web_log_viewer/__pycache__/log_data.cpython-311.pyc` | 31642 | — (목록만) |
| `web_log_viewer/__pycache__/server.cpython-311.pyc` | 15969 | — (목록만) |
| `web_log_viewer/log_data.py` | 18732 | ✅ 전문 수록 |
| `web_log_viewer/README.md` | 1013 | ✅ 전문 수록 |
| `web_log_viewer/server.py` | 9250 | ✅ 전문 수록 |
| `web_log_viewer/static/app.js` | 23657 | ✅ 전문 수록 |
| `web_log_viewer/static/index.html` | 2879 | ✅ 전문 수록 |
| `web_log_viewer/static/style.css` | 3947 | ✅ 전문 수록 |
| `web_log_viewer/static/vendor/OrbitControls.js` | 32266 | — (목록만) |
| `web_log_viewer/static/vendor/three.module.min.js` | 674422 | — (목록만) |
| `web_log_viewer/static/vendor/THREE_LICENSE.txt` | 1081 | ✅ 전문 수록 |
| `web_log_viewer/tests/__pycache__/test_log_data.cpython-311.pyc` | 3659 | — (목록만) |
| `web_log_viewer/tests/test_log_data.py` | 1584 | ✅ 전문 수록 |

---

## 소스 파일 전문 (verbatim)

### `dogfight_dashboard/__init__.py`

```python
"""Unified DogFightEnv training and replay dashboard."""
```

### `dogfight_dashboard/README.md`

````markdown
# DogFight Unified Dashboard

Local tabbed dashboard for DogFightEnv training metrics and Tacview CSV replay.

## Run

From `DogFightEnv/MyTrainEnv` or `DogFightEnv/Release`:

```powershell
C:\Users\USER\anaconda3\envs\aip\python.exe tools\dashboard.py `
  --training-logdir artifacts\dashboard `
  --replay-logdir logs `
  --port 7860
```

Then open:

```text
http://127.0.0.1:7860
```

## Tabs

- `Training`: scalar charts from `metrics.jsonl` and run `config.json`.
- `Replay`: Three.js/WebGL playback for Blue/Red Tacview CSV pairs.

## Compatibility

- `tools/training_dashboard/server.py --logdir artifacts/dashboard` still works
  and opens the `Training` tab.
- `tools/web_log_viewer.py --logdir <csv-dir>` still works and opens the
  `Replay` tab.
- The old PyVista viewer has been removed from active code paths.

## 판단 근거

- Training metrics and replay logs are both read-only local artifacts, so one
  HTTP server can safely serve both.
- API paths are namespaced under `/api/training/*` and `/api/replay/*` to avoid
  endpoint collisions.
- Keeping compatibility wrappers reduces command churn while making
  `tools/dashboard.py` the preferred entrypoint.
````

### `dogfight_dashboard/server.py`

```python
"""Unified HTTP server for DogFightEnv training and replay dashboards."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

try:
    from .training_data import MetricsReader
except ImportError:  # pragma: no cover - direct script execution.
    from training_data import MetricsReader  # type: ignore


PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
TOOLS_DIR = PACKAGE_DIR.parent
DEFAULT_ENV_ROOT = TOOLS_DIR.parent / "MyTrainEnv"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from web_log_viewer.log_data import (  # noqa: E402
    DEFAULT_WEZ_ANGLE_DEG,
    DEFAULT_WEZ_MIN_RANGE_M,
    DEFAULT_WEZ_RANGE_M,
)
from web_log_viewer.server import ViewerRepository  # noqa: E402


class DashboardRepository:
    """Bundle training metrics and replay log repositories."""

    def __init__(
        self,
        env_root: Path,
        training_logdir: Path | None,
        replay_logdir: Path | None,
        mesh_path: Path | None,
        default_tab: str,
    ) -> None:
        self.env_root = env_root.resolve()
        self.training_logdir = (
            training_logdir or self.env_root / "artifacts" / "dashboard"
        ).resolve()
        self.training_logdir.mkdir(parents=True, exist_ok=True)
        self.metrics = MetricsReader(self.training_logdir)
        self.replay = ViewerRepository(
            env_root=self.env_root,
            logdir=replay_logdir,
            mesh_path=mesh_path,
        )
        self.default_tab = default_tab if default_tab in {"training", "replay"} else "training"


def make_handler(repository: DashboardRepository):
    """Create a request handler bound to dashboard repositories."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            if path.startswith("/api/"):
                self._handle_api(path, query)
                return

            if path == "/":
                path = "/index.html"
            file_path = (STATIC_DIR / path.lstrip("/")).resolve()
            if not _is_relative_to(file_path, STATIC_DIR) or not file_path.is_file():
                self.send_error(404)
                return
            body = file_path.read_bytes()
            mime, _ = mimetypes.guess_type(str(file_path))
            self.send_response(200)
            self.send_header("Content-Type", mime or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _handle_api(self, path: str, query: dict) -> None:
            try:
                if path == "/api/app/config":
                    self._json(
                        {
                            "envRoot": str(repository.env_root),
                            "trainingLogdir": str(repository.training_logdir),
                            "replayLogdir": str(repository.replay.logdir),
                            "mesh": str(repository.replay.mesh_path),
                            "defaultTab": repository.default_tab,
                        }
                    )
                elif path == "/api/training/runs":
                    self._json({"runs": repository.metrics.list_runs()})
                elif path == "/api/training/metrics":
                    run = _query_value(query, "run")
                    since = int(_query_value(query, "since_step", "0"))
                    smooth = int(_query_value(query, "smooth", "1"))
                    self._json(repository.metrics.read_metrics(run, since, smooth))
                elif path == "/api/training/latest":
                    self._json(repository.metrics.get_latest(_query_value(query, "run")))
                elif path == "/api/training/config":
                    self._json(repository.metrics.get_config(_query_value(query, "run")))
                elif path == "/api/replay/logs":
                    self._json({"logs": repository.replay.list_logs()})
                elif path == "/api/replay/data":
                    self._json(
                        repository.replay.load_replay(
                            ownship=_query_value(query, "ownship"),
                            target=_query_value(query, "target"),
                        )
                    )
                elif path == "/api/replay/mesh/f16":
                    self._json(repository.replay.load_mesh())
                elif path == "/api/replay/config":
                    self._json(
                        {
                            "envRoot": str(repository.replay.env_root),
                            "logdir": str(repository.replay.logdir),
                            "mesh": str(repository.replay.mesh_path),
                            "defaults": {
                                "wezMinRangeM": DEFAULT_WEZ_MIN_RANGE_M,
                                "wezRangeM": DEFAULT_WEZ_RANGE_M,
                                "wezAngleDeg": DEFAULT_WEZ_ANGLE_DEG,
                            },
                        }
                    )
                else:
                    self._json({"error": "not found"}, status=404)
            except Exception as exc:
                self._json({"error": str(exc)}, status=400)

        def _json(self, data: dict, status: int = 200) -> None:
            body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _query_value(query: dict, key: str, default: str | None = None) -> str:
    value = (query.get(key) or [default])[0]
    if value is None or value == "":
        raise ValueError(f"{key} parameter required")
    return str(value)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DogFight unified dashboard")
    parser.add_argument(
        "--env-root",
        default=str(DEFAULT_ENV_ROOT),
        help="DogFightEnv environment root containing artifacts/, logs/, and assets/.",
    )
    parser.add_argument(
        "--training-logdir",
        default=None,
        help="Training metrics directory. Defaults to <env-root>/artifacts/dashboard.",
    )
    parser.add_argument(
        "--logdir",
        "--replay-logdir",
        dest="replay_logdir",
        default=None,
        help="Replay CSV directory. Defaults to <env-root>/logs.",
    )
    parser.add_argument(
        "--mesh",
        default=None,
        help="F-16 OBJ mesh path. Defaults to <env-root>/assets/meshes/f16.",
    )
    parser.add_argument(
        "--default-tab",
        choices=["training", "replay"],
        default="training",
        help="Initial tab opened by the browser UI.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repository = DashboardRepository(
        env_root=Path(args.env_root).expanduser(),
        training_logdir=(
            Path(args.training_logdir).expanduser() if args.training_logdir else None
        ),
        replay_logdir=Path(args.replay_logdir).expanduser() if args.replay_logdir else None,
        mesh_path=Path(args.mesh).expanduser() if args.mesh else None,
        default_tab=args.default_tab,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(repository))
    first_url = f"http://{args.host}:{args.port}"
    print(f"DogFight dashboard: {first_url}/?tab={repository.default_tab}")
    print(f"Env root:           {repository.env_root}")
    print(f"Training logdir:    {repository.training_logdir}")
    print(f"Replay logdir:      {repository.replay.logdir}")
    print(f"Mesh:               {repository.replay.mesh_path}")
    replay_logs = repository.replay.list_logs()
    if replay_logs:
        first = replay_logs[0]
        query = f"ownship={quote(first['ownship'])}&target={quote(first['target'])}"
        print(f"Latest replay API:  {first_url}/api/replay/data?{query}")
    print("Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
```

### `dogfight_dashboard/static/app.js`

```javascript
import { initTrainingDashboard } from "./training.js";
import { initReplayViewer } from "./replay.js";

const AppState = {
  trainingStarted: false,
  replayStarted: false,
  config: null,
};

const $ = id => document.getElementById(id);

start().catch(error => {
  console.error(error);
  $("app-status").textContent = `Startup failed: ${error.message}`;
});

async function start() {
  bindTabs();
  AppState.config = await fetchJson("/api/app/config");
  const params = new URLSearchParams(window.location.search);
  const initialTab = params.get("tab") || AppState.config.defaultTab || "training";
  await showTab(initialTab === "replay" ? "replay" : "training");
  $("app-status").textContent = formatPaths(AppState.config);
}

function bindTabs() {
  for (const button of document.querySelectorAll(".tab-button")) {
    button.addEventListener("click", () => {
      showTab(button.dataset.tab).catch(error => {
        console.error(error);
        $("app-status").textContent = `Tab failed: ${error.message}`;
      });
    });
  }
}

async function showTab(tab) {
  for (const button of document.querySelectorAll(".tab-button")) {
    button.classList.toggle("active", button.dataset.tab === tab);
  }
  $("training-panel").classList.toggle("active", tab === "training");
  $("replay-panel").classList.toggle("active", tab === "replay");
  window.history.replaceState(null, "", `?tab=${tab}`);

  if (tab === "training" && !AppState.trainingStarted) {
    initTrainingDashboard({ apiBase: "/api/training" });
    AppState.trainingStarted = true;
  }
  if (tab === "replay" && !AppState.replayStarted) {
    await initReplayViewer({ apiBase: "/api/replay" });
    AppState.replayStarted = true;
  }
  window.dispatchEvent(new Event("resize"));
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

function formatPaths(config) {
  return `Training: ${config.trainingLogdir} | Replay: ${config.replayLogdir}`;
}
```

### `dogfight_dashboard/static/index.html`

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DogFight Dashboard</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <header class="app-header">
    <div class="brand">DogFight Dashboard</div>
    <nav class="tabs" aria-label="Dashboard tabs">
      <button id="tab-training" class="tab-button active" type="button" data-tab="training">Training</button>
      <button id="tab-replay" class="tab-button" type="button" data-tab="replay">Replay</button>
    </nav>
    <span id="app-status" class="app-status">Starting...</span>
  </header>

  <main>
    <section id="training-panel" class="tab-panel active" aria-labelledby="tab-training">
      <header class="training-toolbar">
        <select id="run-select" aria-label="Training run"></select>
        <button id="compare-button" type="button">Compare</button>
        <label class="smooth">
          <span>EMA</span>
          <input id="smooth-slider" type="range" min="1" max="50" value="8">
          <span id="smooth-value">8</span>
        </label>
        <span id="status-text">Connecting...</span>
      </header>

      <section id="cards" class="cards"></section>

      <div class="training-layout">
        <aside class="training-sidebar">
          <div class="section-title">Runs</div>
          <div id="run-list" class="run-list"></div>
          <div class="section-title">Config</div>
          <pre id="config-box" class="config-box"></pre>
          <div class="section-title">Metrics</div>
          <div id="metric-box" class="metric-box"></div>
        </aside>
        <main id="chart-grid" class="chart-grid"></main>
      </div>
    </section>

    <section id="replay-panel" class="tab-panel" aria-labelledby="tab-replay">
      <header class="replay-toolbar">
        <select id="log-select" aria-label="Replay log"></select>
        <button id="reload-button" type="button" title="Reload logs">Reload</button>
        <button id="play-button" type="button" title="Play or pause">Pause</button>
        <label class="speed-control">
          <span>Speed</span>
          <input id="speed-slider" type="range" min="0" max="20" step="0.5" value="5">
          <span id="speed-value">5.0x</span>
        </label>
        <span id="replay-status-text">Loading...</span>
      </header>

      <div class="viewer-shell">
        <section class="scene-panel">
          <div id="scene-root" class="scene-root"></div>
          <div id="hud-left" class="hud hud-left"></div>
          <div id="hud-right" class="hud hud-right"></div>
          <div id="hud-bottom" class="hud hud-bottom"></div>
        </section>

        <aside class="side-panel">
          <div class="section-title">Display</div>
          <label class="toggle"><input id="toggle-hud" type="checkbox" checked> HUD</label>
          <label class="toggle"><input id="toggle-sea" type="checkbox" checked> Sea</label>
          <label class="toggle"><input id="toggle-trails" type="checkbox" checked> Trails</label>
          <label class="toggle"><input id="toggle-wez" type="checkbox" checked> WEZ</label>

          <div class="section-title">View</div>
          <div class="camera-mode-group" role="group" aria-label="Camera follow mode">
            <button class="camera-mode-button" type="button" data-camera-mode="blue">Blue</button>
            <button class="camera-mode-button" type="button" data-camera-mode="red">Red</button>
            <button class="camera-mode-button" type="button" data-camera-mode="midpoint">Center</button>
          </div>

          <div class="section-title">Replay</div>
          <input id="timeline" class="timeline" type="range" min="0" max="1" step="0.001" value="0">
          <div class="readout-grid">
            <span>Time</span><strong id="time-readout">0.00s</strong>
            <span>Range</span><strong id="range-readout">n/a</strong>
            <span>Closure</span><strong id="closure-readout">n/a</strong>
            <span>Rel Alt</span><strong id="relalt-readout">n/a</strong>
          </div>

          <div class="section-title">Logs</div>
          <pre id="log-info" class="log-info"></pre>

          <div class="section-title">Debug</div>
          <div class="debug-grid">
            <span>WebGL</span><strong id="debug-webgl">n/a</strong>
            <span>Frames</span><strong id="debug-frames">0</strong>
            <span>Samples</span><strong id="debug-samples">0</strong>
          </div>
        </aside>
      </div>
    </section>
  </main>

  <div id="modal" class="modal" hidden>
    <div class="modal-panel">
      <button id="modal-close" class="modal-close" type="button">x</button>
      <div id="modal-title" class="modal-title"></div>
      <canvas id="modal-canvas"></canvas>
      <div id="modal-legend" class="chart-legend modal-legend"></div>
    </div>
  </div>

  <script type="module" src="/app.js"></script>
</body>
</html>
```

### `dogfight_dashboard/static/replay.js`

```javascript
import * as THREE from "./vendor/three.module.min.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

let API_BASE = "/api/replay";

const COLORS = {
  own: 0x4d8dff,
  target: 0xff5757,
  ownTrail: 0x003b8e,
  targetTrail: 0x9f0d19,
  ownWez: 0x4d8dff,
  targetWez: 0xff6b6b,
  sea: 0x0969a8,
  sky: 0x7fb7d7,
};

const AIRCRAFT_MODEL_YAW_OFFSET_DEG = 180;
const CAMERA_MODES = new Set(["blue", "red", "midpoint"]);

const State = {
  logs: [],
  replay: null,
  mesh: null,
  playing: true,
  speed: 5,
  simTime: 0,
  lastNow: 0,
  framesRendered: 0,
  showHud: true,
  showSea: true,
  showTrails: true,
  showWez: true,
  cameraMode: "midpoint",
};

const Scene = {
  renderer: null,
  scene: null,
  camera: null,
  controls: null,
  root: null,
  aircraftGeometry: null,
  ownship: null,
  target: null,
  sea: null,
  ownTrail: null,
  targetTrail: null,
  ownWez: null,
  targetWez: null,
};

const $ = id => document.getElementById(id);

window.DogFightViewerDebug = {
  webglOk: false,
  framesRendered: 0,
  activeLogPair: null,
  samples: 0,
};

export async function initReplayViewer(options = {}) {
  API_BASE = options.apiBase || API_BASE;
  bindEvents();
  initScene();
  await Promise.all([loadMesh(), refreshLogs()]);
  animate(0);
}

function bindEvents() {
  $("reload-button").addEventListener("click", () => refreshLogs());
  $("play-button").addEventListener("click", () => {
    State.playing = !State.playing;
    $("play-button").textContent = State.playing ? "Pause" : "Play";
  });
  $("log-select").addEventListener("change", event => {
    const index = Number(event.target.value);
    if (Number.isInteger(index) && State.logs[index]) {
      loadReplay(State.logs[index]);
    }
  });
  $("speed-slider").addEventListener("input", event => {
    State.speed = Number(event.target.value);
    $("speed-value").textContent = `${State.speed.toFixed(1)}x`;
  });
  $("timeline").addEventListener("input", event => {
    if (!State.replay) {
      return;
    }
    const ratio = Number(event.target.value);
    State.simTime = lerp(State.replay.startTime, State.replay.endTime, ratio);
    updateFrame();
  });

  bindToggle("toggle-hud", "showHud", updateVisibility);
  bindToggle("toggle-sea", "showSea", updateVisibility);
  bindToggle("toggle-trails", "showTrails", updateVisibility);
  bindToggle("toggle-wez", "showWez", updateVisibility);
  document.querySelectorAll("[data-camera-mode]").forEach(button => {
    button.addEventListener("click", () => setCameraMode(button.dataset.cameraMode));
  });
  updateCameraModeButtons();
  window.addEventListener("resize", resizeRenderer);
}

function bindToggle(id, key, callback) {
  $(id).addEventListener("change", event => {
    State[key] = event.target.checked;
    callback();
  });
}

function setCameraMode(mode) {
  if (!CAMERA_MODES.has(mode)) {
    return;
  }
  State.cameraMode = mode;
  updateCameraModeButtons();
  updateFrame();
}

function updateCameraModeButtons() {
  document.querySelectorAll("[data-camera-mode]").forEach(button => {
    const active = button.dataset.cameraMode === State.cameraMode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

function initScene() {
  Scene.root = $("scene-root");
  Scene.scene = new THREE.Scene();
  Scene.scene.background = new THREE.Color(COLORS.sky);
  Scene.scene.fog = new THREE.Fog(COLORS.sky, 6000, 28000);

  Scene.camera = new THREE.PerspectiveCamera(50, 1, 1, 60000);
  Scene.camera.up.set(0, 0, 1);

  Scene.renderer = new THREE.WebGLRenderer({ antialias: true });
  Scene.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  Scene.renderer.outputColorSpace = THREE.SRGBColorSpace;
  Scene.root.appendChild(Scene.renderer.domElement);
  window.DogFightViewerDebug.webglOk = Boolean(Scene.renderer.getContext());

  Scene.controls = new OrbitControls(Scene.camera, Scene.renderer.domElement);
  Scene.controls.enableDamping = true;
  Scene.controls.dampingFactor = 0.08;
  Scene.controls.screenSpacePanning = false;

  Scene.scene.add(new THREE.AmbientLight(0xffffff, 0.62));
  const sun = new THREE.DirectionalLight(0xffffff, 1.25);
  sun.position.set(0.4, -0.6, 1.0).normalize();
  Scene.scene.add(sun);

  resizeRenderer();
}

async function refreshLogs() {
  setStatus("Loading log list...");
  const data = await apiFetch("/api/logs");
  State.logs = data.logs || [];
  renderLogOptions();
  if (State.logs.length === 0) {
    setStatus("No Blue/Red CSV log pairs found.");
    return;
  }
  await loadReplay(State.logs[0]);
}

function renderLogOptions() {
  const select = $("log-select");
  select.innerHTML = "";
  if (State.logs.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No logs";
    select.appendChild(option);
    return;
  }
  State.logs.forEach((log, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = log.label || log.ownshipName || `Replay ${index + 1}`;
    select.appendChild(option);
  });
  select.value = "0";
}

async function loadMesh() {
  State.mesh = await apiFetch("/api/mesh/f16");
  Scene.aircraftGeometry = buildAircraftGeometry(State.mesh);
}

async function loadReplay(logPair) {
  setStatus("Loading replay...");
  const ownship = encodeURIComponent(logPair.ownship);
  const target = encodeURIComponent(logPair.target);
  State.replay = await apiFetch(`/api/data?ownship=${ownship}&target=${target}`);
  State.simTime = State.replay.startTime;
  State.playing = true;
  $("play-button").textContent = "Pause";
  $("timeline").value = "0";
  window.DogFightViewerDebug.activeLogPair = {
    ownship: State.replay.logs.ownship,
    target: State.replay.logs.target,
  };
  window.DogFightViewerDebug.samples = State.replay.ownship.time.length;
  $("debug-samples").textContent = String(State.replay.ownship.time.length);
  setupReplayScene();
  updateFrame();
  setStatus(`Loaded ${State.replay.logs.ownship}`);
}

function setupReplayScene() {
  clearReplayObjects();
  const replay = State.replay;
  const size = replay.seaSizeM;

  const seaGeometry = new THREE.PlaneGeometry(size, size, 80, 80);
  const positions = seaGeometry.attributes.position;
  for (let i = 0; i < positions.count; i += 1) {
    const x = positions.getX(i);
    const y = positions.getY(i);
    const z = 4 * Math.sin(x / 850) + 2.5 * Math.cos(y / 650);
    positions.setZ(i, THREE.MathUtils.clamp(z, -10, 10));
  }
  positions.needsUpdate = true;
  seaGeometry.computeVertexNormals();
  Scene.sea = new THREE.Mesh(
    seaGeometry,
    new THREE.MeshPhongMaterial({
      color: COLORS.sea,
      transparent: true,
      opacity: 0.86,
      shininess: 22,
      side: THREE.DoubleSide,
    })
  );
  Scene.scene.add(Scene.sea);

  const ownMaterial = new THREE.MeshPhongMaterial({ color: COLORS.own, shininess: 50 });
  const targetMaterial = new THREE.MeshPhongMaterial({
    color: COLORS.target,
    shininess: 50,
  });
  Scene.ownship = new THREE.Mesh(Scene.aircraftGeometry, ownMaterial);
  Scene.target = new THREE.Mesh(Scene.aircraftGeometry, targetMaterial);
  Scene.scene.add(Scene.ownship);
  Scene.scene.add(Scene.target);

  Scene.ownTrail = makeLine(COLORS.ownTrail, 4);
  Scene.targetTrail = makeLine(COLORS.targetTrail, 4);
  Scene.scene.add(Scene.ownTrail);
  Scene.scene.add(Scene.targetTrail);

  Scene.ownWez = makeWezMesh(COLORS.ownWez, 0.14);
  Scene.targetWez = makeWezMesh(COLORS.targetWez, 0.12);
  Scene.scene.add(Scene.ownWez);
  Scene.scene.add(Scene.targetWez);

  setInitialCamera();
  updateVisibility();
}

function clearReplayObjects() {
  for (const key of [
    "ownship",
    "target",
    "sea",
    "ownTrail",
    "targetTrail",
    "ownWez",
    "targetWez",
  ]) {
    const object = Scene[key];
    if (object) {
      Scene.scene.remove(object);
      disposeObject(object);
      Scene[key] = null;
    }
  }
}

function buildAircraftGeometry(mesh) {
  const vertices = [];
  for (const vertex of mesh.vertices) {
    vertices.push(vertex[0], vertex[1], vertex[2]);
  }
  const indices = [];
  for (const triangle of mesh.triangles) {
    indices.push(triangle[0], triangle[1], triangle[2]);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function makeLine(color, width) {
  return new THREE.Line(
    new THREE.BufferGeometry(),
    new THREE.LineBasicMaterial({ color, linewidth: width })
  );
}

function makeWezMesh(color, opacity) {
  return new THREE.Mesh(
    new THREE.BufferGeometry(),
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity,
      side: THREE.DoubleSide,
      depthWrite: false,
      wireframe: false,
    })
  );
}

function updateVisibility() {
  $("hud-left").hidden = !State.showHud;
  $("hud-right").hidden = !State.showHud;
  $("hud-bottom").hidden = !State.showHud;
  if (Scene.sea) {
    Scene.sea.visible = State.showSea;
  }
  if (Scene.ownTrail) {
    Scene.ownTrail.visible = State.showTrails;
  }
  if (Scene.targetTrail) {
    Scene.targetTrail.visible = State.showTrails;
  }
  if (Scene.ownWez) {
    Scene.ownWez.visible = State.showWez;
  }
  if (Scene.targetWez) {
    Scene.targetWez.visible = State.showWez;
  }
}

function setInitialCamera() {
  const replay = State.replay;
  const own = replay.ownship.position[0];
  const target = replay.target.position[0];
  const focal = [
    (own[0] + target[0]) / 2,
    (own[1] + target[1]) / 2,
    (own[2] + target[2]) / 2,
  ];
  const scale = Math.max(
    replay.sceneExtentM,
    replay.defaults.wezRangeM * 2.5,
    1500
  );
  Scene.camera.position.set(
    focal[0] + 0.36 * scale,
    focal[1] - 0.5 * scale,
    focal[2] + 0.28 * scale
  );
  Scene.camera.near = 1;
  Scene.camera.far = Math.max(scale * 8, 10000);
  Scene.camera.updateProjectionMatrix();
  Scene.controls.target.set(focal[0], focal[1], focal[2]);
  Scene.controls.update();
}

function animate(now) {
  requestAnimationFrame(animate);
  const dt = State.lastNow ? (now - State.lastNow) / 1000 : 0;
  State.lastNow = now;

  if (State.replay && State.playing) {
    State.simTime += dt * State.speed;
    if (State.simTime > State.replay.endTime) {
      State.simTime = State.replay.startTime;
    }
    updateFrame();
  }
  Scene.controls?.update();
  Scene.renderer?.render(Scene.scene, Scene.camera);
  State.framesRendered += 1;
  window.DogFightViewerDebug.framesRendered = State.framesRendered;
  $("debug-frames").textContent = String(State.framesRendered);
}

function updateFrame() {
  const replay = State.replay;
  if (!replay || !Scene.ownship || !Scene.target) {
    return;
  }
  const ownIndex = nearestIndex(replay.ownship.time, State.simTime);
  const targetIndex = nearestIndex(replay.target.time, State.simTime);
  updateAircraft(Scene.ownship, replay.ownship, ownIndex);
  updateAircraft(Scene.target, replay.target, targetIndex);
  updateTrail(Scene.ownTrail, replay.ownship, State.simTime);
  updateTrail(Scene.targetTrail, replay.target, State.simTime);
  updateWez(Scene.ownWez, replay.ownship, ownIndex);
  updateWez(Scene.targetWez, replay.target, targetIndex);
  updateHud(ownIndex, targetIndex);
  updateFollowCamera(ownIndex, targetIndex);
  updateTimeline();
}

function updateAircraft(object, track, index) {
  const pos = track.position[index];
  const matrix = aircraftVisualMatrix(
    track.rollDeg[index],
    track.pitchDeg[index],
    track.yawDeg[index]
  );
  const rot = new THREE.Matrix4().set(
    matrix[0][0], matrix[0][1], matrix[0][2], 0,
    matrix[1][0], matrix[1][1], matrix[1][2], 0,
    matrix[2][0], matrix[2][1], matrix[2][2], 0,
    0, 0, 0, 1
  );
  object.position.set(pos[0], pos[1], pos[2]);
  object.quaternion.setFromRotationMatrix(rot);
  object.scale.setScalar(State.replay.aircraftDisplayLengthM);
}

function aircraftVisualMatrix(rollDeg, pitchDeg, yawDeg) {
  const bodyMatrix = attitudeMatrix(rollDeg, pitchDeg, yawDeg);
  if (AIRCRAFT_MODEL_YAW_OFFSET_DEG === 0) {
    return bodyMatrix;
  }
  return matmul3(
    bodyMatrix,
    zRotationMatrix(AIRCRAFT_MODEL_YAW_OFFSET_DEG)
  );
}

function updateFollowCamera(ownIndex, targetIndex) {
  if (!Scene.camera || !Scene.controls) {
    return;
  }
  const focal = cameraFocalPoint(ownIndex, targetIndex);
  const delta = focal.clone().sub(Scene.controls.target);
  if (delta.lengthSq() <= 1e-8) {
    return;
  }
  Scene.camera.position.add(delta);
  Scene.controls.target.copy(focal);
  Scene.controls.update();
}

function cameraFocalPoint(ownIndex, targetIndex) {
  const replay = State.replay;
  const own = replay.ownship.position[ownIndex];
  const target = replay.target.position[targetIndex];
  if (State.cameraMode === "blue") {
    return new THREE.Vector3(own[0], own[1], own[2]);
  }
  if (State.cameraMode === "red") {
    return new THREE.Vector3(target[0], target[1], target[2]);
  }
  return new THREE.Vector3(
    (own[0] + target[0]) / 2,
    (own[1] + target[1]) / 2,
    (own[2] + target[2]) / 2
  );
}

function updateTrail(line, track, simTime) {
  if (!line) {
    return;
  }
  const startTime = simTime - State.replay.defaults.trailSeconds;
  const start = lowerBound(track.time, startTime);
  const end = upperBound(track.time, simTime);
  const points = [];
  for (let i = start; i < end; i += 1) {
    const p = track.position[i];
    points.push(new THREE.Vector3(p[0], p[1], p[2]));
  }
  line.geometry.dispose();
  line.geometry = new THREE.BufferGeometry().setFromPoints(points);
}

function updateWez(mesh, track, index) {
  if (!mesh) {
    return;
  }
  const pos = track.position[index];
  const forward = forwardVector(track.yawDeg[index], track.pitchDeg[index]);
  mesh.geometry.dispose();
  mesh.geometry = buildWezGeometry(
    new THREE.Vector3(pos[0], pos[1], pos[2]),
    new THREE.Vector3(forward[0], forward[1], forward[2]),
    State.replay.defaults.wezMinRangeM,
    State.replay.defaults.wezRangeM,
    State.replay.defaults.wezAngleDeg
  );
}

function buildWezGeometry(nose, direction, minRange, maxRange, angleDeg) {
  const dir = direction.lengthSq() > 0 ? direction.clone().normalize() : new THREE.Vector3(1, 0, 0);
  const nearRange = Math.max(0, minRange);
  const farRange = Math.max(nearRange, maxRange);
  const halfAngle = THREE.MathUtils.degToRad(angleDeg / 2);
  const nearRadius = nearRange * Math.tan(halfAngle);
  const farRadius = farRange * Math.tan(halfAngle);
  let ref = new THREE.Vector3(0, 0, 1);
  if (Math.abs(dir.dot(ref)) > 0.98) {
    ref = new THREE.Vector3(0, 1, 0);
  }
  const side = new THREE.Vector3().crossVectors(dir, ref).normalize();
  const up = new THREE.Vector3().crossVectors(side, dir).normalize();
  const resolution = 48;
  const nearCenter = nose.clone().addScaledVector(dir, nearRange);
  const farCenter = nose.clone().addScaledVector(dir, farRange);
  const vertices = [];
  const indices = [];

  for (let step = 0; step < resolution; step += 1) {
    const theta = (2 * Math.PI * step) / resolution;
    const radial = side.clone().multiplyScalar(Math.cos(theta))
      .add(up.clone().multiplyScalar(Math.sin(theta)));
    const nearPoint = nearCenter.clone().addScaledVector(radial, nearRadius);
    const farPoint = farCenter.clone().addScaledVector(radial, farRadius);
    vertices.push(nearPoint.x, nearPoint.y, nearPoint.z);
    vertices.push(farPoint.x, farPoint.y, farPoint.z);
  }

  for (let step = 0; step < resolution; step += 1) {
    const next = (step + 1) % resolution;
    const nearA = step * 2;
    const farA = nearA + 1;
    const nearB = next * 2;
    const farB = nearB + 1;
    indices.push(nearA, nearB, farB, nearA, farB, farA);
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function updateHud(ownIndex, targetIndex) {
  const replay = State.replay;
  const own = replay.ownship;
  const target = replay.target;
  const ownPos = own.position[ownIndex];
  const targetPos = target.position[targetIndex];
  const relative = sub(targetPos, ownPos);
  const distance = norm(relative);
  const ownForward = forwardVector(own.yawDeg[ownIndex], own.pitchDeg[ownIndex]);
  const targetForward = forwardVector(target.yawDeg[targetIndex], target.pitchDeg[targetIndex]);
  const ownAta = angleBetweenDeg(ownForward, relative);
  const targetAta = angleBetweenDeg(targetForward, scale(relative, -1));
  const ownAa = angleBetweenDeg(targetForward, scale(relative, -1));
  const ownSpeed = speedAt(own, ownIndex);
  const targetSpeed = speedAt(target, targetIndex);
  const closure = distance > 0
    ? -dot(relative, sub(velocityAt(target, targetIndex), velocityAt(own, ownIndex))) / distance
    : 0;
  const ownWez = inWez(distance, ownAta);
  const targetWez = inWez(distance, targetAta);
  const state = State.playing ? "PLAY" : "PAUSE";

  $("hud-left").textContent =
    `${state}  t=${State.simTime.toFixed(2)}s  x${State.speed.toFixed(1)}\n` +
    `Own  alt=${fmt0(ownPos[2])}m  v=${fmt1(ownSpeed)}m/s  hp=${fmtHealth(own.health[ownIndex])}\n` +
    `Tgt  alt=${fmt0(targetPos[2])}m  v=${fmt1(targetSpeed)}m/s  hp=${fmtHealth(target.health[targetIndex])}`;
  $("hud-right").textContent =
    `Range      ${fmt0(distance)} m\n` +
    `Closure    ${fmt1(closure)} m/s\n` +
    `Rel Alt    ${fmt0(targetPos[2] - ownPos[2])} m\n` +
    `Own ATA    ${fmt1(ownAta)} deg\n` +
    `Target AA  ${fmt1(ownAa)} deg\n` +
    `Own WEZ    ${ownWez ? "IN" : "out"}\n` +
    `Threat     ${targetWez ? "IN" : "out"}`;
  $("hud-right").style.color = targetWez ? "#ff6b6b" : ownWez ? "#f3b34c" : "#eef3f7";
  $("hud-bottom").textContent =
    `${replay.logs.ownship}\n${replay.logs.target}\nEnd: ${replay.endCondition}`;

  $("time-readout").textContent = `${State.simTime.toFixed(2)}s`;
  $("range-readout").textContent = `${fmt0(distance)} m`;
  $("closure-readout").textContent = `${fmt1(closure)} m/s`;
  $("relalt-readout").textContent = `${fmt0(targetPos[2] - ownPos[2])} m`;
  $("log-info").textContent = JSON.stringify({
    ownship: replay.logs.ownship,
    target: replay.logs.target,
    metadata: replay.logs.metadata,
    end: replay.endCondition,
  }, null, 2);
}

function updateTimeline() {
  const replay = State.replay;
  const denom = replay.endTime - replay.startTime;
  const ratio = denom > 0 ? (State.simTime - replay.startTime) / denom : 0;
  $("timeline").value = String(THREE.MathUtils.clamp(ratio, 0, 1));
}

function resizeRenderer() {
  if (!Scene.renderer || !Scene.camera || !Scene.root) {
    return;
  }
  const rect = Scene.root.getBoundingClientRect();
  const width = Math.max(1, Math.floor(rect.width));
  const height = Math.max(1, Math.floor(rect.height));
  Scene.renderer.setSize(width, height, false);
  Scene.camera.aspect = width / height;
  Scene.camera.updateProjectionMatrix();
  $("debug-webgl").textContent = window.DogFightViewerDebug.webglOk ? "ok" : "fail";
}

async function apiFetch(path) {
  const response = await fetch(path.replace(/^\/api/, API_BASE), { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

function setStatus(message) {
  $("replay-status-text").textContent = message;
}

function disposeObject(object) {
  object.traverse?.(child => {
    child.geometry?.dispose?.();
    if (Array.isArray(child.material)) {
      child.material.forEach(material => material.dispose?.());
    } else {
      child.material?.dispose?.();
    }
  });
}

function nearestIndex(times, value) {
  return Math.max(0, Math.min(upperBound(times, value) - 1, times.length - 1));
}

function lowerBound(values, target) {
  let low = 0;
  let high = values.length;
  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (values[mid] < target) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  return low;
}

function upperBound(values, target) {
  let low = 0;
  let high = values.length;
  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (values[mid] <= target) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  return low;
}

function attitudeMatrix(rollDeg, pitchDeg, yawDeg) {
  const roll = THREE.MathUtils.degToRad(rollDeg);
  const pitch = THREE.MathUtils.degToRad(pitchDeg);
  const yaw = THREE.MathUtils.degToRad(90 - yawDeg);
  const cr = Math.cos(roll);
  const sr = Math.sin(roll);
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const rotX = [[1, 0, 0], [0, cr, -sr], [0, sr, cr]];
  const rotY = [[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]];
  const rotZ = [[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]];
  return matmul3(matmul3(rotZ, rotY), rotX);
}

function zRotationMatrix(deg) {
  const rad = THREE.MathUtils.degToRad(deg);
  const c = Math.cos(rad);
  const s = Math.sin(rad);
  return [[c, -s, 0], [s, c, 0], [0, 0, 1]];
}

function matmul3(a, b) {
  const out = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  for (let row = 0; row < 3; row += 1) {
    for (let col = 0; col < 3; col += 1) {
      out[row][col] = a[row][0] * b[0][col] +
        a[row][1] * b[1][col] +
        a[row][2] * b[2][col];
    }
  }
  return out;
}

function forwardVector(yawDeg, pitchDeg) {
  const matrix = attitudeMatrix(0, pitchDeg, yawDeg);
  const direction = [matrix[0][0], matrix[1][0], matrix[2][0]];
  const length = norm(direction);
  return length > 0 ? scale(direction, 1 / length) : [1, 0, 0];
}

function speedAt(track, index) {
  if (track.time.length < 2) {
    return 0;
  }
  const prev = Math.max(0, index - 1);
  const next = Math.min(track.time.length - 1, index + 1);
  const dt = track.time[next] - track.time[prev];
  return dt > 0 ? norm(sub(track.position[next], track.position[prev])) / dt : 0;
}

function velocityAt(track, index) {
  if (track.time.length < 2) {
    return [0, 0, 0];
  }
  const prev = Math.max(0, index - 1);
  const next = Math.min(track.time.length - 1, index + 1);
  const dt = track.time[next] - track.time[prev];
  return dt > 0 ? scale(sub(track.position[next], track.position[prev]), 1 / dt) : [0, 0, 0];
}

function angleBetweenDeg(first, second) {
  const firstNorm = norm(first);
  const secondNorm = norm(second);
  if (firstNorm <= 0 || secondNorm <= 0) {
    return 0;
  }
  const cosine = THREE.MathUtils.clamp(dot(first, second) / (firstNorm * secondNorm), -1, 1);
  return THREE.MathUtils.radToDeg(Math.acos(cosine));
}

function inWez(rangeM, ataDeg) {
  const defs = State.replay.defaults;
  return rangeM >= defs.wezMinRangeM &&
    rangeM <= defs.wezRangeM &&
    ataDeg <= Math.max(0, defs.wezAngleDeg / 2);
}

function sub(first, second) {
  return [first[0] - second[0], first[1] - second[1], first[2] - second[2]];
}

function scale(vector, scalar) {
  return [vector[0] * scalar, vector[1] * scalar, vector[2] * scalar];
}

function dot(first, second) {
  return first[0] * second[0] + first[1] * second[1] + first[2] * second[2];
}

function norm(vector) {
  return Math.sqrt(dot(vector, vector));
}

function lerp(start, end, ratio) {
  return start + (end - start) * ratio;
}

function fmt0(value) {
  return Number.isFinite(value) ? value.toFixed(0).padStart(6, " ") : "n/a";
}

function fmt1(value) {
  return Number.isFinite(value) ? value.toFixed(1).padStart(6, " ") : "n/a";
}

function fmtHealth(value) {
  return value === null || value === undefined ? "n/a" : Number(value).toFixed(3);
}
```

### `dogfight_dashboard/static/style.css`

```css
:root {
  color-scheme: dark;
  --bg: #101214;
  --panel: #171b1f;
  --panel-2: #1d2328;
  --line: #303941;
  --text: #eef3f7;
  --muted: #9aa7b0;
  --accent: #4db6ac;
  --blue: #4d8dff;
  --red: #ff5757;
  --sea: #0969a8;
  --warn: #f3b34c;
  --bad: #f06f64;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  font-family: "Segoe UI", Arial, sans-serif;
  letter-spacing: 0;
}

button,
input,
select {
  font: inherit;
}

button,
select {
  min-height: 34px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--panel-2);
  color: var(--text);
}

button {
  padding: 0 12px;
  cursor: pointer;
}

button:hover,
button.active {
  border-color: var(--accent);
  color: var(--accent);
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 3;
  display: grid;
  grid-template-columns: auto auto 1fr;
  gap: 14px;
  align-items: center;
  min-height: 58px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
  background: rgba(16, 18, 20, 0.98);
}

.brand {
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
}

.tabs {
  display: inline-flex;
  gap: 8px;
}

.tab-button {
  min-width: 92px;
}

.app-status {
  min-width: 0;
  color: var(--muted);
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tab-panel {
  display: none;
}

.tab-panel.active {
  display: block;
}

.training-toolbar,
.replay-toolbar {
  display: grid;
  gap: 12px;
  align-items: center;
  min-height: 58px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--line);
  background: rgba(16, 18, 20, 0.78);
}

.training-toolbar {
  grid-template-columns: minmax(180px, 300px) auto minmax(170px, 260px) 1fr;
}

.replay-toolbar {
  grid-template-columns: minmax(220px, 420px) auto auto minmax(210px, 280px) 1fr;
}

.smooth,
.speed-control {
  display: grid;
  gap: 8px;
  align-items: center;
  color: var(--muted);
}

.smooth {
  grid-template-columns: auto 1fr 28px;
}

.speed-control {
  grid-template-columns: auto 1fr 46px;
}

#status-text,
#replay-status-text {
  min-width: 0;
  color: var(--muted);
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 10px;
  padding: 14px 16px 8px;
}

.metric-card {
  min-height: 78px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
}

.metric-card.alert {
  border-color: var(--bad);
}

.card-label {
  color: var(--muted);
  font-size: 12px;
}

.card-value {
  margin-top: 8px;
  font-size: clamp(18px, 2.1vw, 24px);
  font-weight: 700;
  overflow-wrap: anywhere;
}

.training-layout {
  display: grid;
  grid-template-columns: 340px 1fr;
  gap: 14px;
  padding: 8px 16px 16px;
}

.training-sidebar {
  min-width: 0;
  border-right: 1px solid var(--line);
  padding-right: 14px;
}

.section-title {
  margin: 10px 0 8px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.run-list {
  display: grid;
  gap: 8px;
}

.run-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 8px;
  align-items: center;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  cursor: pointer;
}

.run-item.selected {
  border-color: var(--accent);
}

.run-name {
  min-width: 0;
  overflow-wrap: anywhere;
  font-weight: 600;
}

.run-step {
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}

.config-box,
.log-info {
  margin: 0;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--muted);
  font-size: 12px;
}

.config-box {
  max-height: 340px;
  padding: 0;
}

.metric-box {
  display: grid;
  max-height: 260px;
  gap: 8px;
  overflow: auto;
}

.metric-group {
  padding: 9px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
}

.metric-group-title {
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
}

.metric-list {
  margin-top: 6px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.config-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.config-row {
  border-bottom: 1px solid rgba(48, 57, 65, 0.55);
}

.config-key {
  width: 42%;
  padding: 7px 8px 7px 10px;
  color: var(--accent);
  text-align: left;
  vertical-align: top;
  overflow-wrap: anywhere;
  font-weight: 600;
}

.config-value {
  width: 58%;
  padding: 7px 10px 7px 8px;
  color: var(--text);
  vertical-align: top;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  text-align: left;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(260px, 1fr));
  gap: 12px;
}

.chart-card {
  min-width: 0;
  height: 330px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  cursor: zoom-in;
}

.chart-title {
  height: 24px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

canvas {
  display: block;
  width: 100%;
  height: calc(100% - 82px);
}

.chart-legend {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 6px 10px;
  height: 58px;
  overflow: auto;
  padding-top: 6px;
  color: var(--muted);
  font-size: 11px;
}

.legend-item {
  display: inline-flex;
  min-width: 0;
  max-width: 100%;
  align-items: center;
  gap: 5px;
}

.legend-swatch {
  width: 9px;
  height: 9px;
  flex: 0 0 auto;
  border-radius: 2px;
}

.legend-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.modal {
  position: fixed;
  inset: 0;
  z-index: 5;
  display: grid;
  place-items: center;
  padding: 18px;
  background: rgba(0, 0, 0, 0.68);
}

.modal[hidden] {
  display: none;
}

.modal-panel {
  position: relative;
  width: min(1100px, 96vw);
  height: min(720px, 88vh);
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
}

.modal-close {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 34px;
  padding: 0;
}

.modal-title {
  height: 34px;
  padding-right: 44px;
  color: var(--text);
  font-weight: 700;
}

#modal-canvas {
  height: calc(100% - 92px);
}

.modal-legend {
  height: 58px;
}

.viewer-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  height: calc(100vh - 116px);
}

.scene-panel {
  position: relative;
  min-width: 0;
  min-height: 0;
  background: #07090a;
}

.scene-root {
  position: absolute;
  inset: 0;
}

.scene-root canvas {
  height: 100%;
}

.hud {
  position: absolute;
  z-index: 1;
  padding: 8px 10px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 6px;
  background: rgba(10, 12, 14, 0.56);
  color: var(--text);
  font-size: 13px;
  line-height: 1.4;
  white-space: pre;
  pointer-events: none;
  text-shadow: 0 1px 2px #000;
}

.hud-left {
  top: 14px;
  left: 14px;
}

.hud-right {
  top: 14px;
  right: 14px;
  text-align: right;
}

.hud-bottom {
  right: 14px;
  bottom: 14px;
  max-width: min(720px, calc(100% - 28px));
  overflow: hidden;
  text-overflow: ellipsis;
}

.side-panel {
  min-width: 0;
  overflow: auto;
  border-left: 1px solid var(--line);
  background: var(--panel);
  padding: 14px;
}

.toggle {
  display: grid;
  grid-template-columns: 18px 1fr;
  gap: 8px;
  align-items: center;
  min-height: 30px;
  color: var(--text);
}

.camera-mode-group {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.camera-mode-button {
  min-width: 0;
  padding: 0 8px;
}

.camera-mode-button.active {
  border-color: var(--blue);
  background: rgba(77, 141, 255, 0.18);
  color: #ffffff;
}

.timeline {
  width: 100%;
}

.readout-grid,
.debug-grid {
  display: grid;
  grid-template-columns: 82px 1fr;
  gap: 6px 10px;
  align-items: center;
  color: var(--muted);
}

.readout-grid strong,
.debug-grid strong {
  min-width: 0;
  color: var(--text);
  overflow-wrap: anywhere;
}

.log-info {
  max-height: 220px;
  padding: 10px;
  line-height: 1.45;
  white-space: pre-wrap;
}

@media (max-width: 960px) {
  .app-header,
  .training-toolbar,
  .replay-toolbar {
    grid-template-columns: 1fr;
  }

  .app-status,
  #status-text,
  #replay-status-text {
    text-align: left;
  }

  .cards {
    grid-template-columns: repeat(2, minmax(130px, 1fr));
  }

  .training-layout,
  .viewer-shell {
    grid-template-columns: 1fr;
    height: auto;
  }

  .training-sidebar {
    border-right: 0;
    padding-right: 0;
  }

  .chart-grid {
    grid-template-columns: 1fr;
  }

  .scene-panel {
    height: 64vh;
  }

  .side-panel {
    border-left: 0;
    border-top: 1px solid var(--line);
  }

  .hud {
    font-size: 11px;
    max-width: calc(100% - 28px);
  }
}
```

### `dogfight_dashboard/static/training.js`

```javascript
"use strict";

let API_BASE = "/api/training";

const CHART_GROUPS = [
  {
    id: "reward",
    title: "Episode Reward",
    metrics: ["episode/score", "episode/reward_mean"],
  },
  {
    id: "outcome",
    title: "Outcome Rates",
    metrics: [
      "episode/win_rate",
      "episode/loss_rate",
      "episode/timeout_rate",
      "episode/crash_rate",
    ],
  },
  {
    id: "length",
    title: "Episode Length and Count",
    metrics: ["episode/length", "episode/count"],
  },
  {
    id: "tactical",
    title: "Tactical Distance / WEZ",
    metrics: [
      "dogfight/wez_steps",
      "dogfight/distance_mean",
      "dogfight/distance_min",
    ],
  },
  {
    id: "tactical_angles",
    title: "Tactical Angles",
    metrics: [
      "dogfight/initial_alpha_deg",
      "dogfight/initial_ata_deg",
      "dogfight/initial_aa_deg",
      "dogfight/final_ata_deg",
      "dogfight/final_aa_deg",
    ],
  },
  {
    id: "safety",
    title: "Safety / Envelope",
    metrics: [
      "dogfight/altitude_penalty_steps",
      "dogfight/headon_guard_fail",
      "episode/crash_rate",
      "episode/timeout_rate",
    ],
  },
  {
    id: "reward_parts",
    title: "Reward Components",
    metrics: [
      "reward/pursuit",
      "reward/damage",
      "reward/safety",
      "reward/survival",
    ],
  },
  {
    id: "stability",
    title: "Learner Stability",
    metrics: [
      "train/loss/policy",
      "train/loss/value",
      "train/entropy",
      "train/kl",
    ],
  },
  {
    id: "action",
    title: "Action Health",
    metrics: [
      "action/saturation_rate",
      "action/roll_mean",
      "action/pitch_mean",
      "action/rudder_mean",
      "action/throttle_mean",
    ],
  },
  {
    id: "action_std",
    title: "Action Variability",
    metrics: [
      "action/roll_std",
      "action/pitch_std",
      "action/rudder_std",
      "action/throttle_std",
    ],
  },
  {
    id: "value",
    title: "Value Diagnostics",
    metrics: ["train/clip_frac", "train/explained_var"],
  },
  {
    id: "sac",
    title: "SAC / Replay Diagnostics",
    metrics: [
      "train/loss/actor",
      "train/loss/critic",
      "train/loss/alpha",
      "train/alpha",
      "replay/memory_mb",
    ],
  },
  {
    id: "curriculum",
    title: "Curriculum / Throughput",
    metrics: [
      "curriculum/stage",
      "perf/env_steps_per_sec",
      "perf/learner_steps_per_sec",
      "perf/iteration_time_s",
    ],
  },
];

const STATUS_CARDS = [
  { key: "episode/score", label: "Reward", fmt: formatNumber },
  { key: "episode/win_rate", label: "Win Rate", fmt: formatPercent },
  { key: "episode/crash_rate", label: "Crash Rate", fmt: formatPercent },
  { key: "dogfight/distance_min", label: "Min Range", fmt: value => `${formatCompact(value)}m` },
  { key: "dogfight/wez_steps", label: "WEZ Steps", fmt: formatNumber },
  { key: "train/entropy", label: "Entropy", fmt: formatNumber },
  { key: "action/saturation_rate", label: "Sat Rate", fmt: formatPercent },
  { key: "curriculum/stage", label: "Stage", fmt: value => formatNumber(value) },
];

const COLORS = [
  "#4db6ac",
  "#f3b34c",
  "#7aa6ff",
  "#f06f64",
  "#b084d8",
  "#77c66e",
  "#d9c86c",
  "#66c6e0",
  "#ff9f7a",
  "#9ee37d",
  "#e8e2a7",
  "#d5a6ff",
];

const EXPECTED_METRICS = [...new Set(CHART_GROUPS.flatMap(group => group.metrics))];

const State = {
  runs: [],
  selectedRun: "",
  compareMode: false,
  compareRuns: [],
  allData: {},
  lastStep: {},
  smooth: 8,
  pollTimer: null,
  lastUpdate: 0,
};

const $ = id => document.getElementById(id);

export function initTrainingDashboard(options = {}) {
  API_BASE = options.apiBase || API_BASE;
  buildChartCards();
  bindEvents();
  refreshRunList().then(() => {
    poll();
    State.pollTimer = setInterval(poll, 5000);
  });
  setInterval(updateStatus, 1000);
}

function buildChartCards() {
  const grid = $("chart-grid");
  grid.innerHTML = "";
  for (const group of CHART_GROUPS) {
    const card = document.createElement("section");
    card.className = "chart-card";
    card.innerHTML = `
      <div class="chart-title">${group.title}</div>
      <canvas id="chart-${group.id}"></canvas>
      <div id="legend-${group.id}" class="chart-legend"></div>
    `;
    card.addEventListener("click", () => openModal(group));
    grid.appendChild(card);
  }
}

function bindEvents() {
  $("run-select").addEventListener("change", event => {
    selectRun(event.target.value);
  });
  $("compare-button").addEventListener("click", () => {
    State.compareMode = !State.compareMode;
    $("compare-button").classList.toggle("active", State.compareMode);
    renderRunList();
    renderCharts();
  });
  $("smooth-slider").addEventListener("input", event => {
    State.smooth = Number(event.target.value);
    $("smooth-value").textContent = String(State.smooth);
    State.allData = {};
    State.lastStep = {};
    poll();
  });
  $("modal-close").addEventListener("click", closeModal);
  $("modal").addEventListener("click", event => {
    if (event.target === $("modal")) {
      closeModal();
    }
  });
  window.addEventListener("resize", renderCharts);
}

async function refreshRunList() {
  const data = await apiFetch("/api/runs");
  State.runs = data.runs || [];
  const select = $("run-select");
  const previous = select.value;
  select.innerHTML = "";
  for (const run of State.runs) {
    const option = document.createElement("option");
    option.value = run.name;
    option.textContent = run.name;
    select.appendChild(option);
  }
  if (State.runs.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No runs";
    select.appendChild(option);
    $("status-text").textContent = "No dashboard runs found";
    return;
  }
  const next = State.runs.some(run => run.name === previous)
    ? previous
    : State.runs[0].name;
  select.value = next;
  if (!State.selectedRun) {
    State.selectedRun = next;
    loadConfig(next);
  }
  renderRunList();
}

function renderRunList() {
  const list = $("run-list");
  list.innerHTML = "";
  for (const run of State.runs) {
    const item = document.createElement("div");
    item.className = "run-item";
    if (run.name === State.selectedRun) {
      item.classList.add("selected");
    }

    if (State.compareMode) {
      const box = document.createElement("input");
      box.type = "checkbox";
      box.checked = State.compareRuns.includes(run.name);
      box.addEventListener("change", event => {
        event.stopPropagation();
        if (box.checked) {
          State.compareRuns.push(run.name);
        } else {
          State.compareRuns = State.compareRuns.filter(name => name !== run.name);
        }
        poll();
      });
      item.appendChild(box);
    } else {
      const spacer = document.createElement("span");
      item.appendChild(spacer);
    }

    const body = document.createElement("div");
    body.innerHTML = `
      <div class="run-name">${run.name}</div>
      <div class="run-step">step ${formatCompact(run.last_step)}</div>
    `;
    item.appendChild(body);
    item.addEventListener("click", () => selectRun(run.name));
    list.appendChild(item);
  }
}

function selectRun(name) {
  if (!name) {
    return;
  }
  State.selectedRun = name;
  $("run-select").value = name;
  loadConfig(name);
  renderRunList();
  poll();
}

async function loadConfig(run) {
  try {
    const config = await apiFetch(`/api/config?run=${encodeURIComponent(run)}`);
    renderConfig(config);
  } catch (error) {
    $("config-box").innerHTML = "";
  }
}

function renderConfig(config) {
  const box = $("config-box");
  box.innerHTML = "";
  const entries = flattenConfig(config);
  if (entries.length === 0) {
    box.textContent = "No config";
    return;
  }
  const table = document.createElement("table");
  table.className = "config-table";
  const tbody = document.createElement("tbody");
  for (const [key, value] of entries) {
    const row = document.createElement("tr");
    row.className = "config-row";
    const keyEl = document.createElement("th");
    keyEl.className = "config-key";
    keyEl.scope = "row";
    keyEl.textContent = key;
    keyEl.title = key;
    const valueEl = document.createElement("td");
    valueEl.className = "config-value";
    valueEl.textContent = formatConfigValue(value);
    row.appendChild(keyEl);
    row.appendChild(valueEl);
    tbody.appendChild(row);
  }
  table.appendChild(tbody);
  box.appendChild(table);
}

function flattenConfig(value, prefix = "", out = []) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    if (prefix) {
      out.push([prefix, value]);
    }
    return out;
  }
  for (const [key, child] of Object.entries(value)) {
    const next = prefix ? `${prefix}.${key}` : key;
    flattenConfig(child, next, out);
  }
  return out;
}

function formatConfigValue(value) {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

async function poll() {
  await refreshRunList();
  const runs = getActiveRuns();
  await Promise.all(runs.map(fetchMetrics));
  if (State.selectedRun) {
    await refreshLatest(State.selectedRun);
  }
  renderCharts();
  renderMetricInventory();
  State.lastUpdate = Date.now();
  updateStatus();
}

async function fetchMetrics(run) {
  const since = State.lastStep[run] || 0;
  const path = `/api/metrics?run=${encodeURIComponent(run)}`
    + `&since_step=${since}&smooth=${State.smooth}`;
  const data = await apiFetch(path);
  State.allData[run] ||= {};
  for (const [key, points] of Object.entries(data.metrics || {})) {
    State.allData[run][key] ||= [];
    State.allData[run][key].push(...points);
  }
  if (data.last_step > (State.lastStep[run] || 0)) {
    State.lastStep[run] = data.last_step;
  }
}

async function refreshLatest(run) {
  const latest = await apiFetch(`/api/latest?run=${encodeURIComponent(run)}`);
  const cards = $("cards");
  cards.innerHTML = "";
  for (const spec of STATUS_CARDS) {
    const value = latest.values?.[spec.key];
    const card = document.createElement("div");
    card.className = "metric-card";
    if (latest.alerts?.[spec.key] !== undefined) {
      card.classList.add("alert");
    }
    card.innerHTML = `
      <div class="card-label">${spec.label}</div>
      <div class="card-value">${value === undefined ? "--" : spec.fmt(value)}</div>
    `;
    cards.appendChild(card);
  }
}

function getActiveRuns() {
  if (State.compareMode && State.compareRuns.length > 0) {
    return [...new Set(State.compareRuns)];
  }
  return State.selectedRun ? [State.selectedRun] : [];
}

function renderCharts() {
  for (const group of CHART_GROUPS) {
    const canvas = $(`chart-${group.id}`);
    if (canvas) {
      const datasets = buildDatasets(group);
      drawChart(canvas, group, datasets);
      renderLegend($(`legend-${group.id}`), datasets);
    }
  }
  const modal = $("modal");
  if (!modal.hidden && modal.dataset.groupId) {
    const group = CHART_GROUPS.find(item => item.id === modal.dataset.groupId);
    if (group) {
      const datasets = buildDatasets(group);
      drawChart($("modal-canvas"), group, datasets);
      renderLegend($("modal-legend"), datasets);
    }
  }
}

function renderMetricInventory() {
  const box = $("metric-box");
  if (!box) {
    return;
  }
  const runData = State.allData[State.selectedRun] || {};
  const available = Object.keys(runData)
    .filter(key => (runData[key] || []).length > 0)
    .sort();
  const missing = EXPECTED_METRICS.filter(key => !available.includes(key));
  const extra = available.filter(key => !EXPECTED_METRICS.includes(key));
  box.innerHTML = "";
  for (const [title, values] of [
    ["Available", available],
    ["Expected Missing", missing],
    ["Other Logged", extra],
  ]) {
    const group = document.createElement("div");
    group.className = "metric-group";
    const titleEl = document.createElement("div");
    titleEl.className = "metric-group-title";
    titleEl.textContent = `${title} (${values.length})`;
    const listEl = document.createElement("div");
    listEl.className = "metric-list";
    listEl.textContent = values.length ? values.join(", ") : "None";
    group.appendChild(titleEl);
    group.appendChild(listEl);
    box.appendChild(group);
  }
}

function buildDatasets(group) {
  const datasets = [];
  let colorIndex = 0;
  for (const run of getActiveRuns()) {
    const runData = State.allData[run] || {};
    for (const metric of group.metrics) {
      const points = runData[metric] || [];
      if (points.length === 0) {
        continue;
      }
      datasets.push({
        name: `${getActiveRuns().length > 1 ? run + " / " : ""}${shortName(metric)}`,
        points,
        color: COLORS[colorIndex % COLORS.length],
      });
      colorIndex += 1;
    }
  }
  return datasets;
}

function drawChart(canvas, group, datasets) {
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.floor(rect.width * dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * dpr));
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const width = rect.width;
  const height = rect.height;
  ctx.clearRect(0, 0, width, height);

  ctx.fillStyle = "#171b1f";
  ctx.fillRect(0, 0, width, height);
  if (datasets.length === 0) {
    ctx.fillStyle = "#9aa7b0";
    ctx.font = "13px Segoe UI, Arial";
    ctx.fillText("Waiting for metrics", 24, height / 2);
    return;
  }

  const bounds = getBounds(datasets);
  const padding = chartPadding(ctx, width, height, bounds);
  const plot = {
    x: padding.left,
    y: padding.top,
    w: Math.max(1, width - padding.left - padding.right),
    h: Math.max(1, height - padding.top - padding.bottom),
  };

  drawGrid(ctx, plot, bounds);
  for (const dataset of datasets) {
    drawSeries(ctx, plot, bounds, dataset);
  }
}

function chartPadding(ctx, width, height, bounds) {
  ctx.font = "11px Segoe UI, Arial";
  const labels = [];
  for (let i = 0; i <= 4; i += 1) {
    const value = bounds.maxY - ((bounds.maxY - bounds.minY) * i) / 4;
    labels.push(formatCompact(value));
  }
  const widest = Math.max(...labels.map(label => ctx.measureText(label).width));
  return {
    left: Math.min(Math.max(widest + 18, 46), Math.max(54, width * 0.24)),
    right: Math.max(12, width * 0.03),
    top: Math.max(10, height * 0.04),
    bottom: Math.max(26, height * 0.12),
  };
}

function getBounds(datasets) {
  const xs = [];
  const ys = [];
  for (const dataset of datasets) {
    for (const [x, y] of dataset.points) {
      xs.push(x);
      ys.push(y);
    }
  }
  let minX = Math.min(...xs);
  let maxX = Math.max(...xs);
  let minY = Math.min(...ys);
  let maxY = Math.max(...ys);
  if (minX === maxX) {
    maxX += 1;
  }
  if (minY === maxY) {
    minY -= 1;
    maxY += 1;
  }
  const yPad = (maxY - minY) * 0.08;
  return { minX, maxX, minY: minY - yPad, maxY: maxY + yPad };
}

function drawGrid(ctx, plot, bounds) {
  ctx.strokeStyle = "#303941";
  ctx.lineWidth = 1;
  ctx.font = "11px Segoe UI, Arial";
  ctx.fillStyle = "#9aa7b0";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";

  for (let i = 0; i <= 4; i += 1) {
    const y = plot.y + (plot.h * i) / 4;
    const value = bounds.maxY - ((bounds.maxY - bounds.minY) * i) / 4;
    ctx.beginPath();
    ctx.moveTo(plot.x, y);
    ctx.lineTo(plot.x + plot.w, y);
    ctx.stroke();
    ctx.fillText(formatCompact(value), plot.x - 8, y);
  }

  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let i = 0; i <= 4; i += 1) {
    const x = plot.x + (plot.w * i) / 4;
    const value = bounds.minX + ((bounds.maxX - bounds.minX) * i) / 4;
    ctx.beginPath();
    ctx.moveTo(x, plot.y);
    ctx.lineTo(x, plot.y + plot.h);
    ctx.stroke();
    ctx.fillText(formatCompact(value), x, plot.y + plot.h + 8);
  }
}

function drawSeries(ctx, plot, bounds, dataset) {
  ctx.strokeStyle = dataset.color;
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  dataset.points.forEach(([xValue, yValue], index) => {
    const x = plot.x
      + ((xValue - bounds.minX) / (bounds.maxX - bounds.minX)) * plot.w;
    const y = plot.y + plot.h
      - ((yValue - bounds.minY) / (bounds.maxY - bounds.minY)) * plot.h;
    if (index === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });
  ctx.stroke();
}

function renderLegend(container, datasets) {
  if (!container) {
    return;
  }
  container.innerHTML = "";
  if (datasets.length === 0) {
    container.textContent = "No visible series";
    return;
  }
  for (const dataset of datasets) {
    const item = document.createElement("span");
    item.className = "legend-item";
    item.title = dataset.name;
    const swatch = document.createElement("span");
    swatch.className = "legend-swatch";
    swatch.style.background = dataset.color;
    const label = document.createElement("span");
    label.className = "legend-label";
    label.textContent = dataset.name;
    item.appendChild(swatch);
    item.appendChild(label);
    container.appendChild(item);
  }
}

function openModal(group) {
  const modal = $("modal");
  modal.hidden = false;
  modal.dataset.groupId = group.id;
  $("modal-title").textContent = group.title;
  const datasets = buildDatasets(group);
  drawChart($("modal-canvas"), group, datasets);
  renderLegend($("modal-legend"), datasets);
}

function closeModal() {
  const modal = $("modal");
  modal.hidden = true;
  modal.dataset.groupId = "";
}

function updateStatus() {
  if (!State.lastUpdate) {
    return;
  }
  const seconds = Math.round((Date.now() - State.lastUpdate) / 1000);
  const step = State.lastStep[State.selectedRun] || 0;
  $("status-text").textContent =
    `Updated ${seconds}s ago | step ${formatCompact(step)}`;
}

async function apiFetch(path) {
  const response = await fetch(path.replace(/^\/api/, API_BASE), { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${path}`);
  }
  return response.json();
}

function shortName(key) {
  return key.split("/").slice(-2).join("/");
}

function formatNumber(value) {
  if (!Number.isFinite(value)) {
    return "--";
  }
  if (Math.abs(value) >= 100) {
    return value.toFixed(0);
  }
  if (Math.abs(value) >= 10) {
    return value.toFixed(1);
  }
  return value.toFixed(3);
}

function formatPercent(value) {
  if (!Number.isFinite(value)) {
    return "--";
  }
  return `${(value * 100).toFixed(1)}%`;
}

function formatCompact(value) {
  if (!Number.isFinite(value)) {
    return "--";
  }
  const abs = Math.abs(value);
  if (abs >= 1e6) {
    return `${(value / 1e6).toFixed(1)}M`;
  }
  if (abs >= 1e3) {
    return `${(value / 1e3).toFixed(1)}k`;
  }
  if (abs < 1 && value !== 0) {
    return value.toFixed(3);
  }
  return value.toFixed(0);
}
```

### `dogfight_dashboard/static/vendor/THREE_LICENSE.txt`

```text
The MIT License

Copyright © 2010-2024 three.js authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

### `dogfight_dashboard/training_data.py`

```python
"""Training metrics reader for the unified dashboard."""

from __future__ import annotations

import json
import math
import threading
from pathlib import Path


class MetricsReader:
    """Incrementally read dashboard metrics from run directories."""

    def __init__(self, logdir: Path) -> None:
        self.logdir = Path(logdir).resolve()
        self._lock = threading.Lock()
        self._offsets: dict[str, int] = {}
        self._cache: dict[str, list[dict]] = {}

    def list_runs(self) -> list[dict]:
        """Return metric run directories sorted by latest modification time."""
        runs = []
        if not self.logdir.exists():
            return runs
        for run_dir in sorted(self.logdir.iterdir()):
            metrics_path = run_dir / "metrics.jsonl"
            if not run_dir.is_dir() or not metrics_path.exists():
                continue
            rows = self._read_rows(run_dir.name)
            runs.append(
                {
                    "name": run_dir.name,
                    "last_step": int(rows[-1].get("step", 0)) if rows else 0,
                    "last_modified": metrics_path.stat().st_mtime,
                    "has_config": (
                        (run_dir / "config.json").exists()
                        or (run_dir / "config.yaml").exists()
                    ),
                }
            )
        runs.sort(key=lambda item: item["last_modified"], reverse=True)
        return runs

    def read_metrics(
        self,
        run: str,
        since_step: int = 0,
        smooth: int = 1,
    ) -> dict:
        """Return scalar metric series for one training run."""
        rows = self._read_rows(run)
        full_series: dict[str, list[list[float]]] = {}
        for row in rows:
            step = _as_number(row.get("step"))
            if step is None:
                continue
            for key, value in row.items():
                if key == "step":
                    continue
                number = _as_number(value)
                if number is not None:
                    full_series.setdefault(key, []).append([step, number])
        if smooth > 1:
            full_series = {
                key: self._smooth_ema(points, smooth)
                for key, points in full_series.items()
            }
        series = {
            key: [point for point in points if point[0] > since_step]
            for key, points in full_series.items()
        }
        last_step = int(rows[-1].get("step", 0)) if rows else 0
        return {"last_step": last_step, "metrics": series}

    def get_latest(self, run: str) -> dict:
        """Return latest scalar values and alert subset for one run."""
        values = {}
        step = 0
        for row in self._read_rows(run):
            step = int(row.get("step", step) or step)
            for key, value in row.items():
                if key == "step":
                    continue
                number = _as_number(value)
                if number is not None:
                    values[key] = number
        alerts = {
            key: value
            for key, value in values.items()
            if self._is_alert(key, value)
        }
        return {"step": step, "values": values, "alerts": alerts}

    def get_config(self, run: str) -> dict:
        """Read sibling config JSON/YAML for one training run."""
        run_dir = self._run_dir(run)
        json_path = run_dir / "config.json"
        if json_path.exists():
            try:
                return json.loads(json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {"raw": json_path.read_text(encoding="utf-8")}
        yaml_path = run_dir / "config.yaml"
        if yaml_path.exists():
            return {"raw": yaml_path.read_text(encoding="utf-8")}
        return {}

    def _read_rows(self, run: str) -> list[dict]:
        metrics_path = self._run_dir(run) / "metrics.jsonl"
        if not metrics_path.exists():
            return self._cache.get(run, [])

        with self._lock:
            size = metrics_path.stat().st_size
            offset = self._offsets.get(run, 0)
            if offset > size:
                offset = 0
                self._cache[run] = []
            if offset == size:
                return self._cache.get(run, [])

            with metrics_path.open("rb") as file:
                file.seek(offset)
                chunk = file.read()
                self._offsets[run] = file.tell()

            rows = self._cache.setdefault(run, [])
            for line in chunk.decode("utf-8", errors="replace").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
            return rows

    def _run_dir(self, run: str) -> Path:
        candidate = (self.logdir / run).resolve()
        if self.logdir not in candidate.parents and candidate != self.logdir:
            raise ValueError("invalid run path")
        return candidate

    @staticmethod
    def _smooth_ema(points: list[list[float]], smooth: int) -> list[list[float]]:
        if not points:
            return points
        weight = 1.0 / (smooth + 1)
        value = points[0][1]
        result = []
        for step, raw in points:
            value = (1.0 - weight) * value + weight * raw
            result.append([step, round(value, 6)])
        return result

    @staticmethod
    def _is_alert(key: str, value: float) -> bool:
        thresholds = {
            "episode/crash_rate": (">", 0.3),
            "action/saturation_rate": (">", 0.6),
            "dogfight/headon_guard_fail": (">", 0.0),
            "dogfight/altitude_penalty_steps": (">", 0.0),
            "train/kl": (">", 1.0),
            "train/entropy": ("<", 0.01),
        }
        rule = thresholds.get(key)
        if not rule:
            return False
        op, threshold = rule
        return value > threshold if op == ">" else value < threshold


def _as_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    return None
```

### `web_log_viewer/__init__.py`

```python
"""Web-based Tacview CSV replay viewer for DogFightEnv."""
```

### `web_log_viewer/log_data.py`

```python
"""PyVista-free log parsing and tactical math for web playback."""

from __future__ import annotations

import csv
import json
import math
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SEA_SIZE_M = 20_000.0
AIRCRAFT_MIN_DISPLAY_LENGTH_M = 45.0
AIRCRAFT_MAX_DISPLAY_LENGTH_M = 160.0
FEET_TO_M = 0.3048
DEFAULT_SPEED = 5.0
TRAIL_SECONDS = 10.0
DEFAULT_WEZ_MIN_RANGE_M = 500.0 * FEET_TO_M
DEFAULT_WEZ_RANGE_M = 3_000.0 * FEET_TO_M
DEFAULT_WEZ_ANGLE_DEG = 2.0

REQUIRED_COLUMNS = {
    "Time",
    "Longitude",
    "Latitude",
    "Altitude",
    "Roll (deg)",
    "Pitch (deg)",
    "Yaw (deg)",
}


Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class AircraftTrack:
    """Parsed aircraft state history in local ENU display coordinates."""

    time: list[float]
    position: list[Vector3]
    roll_deg: list[float]
    pitch_deg: list[float]
    yaw_deg: list[float]
    health: list[float]


@dataclass(frozen=True)
class ViewerData:
    """Resolved log inputs and derived viewer state."""

    ownship_log: Path
    target_log: Path
    metadata_path: Path | None
    end_condition: str
    ownship: AircraftTrack
    target: AircraftTrack


def normalize_log_pair(
    selected_log: Path,
    paired_log: Path | None = None,
) -> tuple[Path, Path]:
    """Resolve selected Blue/Red CSVs into ownship/target paths."""
    selected_log = Path(selected_log)
    if selected_log.suffix.lower() != ".csv":
        raise ValueError(f"Expected a CSV log file: {selected_log}")

    if paired_log is not None:
        paired_log = Path(paired_log)
        ownship_log = selected_log if "[Blue]" in selected_log.name else paired_log
        target_log = selected_log if "[Red]" in selected_log.name else paired_log
        return ownship_log, target_log

    selected_name = selected_log.name
    if "[Blue]" in selected_name:
        ownship_log = selected_log
        target_name = selected_name.replace("ownship", "target").replace(
            "[Blue]", "[Red]"
        )
        target_log = selected_log.with_name(target_name)
    elif "[Red]" in selected_name:
        target_log = selected_log
        ownship_name = selected_name.replace("target", "ownship").replace(
            "[Red]", "[Blue]"
        )
        ownship_log = selected_log.with_name(ownship_name)
    else:
        raise ValueError(
            "Cannot infer Blue/Red pair from filename without [Blue]/[Red]: "
            f"{selected_log}"
        )

    if not ownship_log.exists():
        raise FileNotFoundError(f"Blue log not found: {ownship_log}")
    if not target_log.exists():
        raise FileNotFoundError(f"Red log not found: {target_log}")
    return ownship_log, target_log


def discover_log_pairs(logdir: Path) -> list[tuple[Path, Path]]:
    """Discover ownship/target CSV pairs under a log directory."""
    if not logdir.exists():
        return []

    pairs: list[tuple[Path, Path]] = []
    seen: set[tuple[Path, Path]] = set()
    for path in sorted(logdir.rglob("*.csv")):
        if "[Blue]" not in path.name and "[Red]" not in path.name:
            continue
        try:
            ownship, target = normalize_log_pair(path)
        except (FileNotFoundError, ValueError):
            continue
        key = (ownship.resolve(), target.resolve())
        if key not in seen:
            seen.add(key)
            pairs.append((ownship, target))
    return pairs


def read_log_rows(path: Path) -> list[dict[str, float]]:
    """Read a Tacview-style CSV log and return numeric rows."""
    rows: list[dict[str, float]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path} is missing columns: {sorted(missing)}")

        for row in reader:
            parsed = {key: float(row[key]) for key in REQUIRED_COLUMNS}
            health_value = row.get("Health", row.get("health", "nan"))
            parsed["Health"] = parse_optional_float(health_value)
            rows.append(parsed)

    if not rows:
        raise ValueError(f"{path} has no data rows.")
    return rows


def parse_optional_float(value: object) -> float:
    """Parse optional numeric CSV values as float, returning NaN on blanks."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def build_track(
    rows: list[dict[str, float]],
    ref_lat: float,
    ref_lon: float,
) -> AircraftTrack:
    """Convert geodetic rows to a local flat ENU frame."""
    position: list[Vector3] = []
    for row in rows:
        east, north = geodetic_to_local_m(
            lat_deg=row["Latitude"],
            lon_deg=row["Longitude"],
            ref_lat_deg=ref_lat,
            ref_lon_deg=ref_lon,
        )
        position.append((east, north, row["Altitude"]))

    return AircraftTrack(
        time=[row["Time"] for row in rows],
        position=position,
        roll_deg=[row["Roll (deg)"] for row in rows],
        pitch_deg=[row["Pitch (deg)"] for row in rows],
        yaw_deg=[row["Yaw (deg)"] for row in rows],
        health=[row["Health"] for row in rows],
    )


def geodetic_to_local_m(
    lat_deg: float,
    lon_deg: float,
    ref_lat_deg: float,
    ref_lon_deg: float,
) -> tuple[float, float]:
    """Approximate WGS84 geodetic deltas as local meters."""
    earth_radius_m = 6_378_137.0
    lat_rad = math.radians(lat_deg)
    lon_rad = math.radians(lon_deg)
    ref_lat_rad = math.radians(ref_lat_deg)
    ref_lon_rad = math.radians(ref_lon_deg)
    north = (lat_rad - ref_lat_rad) * earth_radius_m
    east = (lon_rad - ref_lon_rad) * earth_radius_m * math.cos(ref_lat_rad)
    return east, north


def build_viewer_data(
    ownship_log: Path,
    target_log: Path,
    metadata_path: Path | None,
    fallback_end_condition: str = "n/a",
) -> ViewerData:
    """Load logs and build a viewer-ready dataset."""
    own_rows = read_log_rows(ownship_log)
    target_rows = read_log_rows(target_log)
    ref_lat, ref_lon = first_row_ref(own_rows)
    ownship = build_track(own_rows, ref_lat, ref_lon)
    target = build_track(target_rows, ref_lat, ref_lon)
    end_condition = load_end_condition(metadata_path, fallback_end_condition)
    return ViewerData(
        ownship_log=Path(ownship_log),
        target_log=Path(target_log),
        metadata_path=metadata_path,
        end_condition=end_condition,
        ownship=ownship,
        target=target,
    )


def first_row_ref(rows: Iterable[dict[str, float]]) -> tuple[float, float]:
    """Return latitude/longitude from the first parsed CSV row."""
    first = next(iter(rows))
    return first["Latitude"], first["Longitude"]


def infer_summary_path(ownship_log: Path) -> Path | None:
    """Infer the summary JSON path generated beside an ownship CSV log."""
    marker = "_ownship_(F-16)[Blue].csv"
    name = Path(ownship_log).name
    if marker not in name:
        return None
    candidate = Path(ownship_log).with_name(name.replace(marker, "_summary.json"))
    return candidate if candidate.exists() else None


def load_metadata(metadata_path: Path | None) -> dict:
    """Load optional replay metadata JSON."""
    if metadata_path is None:
        return {}
    try:
        with Path(metadata_path).open("r", encoding="utf-8") as file:
            metadata = json.load(file)
    except (OSError, json.JSONDecodeError):
        return {}
    return metadata if isinstance(metadata, dict) else {}


def load_end_condition(metadata_path: Path | None, fallback: str) -> str:
    """Load end condition text from metadata JSON when available."""
    metadata = load_metadata(metadata_path)
    if not metadata:
        return fallback
    end_condition = metadata.get("end_condition") or fallback
    outcome = metadata.get("outcome")
    if outcome:
        return f"{end_condition} ({outcome})"
    return str(end_condition)


def scene_extent_m(ownship: AircraftTrack, target: AircraftTrack) -> float:
    """Return the largest span needed to frame both tracks."""
    points = ownship.position + target.position
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    xy_span = max(max(xs) - min(xs), max(ys) - min(ys))
    z_span = max(zs) - min(zs)
    return max(xy_span, z_span, 1.0)


def sea_size_for_tracks(ownship: AircraftTrack, target: AircraftTrack) -> float:
    """Pick a sea plane size that covers the track extents with margin."""
    points = ownship.position + target.position
    horizontal_extent = max(
        max(abs(point[0]), abs(point[1])) for point in points
    ) * 2.0
    return max(SEA_SIZE_M, horizontal_extent + 2_000.0)


def aircraft_display_length_for_extent(extent_m: float) -> float:
    """Scale aircraft display size to the replay frame with conservative clamps."""
    scaled = max(extent_m * 0.012, AIRCRAFT_MIN_DISPLAY_LENGTH_M)
    return min(scaled, AIRCRAFT_MAX_DISPLAY_LENGTH_M)


def attitude_matrix(
    roll_deg: float,
    pitch_deg: float,
    yaw_deg: float,
) -> tuple[Vector3, Vector3, Vector3]:
    """Build a body-to-display rotation matrix for X-forward aircraft meshes."""
    roll = math.radians(roll_deg)
    pitch = math.radians(pitch_deg)
    yaw = math.radians(90.0 - yaw_deg)

    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)

    rot_x = ((1.0, 0.0, 0.0), (0.0, cr, -sr), (0.0, sr, cr))
    rot_y = ((cp, 0.0, sp), (0.0, 1.0, 0.0), (-sp, 0.0, cp))
    rot_z = ((cy, -sy, 0.0), (sy, cy, 0.0), (0.0, 0.0, 1.0))
    return matmul3(matmul3(rot_z, rot_y), rot_x)


def matmul3(
    first: tuple[Vector3, Vector3, Vector3],
    second: tuple[Vector3, Vector3, Vector3],
) -> tuple[Vector3, Vector3, Vector3]:
    """Multiply two 3x3 matrices."""
    rows: list[Vector3] = []
    for row in range(3):
        values: list[float] = []
        for col in range(3):
            values.append(sum(first[row][k] * second[k][col] for k in range(3)))
        rows.append((values[0], values[1], values[2]))
    return (rows[0], rows[1], rows[2])


def forward_vector(yaw_deg: float, pitch_deg: float) -> Vector3:
    """Compute aircraft forward vector in display coordinates."""
    matrix = attitude_matrix(0.0, pitch_deg, yaw_deg)
    direction = (
        matrix[0][0],
        matrix[1][0],
        matrix[2][0],
    )
    norm = vector_norm(direction)
    return vector_scale(direction, 1.0 / norm) if norm > 0.0 else (1.0, 0.0, 0.0)


def nearest_index(track: AircraftTrack, sim_time: float) -> int:
    """Return the nearest prior sample index for replay time."""
    index = bisect_right(track.time, sim_time) - 1
    return max(0, min(index, len(track.time) - 1))


def trail_points(
    track: AircraftTrack,
    sim_time: float,
    trail_seconds: float,
) -> list[Vector3]:
    """Return display positions inside the trailing time window."""
    start_time = sim_time - trail_seconds
    start = bisect_left(track.time, start_time)
    end = bisect_right(track.time, sim_time)
    return track.position[start:end]


def speed_at(track: AircraftTrack, index: int) -> float:
    """Estimate speed from neighboring log samples in meters per second."""
    if len(track.time) < 2:
        return 0.0
    prev_i = max(0, index - 1)
    next_i = min(len(track.time) - 1, index + 1)
    dt = track.time[next_i] - track.time[prev_i]
    if dt <= 0.0:
        return 0.0
    return vector_norm(vector_sub(track.position[next_i], track.position[prev_i])) / dt


def velocity_at(track: AircraftTrack, index: int) -> Vector3:
    """Estimate velocity vector from neighboring log samples."""
    if len(track.time) < 2:
        return (0.0, 0.0, 0.0)
    prev_i = max(0, index - 1)
    next_i = min(len(track.time) - 1, index + 1)
    dt = track.time[next_i] - track.time[prev_i]
    if dt <= 0.0:
        return (0.0, 0.0, 0.0)
    return vector_scale(vector_sub(track.position[next_i], track.position[prev_i]), 1.0 / dt)


def angle_between_deg(first: Vector3, second: Vector3) -> float:
    """Return the unsigned angle between two vectors in degrees."""
    first_norm = vector_norm(first)
    second_norm = vector_norm(second)
    if first_norm <= 0.0 or second_norm <= 0.0:
        return 0.0
    cosine = vector_dot(first, second) / (first_norm * second_norm)
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


def in_wez(
    range_m: float,
    ata_deg: float,
    min_range_m: float = DEFAULT_WEZ_MIN_RANGE_M,
    max_range_m: float = DEFAULT_WEZ_RANGE_M,
    full_angle_deg: float = DEFAULT_WEZ_ANGLE_DEG,
) -> bool:
    """Return whether target geometry is inside the simplified WEZ frustum."""
    return (
        min_range_m <= range_m <= max_range_m
        and ata_deg <= max(0.0, full_angle_deg / 2.0)
    )


def tactical_snapshot(
    ownship: AircraftTrack,
    target: AircraftTrack,
    sim_time: float,
    wez_min_range: float = DEFAULT_WEZ_MIN_RANGE_M,
    wez_range: float = DEFAULT_WEZ_RANGE_M,
    wez_angle: float = DEFAULT_WEZ_ANGLE_DEG,
) -> dict[str, float | bool]:
    """Compute key HUD values for one replay time."""
    own_i = nearest_index(ownship, sim_time)
    target_i = nearest_index(target, sim_time)
    own_pos = ownship.position[own_i]
    target_pos = target.position[target_i]
    relative = vector_sub(target_pos, own_pos)
    distance = vector_norm(relative)
    own_forward = forward_vector(ownship.yaw_deg[own_i], ownship.pitch_deg[own_i])
    target_forward = forward_vector(target.yaw_deg[target_i], target.pitch_deg[target_i])
    own_ata = angle_between_deg(own_forward, relative)
    target_ata = angle_between_deg(target_forward, vector_scale(relative, -1.0))
    own_aa = angle_between_deg(target_forward, vector_scale(relative, -1.0))
    relative_velocity = vector_sub(velocity_at(target, target_i), velocity_at(ownship, own_i))
    closure = -vector_dot(relative, relative_velocity) / distance if distance > 0.0 else 0.0
    return {
        "own_index": own_i,
        "target_index": target_i,
        "distance_m": distance,
        "closure_mps": closure,
        "relative_alt_m": target_pos[2] - own_pos[2],
        "own_ata_deg": own_ata,
        "target_ata_deg": target_ata,
        "own_aa_deg": own_aa,
        "own_speed_mps": speed_at(ownship, own_i),
        "target_speed_mps": speed_at(target, target_i),
        "own_wez": in_wez(distance, own_ata, wez_min_range, wez_range, wez_angle),
        "target_wez": in_wez(distance, target_ata, wez_min_range, wez_range, wez_angle),
    }


def vector_sub(first: Vector3, second: Vector3) -> Vector3:
    return (first[0] - second[0], first[1] - second[1], first[2] - second[2])


def vector_scale(vector: Vector3, scale: float) -> Vector3:
    return (vector[0] * scale, vector[1] * scale, vector[2] * scale)


def vector_dot(first: Vector3, second: Vector3) -> float:
    return first[0] * second[0] + first[1] * second[1] + first[2] * second[2]


def vector_norm(vector: Vector3) -> float:
    return math.sqrt(vector_dot(vector, vector))


def track_to_json(track: AircraftTrack) -> dict[str, list]:
    """Serialize an AircraftTrack to browser-friendly arrays."""
    return {
        "time": track.time,
        "position": track.position,
        "rollDeg": track.roll_deg,
        "pitchDeg": track.pitch_deg,
        "yawDeg": track.yaw_deg,
        "health": [None if math.isnan(value) else value for value in track.health],
    }


def viewer_data_to_json(data: ViewerData) -> dict:
    """Serialize loaded logs and derived display constants."""
    extent = scene_extent_m(data.ownship, data.target)
    start_time = max(data.ownship.time[0], data.target.time[0])
    end_time = min(data.ownship.time[-1], data.target.time[-1])
    metadata = load_metadata(data.metadata_path)
    initial = tactical_snapshot(data.ownship, data.target, start_time)
    return {
        "logs": {
            "ownship": data.ownship_log.name,
            "target": data.target_log.name,
            "metadata": data.metadata_path.name if data.metadata_path else None,
        },
        "metadata": metadata,
        "endCondition": data.end_condition,
        "startTime": start_time,
        "endTime": end_time,
        "duration": max(0.0, end_time - start_time),
        "sceneExtentM": extent,
        "seaSizeM": sea_size_for_tracks(data.ownship, data.target),
        "aircraftDisplayLengthM": aircraft_display_length_for_extent(extent),
        "defaults": {
            "speed": DEFAULT_SPEED,
            "trailSeconds": TRAIL_SECONDS,
            "wezMinRangeM": DEFAULT_WEZ_MIN_RANGE_M,
            "wezRangeM": DEFAULT_WEZ_RANGE_M,
            "wezAngleDeg": DEFAULT_WEZ_ANGLE_DEG,
        },
        "initialTactical": initial,
        "ownship": track_to_json(data.ownship),
        "target": track_to_json(data.target),
    }


def parse_obj_mesh(path: Path) -> dict:
    """Parse a small OBJ mesh into normalized vertices and triangle faces."""
    vertices: list[Vector3] = []
    triangles: list[tuple[int, int, int]] = []
    with Path(path).open("r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if parts[0] == "v" and len(parts) >= 4:
                vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif parts[0] == "f" and len(parts) >= 4:
                face = [_obj_index(token, len(vertices)) for token in parts[1:]]
                for i in range(1, len(face) - 1):
                    triangles.append((face[0], face[i], face[i + 1]))

    if not vertices or not triangles:
        raise ValueError(f"Invalid OBJ mesh: {path}")

    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    center = (
        (min(xs) + max(xs)) / 2.0,
        (min(ys) + max(ys)) / 2.0,
        (min(zs) + max(zs)) / 2.0,
    )
    length = max(xs) - min(xs)
    if length <= 0.0:
        raise ValueError(f"Invalid mesh length: {path}")

    normalized = [
        (
            (v[0] - center[0]) / length,
            (v[1] - center[1]) / length,
            (v[2] - center[2]) / length,
        )
        for v in vertices
    ]
    return {
        "vertices": normalized,
        "triangles": triangles,
        "source": Path(path).name,
        "unitLengthAxis": "x",
    }


def _obj_index(token: str, vertex_count: int) -> int:
    raw = int(token.split("/")[0])
    return raw - 1 if raw > 0 else vertex_count + raw
```

### `web_log_viewer/README.md`

````markdown
# DogFight Replay Viewer Compatibility Layer

`tools/web_log_viewer.py` now opens the `Replay` tab of the unified DogFight
dashboard. The parser and replay data API remain in this package so existing
Tacview CSV playback contracts continue to work.

## Run

From `DogFightEnv/MyTrainEnv`:

```powershell
C:\Users\USER\anaconda3\envs\aip\python.exe tools\web_log_viewer.py --port 7870
```

From `DogFightEnv/Release`:

```powershell
C:\Users\USER\anaconda3\envs\aip\python.exe tools\web_log_viewer.py --port 7870
```

Then open:

```text
http://127.0.0.1:7870/?tab=replay
```

The preferred all-in-one entrypoint is:

```powershell
C:\Users\USER\anaconda3\envs\aip\python.exe tools\dashboard.py --port 7860
```

## 판단 근거

- PyVista has been removed from the active viewer path.
- Three.js-based replay runs inside the unified dashboard with the same F-16 OBJ
  asset and Tacview CSV parser.
- Keeping this wrapper avoids breaking existing replay commands while moving
  users toward the tabbed dashboard.
````

### `web_log_viewer/server.py`

```python
"""HTTP server for the DogFightEnv web log playback viewer."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

try:
    from .log_data import (
        DEFAULT_WEZ_ANGLE_DEG,
        DEFAULT_WEZ_MIN_RANGE_M,
        DEFAULT_WEZ_RANGE_M,
        build_viewer_data,
        discover_log_pairs,
        infer_summary_path,
        parse_obj_mesh,
        viewer_data_to_json,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from log_data import (  # type: ignore
        DEFAULT_WEZ_ANGLE_DEG,
        DEFAULT_WEZ_MIN_RANGE_M,
        DEFAULT_WEZ_RANGE_M,
        build_viewer_data,
        discover_log_pairs,
        infer_summary_path,
        parse_obj_mesh,
        viewer_data_to_json,
    )


PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
DEFAULT_ENV_ROOT = PACKAGE_DIR.parents[1] / "MyTrainEnv"


class ViewerRepository:
    """Resolve log and mesh files for the web viewer API."""

    def __init__(self, env_root: Path, logdir: Path | None, mesh_path: Path | None):
        self.env_root = env_root.resolve()
        self.logdir = (logdir or self.env_root / "logs").resolve()
        self.mesh_path = (
            mesh_path
            or self.env_root / "assets" / "meshes" / "f16" / "f16_simple_cc_by.obj"
        ).resolve()

    def list_logs(self) -> list[dict]:
        """Return discoverable Blue/Red log pairs."""
        pairs = []
        for ownship, target in discover_log_pairs(self.logdir):
            metadata_path = infer_summary_path(ownship)
            try:
                stat_time = max(ownship.stat().st_mtime, target.stat().st_mtime)
            except OSError:
                stat_time = 0.0
            pairs.append(
                {
                    "label": _pair_label(ownship),
                    "ownship": self._url_path(ownship),
                    "target": self._url_path(target),
                    "ownshipName": ownship.name,
                    "targetName": target.name,
                    "metadataName": metadata_path.name if metadata_path else None,
                    "lastModified": stat_time,
                }
            )
        pairs.sort(key=lambda item: item["lastModified"], reverse=True)
        return pairs

    def load_replay(self, ownship: str, target: str) -> dict:
        """Load and serialize one replay log pair."""
        ownship_path = self._safe_log_path(ownship)
        target_path = self._safe_log_path(target)
        metadata_path = infer_summary_path(ownship_path)
        data = build_viewer_data(
            ownship_log=ownship_path,
            target_log=target_path,
            metadata_path=metadata_path,
            fallback_end_condition="n/a",
        )
        return viewer_data_to_json(data)

    def load_mesh(self) -> dict:
        """Load the configured F-16 mesh as JSON geometry."""
        return parse_obj_mesh(self.mesh_path)

    def _safe_log_path(self, value: str) -> Path:
        raw = unquote(value)
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = self.logdir / candidate
        resolved = candidate.resolve()
        if not _is_relative_to(resolved, self.logdir):
            raise ValueError("log path must stay inside the configured logdir")
        if not resolved.is_file():
            raise FileNotFoundError(f"log not found: {resolved}")
        return resolved

    def _url_path(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.logdir).as_posix()
        except ValueError:
            return path.name


def make_handler(repository: ViewerRepository):
    """Create a request handler bound to a viewer repository."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            if path.startswith("/api/"):
                self._handle_api(path, query)
                return

            if path == "/":
                path = "/index.html"
            file_path = (STATIC_DIR / path.lstrip("/")).resolve()
            if not _is_relative_to(file_path, STATIC_DIR) or not file_path.is_file():
                self.send_error(404)
                return
            body = file_path.read_bytes()
            mime, _ = mimetypes.guess_type(str(file_path))
            self.send_response(200)
            self.send_header("Content-Type", mime or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _handle_api(self, path: str, query: dict) -> None:
            try:
                if path == "/api/logs":
                    self._json({"logs": repository.list_logs()})
                elif path == "/api/replay":
                    self._json(
                        repository.load_replay(
                            ownship=_query_value(query, "ownship"),
                            target=_query_value(query, "target"),
                        )
                    )
                elif path == "/api/mesh/f16":
                    self._json(repository.load_mesh())
                elif path == "/api/config":
                    self._json(
                        {
                            "envRoot": str(repository.env_root),
                            "logdir": str(repository.logdir),
                            "mesh": str(repository.mesh_path),
                            "defaults": {
                                "wezMinRangeM": DEFAULT_WEZ_MIN_RANGE_M,
                                "wezRangeM": DEFAULT_WEZ_RANGE_M,
                                "wezAngleDeg": DEFAULT_WEZ_ANGLE_DEG,
                            },
                        }
                    )
                else:
                    self._json({"error": "not found"}, status=404)
            except Exception as exc:
                self._json({"error": str(exc)}, status=400)

        def _json(self, data: dict, status: int = 200) -> None:
            body = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def _query_value(query: dict, key: str) -> str:
    value = (query.get(key) or [""])[0]
    if value == "":
        raise ValueError(f"{key} parameter required")
    return str(value)


def _pair_label(ownship: Path) -> str:
    name = ownship.name
    for marker in ("_ownship_(F-16)[Blue].csv", "_ownship_[Blue].csv"):
        if marker in name:
            return name.replace(marker, "")
    return name.replace(".csv", "")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="DogFightEnv web log viewer")
    parser.add_argument(
        "--env-root",
        default=str(DEFAULT_ENV_ROOT),
        help="DogFightEnv environment root containing logs/ and assets/.",
    )
    parser.add_argument(
        "--logdir",
        default=None,
        help="Log directory. Defaults to <env-root>/logs.",
    )
    parser.add_argument(
        "--mesh",
        default=None,
        help="F-16 OBJ mesh path. Defaults to <env-root>/assets/meshes/f16.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7870)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repository = ViewerRepository(
        env_root=Path(args.env_root).expanduser(),
        logdir=Path(args.logdir).expanduser() if args.logdir else None,
        mesh_path=Path(args.mesh).expanduser() if args.mesh else None,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(repository))
    first_url = f"http://{args.host}:{args.port}"
    print(f"Web log viewer: {first_url}")
    print(f"Env root:       {repository.env_root}")
    print(f"Logdir:         {repository.logdir}")
    print(f"Mesh:           {repository.mesh_path}")
    if repository.list_logs():
        first = repository.list_logs()[0]
        query = f"ownship={quote(first['ownship'])}&target={quote(first['target'])}"
        print(f"Latest replay:  {first_url}/?{query}")
    print("Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
```

### `web_log_viewer/static/app.js`

```javascript
import * as THREE from "./vendor/three.module.min.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

const COLORS = {
  own: 0x4d8dff,
  target: 0xff5757,
  ownTrail: 0x003b8e,
  targetTrail: 0x9f0d19,
  ownWez: 0x4d8dff,
  targetWez: 0xff6b6b,
  sea: 0x0969a8,
  sky: 0x7fb7d7,
};

const AIRCRAFT_MODEL_YAW_OFFSET_DEG = 180;
const CAMERA_MODES = new Set(["blue", "red", "midpoint"]);

const State = {
  logs: [],
  replay: null,
  mesh: null,
  playing: true,
  speed: 5,
  simTime: 0,
  lastNow: 0,
  framesRendered: 0,
  showHud: true,
  showSea: true,
  showTrails: true,
  showWez: true,
  cameraMode: "midpoint",
};

const Scene = {
  renderer: null,
  scene: null,
  camera: null,
  controls: null,
  root: null,
  aircraftGeometry: null,
  ownship: null,
  target: null,
  sea: null,
  ownTrail: null,
  targetTrail: null,
  ownWez: null,
  targetWez: null,
};

const $ = id => document.getElementById(id);

window.DogFightViewerDebug = {
  webglOk: false,
  framesRendered: 0,
  activeLogPair: null,
  samples: 0,
};

init().catch(error => {
  console.error(error);
  setStatus(`Startup failed: ${error.message}`);
});

async function init() {
  bindEvents();
  initScene();
  await Promise.all([loadMesh(), refreshLogs()]);
  animate(0);
}

function bindEvents() {
  $("reload-button").addEventListener("click", () => refreshLogs());
  $("play-button").addEventListener("click", () => {
    State.playing = !State.playing;
    $("play-button").textContent = State.playing ? "Pause" : "Play";
  });
  $("log-select").addEventListener("change", event => {
    const index = Number(event.target.value);
    if (Number.isInteger(index) && State.logs[index]) {
      loadReplay(State.logs[index]);
    }
  });
  $("speed-slider").addEventListener("input", event => {
    State.speed = Number(event.target.value);
    $("speed-value").textContent = `${State.speed.toFixed(1)}x`;
  });
  $("timeline").addEventListener("input", event => {
    if (!State.replay) {
      return;
    }
    const ratio = Number(event.target.value);
    State.simTime = lerp(State.replay.startTime, State.replay.endTime, ratio);
    updateFrame();
  });

  bindToggle("toggle-hud", "showHud", updateVisibility);
  bindToggle("toggle-sea", "showSea", updateVisibility);
  bindToggle("toggle-trails", "showTrails", updateVisibility);
  bindToggle("toggle-wez", "showWez", updateVisibility);
  document.querySelectorAll("[data-camera-mode]").forEach(button => {
    button.addEventListener("click", () => setCameraMode(button.dataset.cameraMode));
  });
  updateCameraModeButtons();
  window.addEventListener("resize", resizeRenderer);
}

function bindToggle(id, key, callback) {
  $(id).addEventListener("change", event => {
    State[key] = event.target.checked;
    callback();
  });
}

function setCameraMode(mode) {
  if (!CAMERA_MODES.has(mode)) {
    return;
  }
  State.cameraMode = mode;
  updateCameraModeButtons();
  updateFrame();
}

function updateCameraModeButtons() {
  document.querySelectorAll("[data-camera-mode]").forEach(button => {
    const active = button.dataset.cameraMode === State.cameraMode;
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });
}

function initScene() {
  Scene.root = $("scene-root");
  Scene.scene = new THREE.Scene();
  Scene.scene.background = new THREE.Color(COLORS.sky);
  Scene.scene.fog = new THREE.Fog(COLORS.sky, 6000, 28000);

  Scene.camera = new THREE.PerspectiveCamera(50, 1, 1, 60000);
  Scene.camera.up.set(0, 0, 1);

  Scene.renderer = new THREE.WebGLRenderer({ antialias: true });
  Scene.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  Scene.renderer.outputColorSpace = THREE.SRGBColorSpace;
  Scene.root.appendChild(Scene.renderer.domElement);
  window.DogFightViewerDebug.webglOk = Boolean(Scene.renderer.getContext());

  Scene.controls = new OrbitControls(Scene.camera, Scene.renderer.domElement);
  Scene.controls.enableDamping = true;
  Scene.controls.dampingFactor = 0.08;
  Scene.controls.screenSpacePanning = false;

  Scene.scene.add(new THREE.AmbientLight(0xffffff, 0.62));
  const sun = new THREE.DirectionalLight(0xffffff, 1.25);
  sun.position.set(0.4, -0.6, 1.0).normalize();
  Scene.scene.add(sun);

  resizeRenderer();
}

async function refreshLogs() {
  setStatus("Loading log list...");
  const data = await apiFetch("/api/logs");
  State.logs = data.logs || [];
  renderLogOptions();
  if (State.logs.length === 0) {
    setStatus("No Blue/Red CSV log pairs found.");
    return;
  }
  await loadReplay(State.logs[0]);
}

function renderLogOptions() {
  const select = $("log-select");
  select.innerHTML = "";
  if (State.logs.length === 0) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "No logs";
    select.appendChild(option);
    return;
  }
  State.logs.forEach((log, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = log.label || log.ownshipName || `Replay ${index + 1}`;
    select.appendChild(option);
  });
  select.value = "0";
}

async function loadMesh() {
  State.mesh = await apiFetch("/api/mesh/f16");
  Scene.aircraftGeometry = buildAircraftGeometry(State.mesh);
}

async function loadReplay(logPair) {
  setStatus("Loading replay...");
  const ownship = encodeURIComponent(logPair.ownship);
  const target = encodeURIComponent(logPair.target);
  State.replay = await apiFetch(`/api/replay?ownship=${ownship}&target=${target}`);
  State.simTime = State.replay.startTime;
  State.playing = true;
  $("play-button").textContent = "Pause";
  $("timeline").value = "0";
  window.DogFightViewerDebug.activeLogPair = {
    ownship: State.replay.logs.ownship,
    target: State.replay.logs.target,
  };
  window.DogFightViewerDebug.samples = State.replay.ownship.time.length;
  $("debug-samples").textContent = String(State.replay.ownship.time.length);
  setupReplayScene();
  updateFrame();
  setStatus(`Loaded ${State.replay.logs.ownship}`);
}

function setupReplayScene() {
  clearReplayObjects();
  const replay = State.replay;
  const size = replay.seaSizeM;

  const seaGeometry = new THREE.PlaneGeometry(size, size, 80, 80);
  const positions = seaGeometry.attributes.position;
  for (let i = 0; i < positions.count; i += 1) {
    const x = positions.getX(i);
    const y = positions.getY(i);
    const z = 4 * Math.sin(x / 850) + 2.5 * Math.cos(y / 650);
    positions.setZ(i, THREE.MathUtils.clamp(z, -10, 10));
  }
  positions.needsUpdate = true;
  seaGeometry.computeVertexNormals();
  Scene.sea = new THREE.Mesh(
    seaGeometry,
    new THREE.MeshPhongMaterial({
      color: COLORS.sea,
      transparent: true,
      opacity: 0.86,
      shininess: 22,
      side: THREE.DoubleSide,
    })
  );
  Scene.scene.add(Scene.sea);

  const ownMaterial = new THREE.MeshPhongMaterial({ color: COLORS.own, shininess: 50 });
  const targetMaterial = new THREE.MeshPhongMaterial({
    color: COLORS.target,
    shininess: 50,
  });
  Scene.ownship = new THREE.Mesh(Scene.aircraftGeometry, ownMaterial);
  Scene.target = new THREE.Mesh(Scene.aircraftGeometry, targetMaterial);
  Scene.scene.add(Scene.ownship);
  Scene.scene.add(Scene.target);

  Scene.ownTrail = makeLine(COLORS.ownTrail, 4);
  Scene.targetTrail = makeLine(COLORS.targetTrail, 4);
  Scene.scene.add(Scene.ownTrail);
  Scene.scene.add(Scene.targetTrail);

  Scene.ownWez = makeWezMesh(COLORS.ownWez, 0.14);
  Scene.targetWez = makeWezMesh(COLORS.targetWez, 0.12);
  Scene.scene.add(Scene.ownWez);
  Scene.scene.add(Scene.targetWez);

  setInitialCamera();
  updateVisibility();
}

function clearReplayObjects() {
  for (const key of [
    "ownship",
    "target",
    "sea",
    "ownTrail",
    "targetTrail",
    "ownWez",
    "targetWez",
  ]) {
    const object = Scene[key];
    if (object) {
      Scene.scene.remove(object);
      disposeObject(object);
      Scene[key] = null;
    }
  }
}

function buildAircraftGeometry(mesh) {
  const vertices = [];
  for (const vertex of mesh.vertices) {
    vertices.push(vertex[0], vertex[1], vertex[2]);
  }
  const indices = [];
  for (const triangle of mesh.triangles) {
    indices.push(triangle[0], triangle[1], triangle[2]);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function makeLine(color, width) {
  return new THREE.Line(
    new THREE.BufferGeometry(),
    new THREE.LineBasicMaterial({ color, linewidth: width })
  );
}

function makeWezMesh(color, opacity) {
  return new THREE.Mesh(
    new THREE.BufferGeometry(),
    new THREE.MeshBasicMaterial({
      color,
      transparent: true,
      opacity,
      side: THREE.DoubleSide,
      depthWrite: false,
      wireframe: false,
    })
  );
}

function updateVisibility() {
  $("hud-left").hidden = !State.showHud;
  $("hud-right").hidden = !State.showHud;
  $("hud-bottom").hidden = !State.showHud;
  if (Scene.sea) {
    Scene.sea.visible = State.showSea;
  }
  if (Scene.ownTrail) {
    Scene.ownTrail.visible = State.showTrails;
  }
  if (Scene.targetTrail) {
    Scene.targetTrail.visible = State.showTrails;
  }
  if (Scene.ownWez) {
    Scene.ownWez.visible = State.showWez;
  }
  if (Scene.targetWez) {
    Scene.targetWez.visible = State.showWez;
  }
}

function setInitialCamera() {
  const replay = State.replay;
  const own = replay.ownship.position[0];
  const target = replay.target.position[0];
  const focal = [
    (own[0] + target[0]) / 2,
    (own[1] + target[1]) / 2,
    (own[2] + target[2]) / 2,
  ];
  const scale = Math.max(
    replay.sceneExtentM,
    replay.defaults.wezRangeM * 2.5,
    1500
  );
  Scene.camera.position.set(
    focal[0] + 0.36 * scale,
    focal[1] - 0.5 * scale,
    focal[2] + 0.28 * scale
  );
  Scene.camera.near = 1;
  Scene.camera.far = Math.max(scale * 8, 10000);
  Scene.camera.updateProjectionMatrix();
  Scene.controls.target.set(focal[0], focal[1], focal[2]);
  Scene.controls.update();
}

function animate(now) {
  requestAnimationFrame(animate);
  const dt = State.lastNow ? (now - State.lastNow) / 1000 : 0;
  State.lastNow = now;

  if (State.replay && State.playing) {
    State.simTime += dt * State.speed;
    if (State.simTime > State.replay.endTime) {
      State.simTime = State.replay.startTime;
    }
    updateFrame();
  }
  Scene.controls?.update();
  Scene.renderer?.render(Scene.scene, Scene.camera);
  State.framesRendered += 1;
  window.DogFightViewerDebug.framesRendered = State.framesRendered;
  $("debug-frames").textContent = String(State.framesRendered);
}

function updateFrame() {
  const replay = State.replay;
  if (!replay || !Scene.ownship || !Scene.target) {
    return;
  }
  const ownIndex = nearestIndex(replay.ownship.time, State.simTime);
  const targetIndex = nearestIndex(replay.target.time, State.simTime);
  updateAircraft(Scene.ownship, replay.ownship, ownIndex);
  updateAircraft(Scene.target, replay.target, targetIndex);
  updateTrail(Scene.ownTrail, replay.ownship, State.simTime);
  updateTrail(Scene.targetTrail, replay.target, State.simTime);
  updateWez(Scene.ownWez, replay.ownship, ownIndex);
  updateWez(Scene.targetWez, replay.target, targetIndex);
  updateHud(ownIndex, targetIndex);
  updateFollowCamera(ownIndex, targetIndex);
  updateTimeline();
}

function updateAircraft(object, track, index) {
  const pos = track.position[index];
  const matrix = aircraftVisualMatrix(
    track.rollDeg[index],
    track.pitchDeg[index],
    track.yawDeg[index]
  );
  const rot = new THREE.Matrix4().set(
    matrix[0][0], matrix[0][1], matrix[0][2], 0,
    matrix[1][0], matrix[1][1], matrix[1][2], 0,
    matrix[2][0], matrix[2][1], matrix[2][2], 0,
    0, 0, 0, 1
  );
  object.position.set(pos[0], pos[1], pos[2]);
  object.quaternion.setFromRotationMatrix(rot);
  object.scale.setScalar(State.replay.aircraftDisplayLengthM);
}

function aircraftVisualMatrix(rollDeg, pitchDeg, yawDeg) {
  const bodyMatrix = attitudeMatrix(rollDeg, pitchDeg, yawDeg);
  if (AIRCRAFT_MODEL_YAW_OFFSET_DEG === 0) {
    return bodyMatrix;
  }
  return matmul3(
    bodyMatrix,
    zRotationMatrix(AIRCRAFT_MODEL_YAW_OFFSET_DEG)
  );
}

function updateFollowCamera(ownIndex, targetIndex) {
  if (!Scene.camera || !Scene.controls) {
    return;
  }
  const focal = cameraFocalPoint(ownIndex, targetIndex);
  const delta = focal.clone().sub(Scene.controls.target);
  if (delta.lengthSq() <= 1e-8) {
    return;
  }
  Scene.camera.position.add(delta);
  Scene.controls.target.copy(focal);
  Scene.controls.update();
}

function cameraFocalPoint(ownIndex, targetIndex) {
  const replay = State.replay;
  const own = replay.ownship.position[ownIndex];
  const target = replay.target.position[targetIndex];
  if (State.cameraMode === "blue") {
    return new THREE.Vector3(own[0], own[1], own[2]);
  }
  if (State.cameraMode === "red") {
    return new THREE.Vector3(target[0], target[1], target[2]);
  }
  return new THREE.Vector3(
    (own[0] + target[0]) / 2,
    (own[1] + target[1]) / 2,
    (own[2] + target[2]) / 2
  );
}

function updateTrail(line, track, simTime) {
  if (!line) {
    return;
  }
  const startTime = simTime - State.replay.defaults.trailSeconds;
  const start = lowerBound(track.time, startTime);
  const end = upperBound(track.time, simTime);
  const points = [];
  for (let i = start; i < end; i += 1) {
    const p = track.position[i];
    points.push(new THREE.Vector3(p[0], p[1], p[2]));
  }
  line.geometry.dispose();
  line.geometry = new THREE.BufferGeometry().setFromPoints(points);
}

function updateWez(mesh, track, index) {
  if (!mesh) {
    return;
  }
  const pos = track.position[index];
  const forward = forwardVector(track.yawDeg[index], track.pitchDeg[index]);
  mesh.geometry.dispose();
  mesh.geometry = buildWezGeometry(
    new THREE.Vector3(pos[0], pos[1], pos[2]),
    new THREE.Vector3(forward[0], forward[1], forward[2]),
    State.replay.defaults.wezMinRangeM,
    State.replay.defaults.wezRangeM,
    State.replay.defaults.wezAngleDeg
  );
}

function buildWezGeometry(nose, direction, minRange, maxRange, angleDeg) {
  const dir = direction.lengthSq() > 0 ? direction.clone().normalize() : new THREE.Vector3(1, 0, 0);
  const nearRange = Math.max(0, minRange);
  const farRange = Math.max(nearRange, maxRange);
  const halfAngle = THREE.MathUtils.degToRad(angleDeg / 2);
  const nearRadius = nearRange * Math.tan(halfAngle);
  const farRadius = farRange * Math.tan(halfAngle);
  let ref = new THREE.Vector3(0, 0, 1);
  if (Math.abs(dir.dot(ref)) > 0.98) {
    ref = new THREE.Vector3(0, 1, 0);
  }
  const side = new THREE.Vector3().crossVectors(dir, ref).normalize();
  const up = new THREE.Vector3().crossVectors(side, dir).normalize();
  const resolution = 48;
  const nearCenter = nose.clone().addScaledVector(dir, nearRange);
  const farCenter = nose.clone().addScaledVector(dir, farRange);
  const vertices = [];
  const indices = [];

  for (let step = 0; step < resolution; step += 1) {
    const theta = (2 * Math.PI * step) / resolution;
    const radial = side.clone().multiplyScalar(Math.cos(theta))
      .add(up.clone().multiplyScalar(Math.sin(theta)));
    const nearPoint = nearCenter.clone().addScaledVector(radial, nearRadius);
    const farPoint = farCenter.clone().addScaledVector(radial, farRadius);
    vertices.push(nearPoint.x, nearPoint.y, nearPoint.z);
    vertices.push(farPoint.x, farPoint.y, farPoint.z);
  }

  for (let step = 0; step < resolution; step += 1) {
    const next = (step + 1) % resolution;
    const nearA = step * 2;
    const farA = nearA + 1;
    const nearB = next * 2;
    const farB = nearB + 1;
    indices.push(nearA, nearB, farB, nearA, farB, farA);
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function updateHud(ownIndex, targetIndex) {
  const replay = State.replay;
  const own = replay.ownship;
  const target = replay.target;
  const ownPos = own.position[ownIndex];
  const targetPos = target.position[targetIndex];
  const relative = sub(targetPos, ownPos);
  const distance = norm(relative);
  const ownForward = forwardVector(own.yawDeg[ownIndex], own.pitchDeg[ownIndex]);
  const targetForward = forwardVector(target.yawDeg[targetIndex], target.pitchDeg[targetIndex]);
  const ownAta = angleBetweenDeg(ownForward, relative);
  const targetAta = angleBetweenDeg(targetForward, scale(relative, -1));
  const ownAa = angleBetweenDeg(targetForward, scale(relative, -1));
  const ownSpeed = speedAt(own, ownIndex);
  const targetSpeed = speedAt(target, targetIndex);
  const closure = distance > 0
    ? -dot(relative, sub(velocityAt(target, targetIndex), velocityAt(own, ownIndex))) / distance
    : 0;
  const ownWez = inWez(distance, ownAta);
  const targetWez = inWez(distance, targetAta);
  const state = State.playing ? "PLAY" : "PAUSE";

  $("hud-left").textContent =
    `${state}  t=${State.simTime.toFixed(2)}s  x${State.speed.toFixed(1)}\n` +
    `Own  alt=${fmt0(ownPos[2])}m  v=${fmt1(ownSpeed)}m/s  hp=${fmtHealth(own.health[ownIndex])}\n` +
    `Tgt  alt=${fmt0(targetPos[2])}m  v=${fmt1(targetSpeed)}m/s  hp=${fmtHealth(target.health[targetIndex])}`;
  $("hud-right").textContent =
    `Range      ${fmt0(distance)} m\n` +
    `Closure    ${fmt1(closure)} m/s\n` +
    `Rel Alt    ${fmt0(targetPos[2] - ownPos[2])} m\n` +
    `Own ATA    ${fmt1(ownAta)} deg\n` +
    `Target AA  ${fmt1(ownAa)} deg\n` +
    `Own WEZ    ${ownWez ? "IN" : "out"}\n` +
    `Threat     ${targetWez ? "IN" : "out"}`;
  $("hud-right").style.color = targetWez ? "#ff6b6b" : ownWez ? "#f3b34c" : "#eef3f7";
  $("hud-bottom").textContent =
    `${replay.logs.ownship}\n${replay.logs.target}\nEnd: ${replay.endCondition}`;

  $("time-readout").textContent = `${State.simTime.toFixed(2)}s`;
  $("range-readout").textContent = `${fmt0(distance)} m`;
  $("closure-readout").textContent = `${fmt1(closure)} m/s`;
  $("relalt-readout").textContent = `${fmt0(targetPos[2] - ownPos[2])} m`;
  $("log-info").textContent = JSON.stringify({
    ownship: replay.logs.ownship,
    target: replay.logs.target,
    metadata: replay.logs.metadata,
    end: replay.endCondition,
  }, null, 2);
}

function updateTimeline() {
  const replay = State.replay;
  const denom = replay.endTime - replay.startTime;
  const ratio = denom > 0 ? (State.simTime - replay.startTime) / denom : 0;
  $("timeline").value = String(THREE.MathUtils.clamp(ratio, 0, 1));
}

function resizeRenderer() {
  if (!Scene.renderer || !Scene.camera || !Scene.root) {
    return;
  }
  const rect = Scene.root.getBoundingClientRect();
  const width = Math.max(1, Math.floor(rect.width));
  const height = Math.max(1, Math.floor(rect.height));
  Scene.renderer.setSize(width, height, false);
  Scene.camera.aspect = width / height;
  Scene.camera.updateProjectionMatrix();
  $("debug-webgl").textContent = window.DogFightViewerDebug.webglOk ? "ok" : "fail";
}

async function apiFetch(path) {
  const response = await fetch(path, { cache: "no-store" });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || response.statusText);
  }
  return data;
}

function setStatus(message) {
  $("status-text").textContent = message;
}

function disposeObject(object) {
  object.traverse?.(child => {
    child.geometry?.dispose?.();
    if (Array.isArray(child.material)) {
      child.material.forEach(material => material.dispose?.());
    } else {
      child.material?.dispose?.();
    }
  });
}

function nearestIndex(times, value) {
  return Math.max(0, Math.min(upperBound(times, value) - 1, times.length - 1));
}

function lowerBound(values, target) {
  let low = 0;
  let high = values.length;
  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (values[mid] < target) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  return low;
}

function upperBound(values, target) {
  let low = 0;
  let high = values.length;
  while (low < high) {
    const mid = Math.floor((low + high) / 2);
    if (values[mid] <= target) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  return low;
}

function attitudeMatrix(rollDeg, pitchDeg, yawDeg) {
  const roll = THREE.MathUtils.degToRad(rollDeg);
  const pitch = THREE.MathUtils.degToRad(pitchDeg);
  const yaw = THREE.MathUtils.degToRad(90 - yawDeg);
  const cr = Math.cos(roll);
  const sr = Math.sin(roll);
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const rotX = [[1, 0, 0], [0, cr, -sr], [0, sr, cr]];
  const rotY = [[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]];
  const rotZ = [[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]];
  return matmul3(matmul3(rotZ, rotY), rotX);
}

function zRotationMatrix(deg) {
  const rad = THREE.MathUtils.degToRad(deg);
  const c = Math.cos(rad);
  const s = Math.sin(rad);
  return [[c, -s, 0], [s, c, 0], [0, 0, 1]];
}

function matmul3(a, b) {
  const out = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  for (let row = 0; row < 3; row += 1) {
    for (let col = 0; col < 3; col += 1) {
      out[row][col] = a[row][0] * b[0][col] +
        a[row][1] * b[1][col] +
        a[row][2] * b[2][col];
    }
  }
  return out;
}

function forwardVector(yawDeg, pitchDeg) {
  const matrix = attitudeMatrix(0, pitchDeg, yawDeg);
  const direction = [matrix[0][0], matrix[1][0], matrix[2][0]];
  const length = norm(direction);
  return length > 0 ? scale(direction, 1 / length) : [1, 0, 0];
}

function speedAt(track, index) {
  if (track.time.length < 2) {
    return 0;
  }
  const prev = Math.max(0, index - 1);
  const next = Math.min(track.time.length - 1, index + 1);
  const dt = track.time[next] - track.time[prev];
  return dt > 0 ? norm(sub(track.position[next], track.position[prev])) / dt : 0;
}

function velocityAt(track, index) {
  if (track.time.length < 2) {
    return [0, 0, 0];
  }
  const prev = Math.max(0, index - 1);
  const next = Math.min(track.time.length - 1, index + 1);
  const dt = track.time[next] - track.time[prev];
  return dt > 0 ? scale(sub(track.position[next], track.position[prev]), 1 / dt) : [0, 0, 0];
}

function angleBetweenDeg(first, second) {
  const firstNorm = norm(first);
  const secondNorm = norm(second);
  if (firstNorm <= 0 || secondNorm <= 0) {
    return 0;
  }
  const cosine = THREE.MathUtils.clamp(dot(first, second) / (firstNorm * secondNorm), -1, 1);
  return THREE.MathUtils.radToDeg(Math.acos(cosine));
}

function inWez(rangeM, ataDeg) {
  const defs = State.replay.defaults;
  return rangeM >= defs.wezMinRangeM &&
    rangeM <= defs.wezRangeM &&
    ataDeg <= Math.max(0, defs.wezAngleDeg / 2);
}

function sub(first, second) {
  return [first[0] - second[0], first[1] - second[1], first[2] - second[2]];
}

function scale(vector, scalar) {
  return [vector[0] * scalar, vector[1] * scalar, vector[2] * scalar];
}

function dot(first, second) {
  return first[0] * second[0] + first[1] * second[1] + first[2] * second[2];
}

function norm(vector) {
  return Math.sqrt(dot(vector, vector));
}

function lerp(start, end, ratio) {
  return start + (end - start) * ratio;
}

function fmt0(value) {
  return Number.isFinite(value) ? value.toFixed(0).padStart(6, " ") : "n/a";
}

function fmt1(value) {
  return Number.isFinite(value) ? value.toFixed(1).padStart(6, " ") : "n/a";
}

function fmtHealth(value) {
  return value === null || value === undefined ? "n/a" : Number(value).toFixed(3);
}
```

### `web_log_viewer/static/index.html`

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DogFight Log Playback</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <header class="topbar">
    <div class="brand">DogFight Log Playback</div>
    <select id="log-select" aria-label="Replay log"></select>
    <button id="reload-button" type="button" title="Reload logs">Reload</button>
    <button id="play-button" type="button" title="Play or pause">Pause</button>
    <label class="speed-control">
      <span>Speed</span>
      <input id="speed-slider" type="range" min="0" max="20" step="0.5" value="5">
      <span id="speed-value">5.0x</span>
    </label>
    <span id="status-text">Loading...</span>
  </header>

  <main class="viewer-shell">
    <section class="scene-panel">
      <div id="scene-root" class="scene-root"></div>
      <div id="hud-left" class="hud hud-left"></div>
      <div id="hud-right" class="hud hud-right"></div>
      <div id="hud-bottom" class="hud hud-bottom"></div>
    </section>

    <aside class="side-panel">
      <div class="section-title">Display</div>
      <label class="toggle"><input id="toggle-hud" type="checkbox" checked> HUD</label>
      <label class="toggle"><input id="toggle-sea" type="checkbox" checked> Sea</label>
      <label class="toggle"><input id="toggle-trails" type="checkbox" checked> Trails</label>
      <label class="toggle"><input id="toggle-wez" type="checkbox" checked> WEZ</label>

      <div class="section-title">View</div>
      <div class="camera-mode-group" role="group" aria-label="Camera follow mode">
        <button class="camera-mode-button" type="button" data-camera-mode="blue">Blue</button>
        <button class="camera-mode-button" type="button" data-camera-mode="red">Red</button>
        <button class="camera-mode-button" type="button" data-camera-mode="midpoint">Center</button>
      </div>

      <div class="section-title">Replay</div>
      <input id="timeline" class="timeline" type="range" min="0" max="1" step="0.001" value="0">
      <div class="readout-grid">
        <span>Time</span><strong id="time-readout">0.00s</strong>
        <span>Range</span><strong id="range-readout">n/a</strong>
        <span>Closure</span><strong id="closure-readout">n/a</strong>
        <span>Rel Alt</span><strong id="relalt-readout">n/a</strong>
      </div>

      <div class="section-title">Logs</div>
      <pre id="log-info" class="log-info"></pre>

      <div class="section-title">Debug</div>
      <div class="debug-grid">
        <span>WebGL</span><strong id="debug-webgl">n/a</strong>
        <span>Frames</span><strong id="debug-frames">0</strong>
        <span>Samples</span><strong id="debug-samples">0</strong>
      </div>
    </aside>
  </main>

  <script type="module" src="/app.js"></script>
</body>
</html>
```

### `web_log_viewer/static/style.css`

```css
:root {
  color-scheme: dark;
  --bg: #111315;
  --panel: #171b1f;
  --panel-2: #20262b;
  --line: #303941;
  --text: #eef3f7;
  --muted: #9aa7b0;
  --blue: #4d8dff;
  --red: #ff5757;
  --sea: #0969a8;
  --warn: #f3b34c;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-height: 100vh;
  overflow: hidden;
  background: var(--bg);
  color: var(--text);
  font-family: "Segoe UI", Arial, sans-serif;
  letter-spacing: 0;
}

button,
input,
select {
  font: inherit;
}

.topbar {
  display: grid;
  grid-template-columns: auto minmax(220px, 380px) auto auto minmax(210px, 280px) 1fr;
  gap: 10px;
  align-items: center;
  min-height: 58px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--line);
  background: rgba(17, 19, 21, 0.98);
}

.brand {
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
}

button,
select {
  min-height: 34px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--panel-2);
  color: var(--text);
}

button {
  padding: 0 12px;
  cursor: pointer;
}

button:hover {
  border-color: var(--blue);
}

.speed-control {
  display: grid;
  grid-template-columns: auto 1fr 46px;
  gap: 8px;
  align-items: center;
  color: var(--muted);
}

#status-text {
  min-width: 0;
  color: var(--muted);
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.viewer-shell {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  height: calc(100vh - 58px);
}

.scene-panel {
  position: relative;
  min-width: 0;
  min-height: 0;
  background: #07090a;
}

.scene-root {
  position: absolute;
  inset: 0;
}

.scene-root canvas {
  display: block;
  width: 100%;
  height: 100%;
}

.hud {
  position: absolute;
  z-index: 1;
  padding: 8px 10px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 6px;
  background: rgba(10, 12, 14, 0.56);
  color: var(--text);
  font-size: 13px;
  line-height: 1.4;
  white-space: pre;
  pointer-events: none;
  text-shadow: 0 1px 2px #000;
}

.hud-left {
  top: 14px;
  left: 14px;
}

.hud-right {
  top: 14px;
  right: 14px;
  text-align: right;
}

.hud-bottom {
  right: 14px;
  bottom: 14px;
  max-width: min(720px, calc(100% - 28px));
  overflow: hidden;
  text-overflow: ellipsis;
}

.side-panel {
  min-width: 0;
  overflow: auto;
  border-left: 1px solid var(--line);
  background: var(--panel);
  padding: 14px;
}

.section-title {
  margin: 12px 0 8px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

.toggle {
  display: grid;
  grid-template-columns: 18px 1fr;
  gap: 8px;
  align-items: center;
  min-height: 30px;
  color: var(--text);
}

.camera-mode-group {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
}

.camera-mode-button {
  min-width: 0;
  padding: 0 8px;
}

.camera-mode-button.active {
  border-color: var(--blue);
  background: rgba(77, 141, 255, 0.18);
  color: #ffffff;
}

.timeline {
  width: 100%;
}

.readout-grid,
.debug-grid {
  display: grid;
  grid-template-columns: 82px 1fr;
  gap: 6px 10px;
  align-items: center;
  color: var(--muted);
}

.readout-grid strong,
.debug-grid strong {
  min-width: 0;
  color: var(--text);
  overflow-wrap: anywhere;
}

.log-info {
  max-height: 220px;
  margin: 0;
  padding: 10px;
  overflow: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #101316;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
  white-space: pre-wrap;
}

@media (max-width: 900px) {
  body {
    overflow: auto;
  }

  .topbar {
    grid-template-columns: 1fr 1fr;
    min-height: auto;
  }

  .brand,
  #status-text,
  .speed-control {
    grid-column: 1 / -1;
  }

  .viewer-shell {
    grid-template-columns: 1fr;
    height: auto;
  }

  .scene-panel {
    height: 64vh;
  }

  .side-panel {
    border-left: 0;
    border-top: 1px solid var(--line);
  }

  .hud {
    font-size: 11px;
    max-width: calc(100% - 28px);
  }
}
```

### `web_log_viewer/static/vendor/THREE_LICENSE.txt`

```text
The MIT License

Copyright © 2010-2024 three.js authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

### `web_log_viewer/tests/test_log_data.py`

```python
"""Unit tests for web log viewer parser and tactical math."""

from __future__ import annotations

import math
import unittest
from pathlib import Path

from log_data import (
    angle_between_deg,
    build_viewer_data,
    discover_log_pairs,
    forward_vector,
    in_wez,
    nearest_index,
    tactical_snapshot,
)


class LogDataTest(unittest.TestCase):
    def test_pair_discovery_and_replay_math(self) -> None:
        env_root = Path(__file__).resolve().parents[3] / "MyTrainEnv"
        logdir = env_root / "logs"
        pairs = discover_log_pairs(logdir)
        self.assertGreaterEqual(len(pairs), 1)

        ownship, target = pairs[0]
        data = build_viewer_data(ownship, target, None)
        self.assertEqual(nearest_index(data.ownship, 0.5), 29)
        self.assertGreater(nearest_index(data.ownship, 1.2), 0)
        snapshot = tactical_snapshot(data.ownship, data.target, 0.0)
        self.assertGreater(snapshot["distance_m"], 50.0)
        self.assertLess(abs(snapshot["relative_alt_m"]), 200.0)

    def test_vectors_and_wez_contract(self) -> None:
        forward = forward_vector(yaw_deg=90.0, pitch_deg=0.0)
        self.assertAlmostEqual(forward[0], 1.0, places=6)
        self.assertAlmostEqual(forward[1], 0.0, places=6)
        self.assertTrue(math.isclose(angle_between_deg((1, 0, 0), (0, 1, 0)), 90.0))
        self.assertTrue(in_wez(500.0, 0.5, 100.0, 1000.0, 2.0))
        self.assertFalse(in_wez(50.0, 0.5, 100.0, 1000.0, 2.0))
        self.assertFalse(in_wez(500.0, 2.0, 100.0, 1000.0, 2.0))


if __name__ == "__main__":
    unittest.main()
```
