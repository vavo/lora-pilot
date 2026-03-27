package launcher

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"
)

var ErrRebootRequired = errors.New("wsl setup requires a Windows reboot; rerun install --resume afterwards")

type Status struct {
	InstallPresent         bool   `json:"install_present"`
	DistroPresent          bool   `json:"distro_present"`
	ControlPilotReachable  bool   `json:"controlpilot_reachable"`
	AppVersion             string `json:"app_version"`
	RuntimeVersion         string `json:"runtime_version"`
	InstallPath            string `json:"install_path"`
	LastStatus             string `json:"last_status"`
	PendingResumeStep      string `json:"pending_resume_step"`
}

type Options struct {
	Paths         Paths
	DistroName    string
	ManifestURL   string
	Executor      Executor
	HTTPClient    *http.Client
	Now           func() time.Time
	HealthTimeout time.Duration
	PollInterval  time.Duration
}

type Launcher struct {
	paths         Paths
	distroName    string
	manifestURL   string
	exec          Executor
	httpClient    *http.Client
	now           func() time.Time
	healthTimeout time.Duration
	pollInterval  time.Duration
}

func New(opts Options) *Launcher {
	paths := opts.Paths
	if paths.BaseDir == "" {
		paths = DefaultPaths()
	}
	distroName := opts.DistroName
	if distroName == "" {
		distroName = "LoRAPilot"
	}
	executor := opts.Executor
	if executor == nil {
		executor = OSExecutor{}
	}
	httpClient := opts.HTTPClient
	if httpClient == nil {
		httpClient = &http.Client{Timeout: 10 * time.Second}
	}
	now := opts.Now
	if now == nil {
		now = time.Now
	}
	healthTimeout := opts.HealthTimeout
	if healthTimeout <= 0 {
		healthTimeout = 3 * time.Minute
	}
	pollInterval := opts.PollInterval
	if pollInterval <= 0 {
		pollInterval = 2 * time.Second
	}
	return &Launcher{
		paths:         paths,
		distroName:    distroName,
		manifestURL:   opts.ManifestURL,
		exec:          executor,
		httpClient:    httpClient,
		now:           now,
		healthTimeout: healthTimeout,
		pollInterval:  pollInterval,
	}
}

func (l *Launcher) Install(ctx context.Context, resume bool) error {
	if err := l.requireWindows(); err != nil {
		return err
	}
	if err := l.paths.Ensure(); err != nil {
		return fmt.Errorf("prepare local directories: %w", err)
	}

	state, err := LoadState(l.paths.StatePath)
	if err != nil {
		return err
	}
	if state.DistroName == "" {
		state.DistroName = l.distroName
	}
	if !resume && state.PendingResumeStep != "" {
		return fmt.Errorf("installation is waiting on %q; rerun install --resume after completing that step", state.PendingResumeStep)
	}

	manifest, err := l.loadManifest(ctx)
	if err != nil {
		return err
	}
	if err := l.validateWindowsBuild(ctx, manifest.MinWindowsBuild); err != nil {
		return err
	}
	if err := l.ensureWSL(ctx, &state); err != nil {
		_ = SaveState(l.paths.StatePath, state)
		return err
	}

	distroPresent, err := l.distroExists(ctx, state.DistroName)
	if err != nil {
		return err
	}

	if distroPresent {
		if state.InstallPath == "" {
			state.InstallPath = l.paths.DistroPath(state.DistroName)
		}
		if err := l.applyOverlay(ctx, state.DistroName, manifest); err != nil {
			return err
		}
	} else {
		installPath := l.paths.DistroPath(state.DistroName)
		if err := l.importFreshRuntime(ctx, state.DistroName, installPath, manifest); err != nil {
			return err
		}
		state.InstallPath = installPath
		state.InstalledAt = l.now().UTC().Format(time.RFC3339)
	}

	state.AppVersion = manifest.AppVersion
	state.RuntimeVersion = manifest.RuntimeVersion
	state.LastStatus = "installed"
	state.PendingResumeStep = ""
	if err := SaveState(l.paths.StatePath, state); err != nil {
		return err
	}
	return nil
}

func (l *Launcher) Start(ctx context.Context) error {
	if err := l.requireWindows(); err != nil {
		return err
	}
	state, err := LoadState(l.paths.StatePath)
	if err != nil {
		return err
	}
	if state.DistroName == "" {
		return fmt.Errorf("LoRA Pilot is not installed")
	}

	manifest, _ := l.loadCachedManifest()
	if manifest.Ports.ControlPilot == 0 {
		manifest = DefaultManifest()
	}
	controlPilotURL := fmt.Sprintf("http://127.0.0.1:%d", manifest.Ports.ControlPilot)
	healthURL := controlPilotURL + "/healthz"
	if ok := l.isHealthy(ctx, healthURL); ok {
		return l.openBrowser(ctx, controlPilotURL)
	}

	conflicts, err := FindConflictingPorts([]int{
		manifest.Ports.ControlPilot,
		manifest.Ports.Jupyter,
		manifest.Ports.CodeServer,
		manifest.Ports.ComfyUI,
		manifest.Ports.Kohya,
		manifest.Ports.TensorBoard,
		manifest.Ports.InvokeAI,
		manifest.Ports.AIToolkit,
	})
	if err != nil {
		return err
	}
	if len(conflicts) > 0 {
		return fmt.Errorf("required localhost ports already in use: %v", conflicts)
	}

	if _, err := l.exec.Run(ctx, BuildWSLExecCommand(state.DistroName, "root", "/opt/pilot/wsl-start.sh")); err != nil {
		return err
	}
	if err := l.waitForHealth(ctx, healthURL, l.healthTimeout); err != nil {
		return err
	}

	state.LastStatus = "running"
	state.LastStartOKAt = l.now().UTC().Format(time.RFC3339)
	if err := SaveState(l.paths.StatePath, state); err != nil {
		return err
	}
	return l.openBrowser(ctx, controlPilotURL)
}

func (l *Launcher) Stop(ctx context.Context) error {
	if err := l.requireWindows(); err != nil {
		return err
	}
	state, err := LoadState(l.paths.StatePath)
	if err != nil {
		return err
	}
	if state.DistroName == "" {
		return fmt.Errorf("LoRA Pilot is not installed")
	}
	if _, err := l.exec.Run(ctx, BuildWSLExecCommand(state.DistroName, "root", "/opt/pilot/wsl-stop.sh")); err != nil {
		return err
	}
	state.LastStatus = "stopped"
	return SaveState(l.paths.StatePath, state)
}

func (l *Launcher) Status(ctx context.Context) (Status, error) {
	state, err := LoadState(l.paths.StatePath)
	if err != nil {
		return Status{}, err
	}
	manifest, _ := l.loadCachedManifest()
	if manifest.Ports.ControlPilot == 0 {
		manifest = DefaultManifest()
	}

	status := Status{
		InstallPresent:    state.DistroName != "",
		DistroPresent:     state.DistroName != "",
		ControlPilotReachable: l.isHealthy(ctx, fmt.Sprintf("http://127.0.0.1:%d/healthz", manifest.Ports.ControlPilot)),
		AppVersion:        state.AppVersion,
		RuntimeVersion:    state.RuntimeVersion,
		InstallPath:       state.InstallPath,
		LastStatus:        state.LastStatus,
		PendingResumeStep: state.PendingResumeStep,
	}
	if runtime.GOOS == "windows" && state.DistroName != "" {
		present, err := l.distroExists(ctx, state.DistroName)
		if err != nil {
			return Status{}, err
		}
		status.DistroPresent = present
	}
	return status, nil
}

func (l *Launcher) Open(ctx context.Context) error {
	manifest, _ := l.loadCachedManifest()
	if manifest.Ports.ControlPilot == 0 {
		manifest = DefaultManifest()
	}
	targetURL := fmt.Sprintf("http://127.0.0.1:%d", manifest.Ports.ControlPilot)
	if !l.isHealthy(ctx, targetURL+"/healthz") {
		return fmt.Errorf("ControlPilot is not reachable; start LoRA Pilot first")
	}
	return l.openBrowser(ctx, targetURL)
}

func (l *Launcher) Uninstall(ctx context.Context, purge bool) error {
	if err := l.requireWindows(); err != nil {
		return err
	}
	state, err := LoadState(l.paths.StatePath)
	if err != nil {
		return err
	}
	if purge && state.DistroName != "" {
		if _, err := l.exec.Run(ctx, BuildWSLUnregisterCommand(state.DistroName)); err != nil {
			return err
		}
	}
	if purge {
		return os.RemoveAll(l.paths.BaseDir)
	}
	for _, path := range []string{l.paths.StatePath, l.paths.CachedManifestPath} {
		_ = os.Remove(path)
	}
	state.LastStatus = "uninstalled"
	state.PendingResumeStep = ""
	return SaveState(l.paths.StatePath, state)
}

func WriteStatus(w io.Writer, status Status, asJSON bool) error {
	if asJSON {
		raw, err := json.MarshalIndent(status, "", "  ")
		if err != nil {
			return err
		}
		_, err = fmt.Fprintln(w, string(raw))
		return err
	}
	_, err := fmt.Fprintf(
		w,
		"installed=%t\ndistro_present=%t\ncontrolpilot_reachable=%t\napp_version=%s\nruntime_version=%s\ninstall_path=%s\nlast_status=%s\npending_resume_step=%s\n",
		status.InstallPresent,
		status.DistroPresent,
		status.ControlPilotReachable,
		status.AppVersion,
		status.RuntimeVersion,
		status.InstallPath,
		status.LastStatus,
		status.PendingResumeStep,
	)
	return err
}

func (l *Launcher) importFreshRuntime(ctx context.Context, distroName, installPath string, manifest Manifest) error {
	artifactPath := filepath.Join(l.paths.DownloadsDir, filepath.Base(manifest.FreshInstall.URL))
	if err := DownloadFile(ctx, l.httpClient, manifest.FreshInstall.URL, artifactPath); err != nil {
		return err
	}
	if err := VerifySHA256File(artifactPath, manifest.FreshInstall.SHA256); err != nil {
		return err
	}

	importPath := artifactPath
	if strings.HasSuffix(strings.ToLower(artifactPath), ".zst") {
		importPath = strings.TrimSuffix(artifactPath, ".zst")
		if err := DecompressZstdFile(artifactPath, importPath); err != nil {
			return err
		}
	}
	if err := os.MkdirAll(installPath, 0o755); err != nil {
		return fmt.Errorf("create distro install dir: %w", err)
	}
	_, err := l.exec.Run(ctx, BuildWSLImportCommand(distroName, installPath, importPath))
	return err
}

func (l *Launcher) applyOverlay(ctx context.Context, distroName string, manifest Manifest) error {
	artifactPath := filepath.Join(l.paths.DownloadsDir, filepath.Base(manifest.UpgradeOverlay.URL))
	if err := DownloadFile(ctx, l.httpClient, manifest.UpgradeOverlay.URL, artifactPath); err != nil {
		return err
	}
	if err := VerifySHA256File(artifactPath, manifest.UpgradeOverlay.SHA256); err != nil {
		return err
	}
	wslPath, err := ToWSLPath(artifactPath)
	if err != nil {
		return err
	}
	_, _ = l.exec.Run(ctx, BuildWSLExecCommand(distroName, "root", "/opt/pilot/wsl-stop.sh || true"))
	command := fmt.Sprintf("/opt/pilot/wsl-apply-update.sh %q %q", wslPath, manifest.RuntimeVersion)
	_, err = l.exec.Run(ctx, BuildWSLExecCommand(distroName, "root", command))
	return err
}

func (l *Launcher) loadManifest(ctx context.Context) (Manifest, error) {
	source := l.manifestURL
	if source == "" {
		source = os.Getenv("LORA_PILOT_MANIFEST_URL")
	}
	if source == "" {
		return l.loadCachedManifest()
	}
	if err := DownloadFile(ctx, l.httpClient, source, l.paths.CachedManifestPath); err != nil {
		return Manifest{}, err
	}
	return l.loadCachedManifest()
}

func (l *Launcher) loadCachedManifest() (Manifest, error) {
	file, err := os.Open(l.paths.CachedManifestPath)
	if err != nil {
		return Manifest{}, fmt.Errorf("open cached manifest: %w", err)
	}
	defer file.Close()
	return LoadManifest(file)
}

func (l *Launcher) ensureWSL(ctx context.Context, state *State) error {
	if _, err := l.exec.Run(ctx, BuildWSLStatusCommand()); err == nil {
		state.PendingResumeStep = ""
		return nil
	}
	if _, err := l.exec.Run(ctx, BuildWSLInstallCommand()); err != nil {
		return fmt.Errorf("WSL is not available and automatic setup failed: %w", err)
	}
	state.PendingResumeStep = "resume-install"
	state.LastStatus = "reboot-required"
	return ErrRebootRequired
}

func (l *Launcher) validateWindowsBuild(ctx context.Context, minBuild int) error {
	output, err := l.exec.Run(ctx, BuildWindowsBuildCommand())
	if err != nil {
		return fmt.Errorf("check Windows build: %w", err)
	}
	build, err := strconv.Atoi(strings.TrimSpace(output))
	if err != nil {
		return fmt.Errorf("parse Windows build %q: %w", output, err)
	}
	if build < minBuild {
		return fmt.Errorf("Windows build %d is below the supported minimum %d", build, minBuild)
	}
	return nil
}

func (l *Launcher) distroExists(ctx context.Context, distroName string) (bool, error) {
	output, err := l.exec.Run(ctx, BuildWSLListCommand())
	if err != nil {
		return false, err
	}
	for _, line := range strings.Split(output, "\n") {
		if strings.EqualFold(strings.TrimSpace(line), distroName) {
			return true, nil
		}
	}
	return false, nil
}

func (l *Launcher) waitForHealth(ctx context.Context, targetURL string, timeout time.Duration) error {
	deadline := l.now().Add(timeout)
	for l.now().Before(deadline) {
		if l.isHealthy(ctx, targetURL) {
			return nil
		}
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(l.pollInterval):
		}
	}
	return fmt.Errorf("ControlPilot did not become healthy before timeout")
}

func (l *Launcher) isHealthy(ctx context.Context, targetURL string) bool {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, targetURL, nil)
	if err != nil {
		return false
	}
	resp, err := l.httpClient.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	return resp.StatusCode == http.StatusOK
}

func (l *Launcher) openBrowser(ctx context.Context, targetURL string) error {
	_, err := l.exec.Run(ctx, BuildOpenBrowserCommand(targetURL))
	return err
}

func (l *Launcher) requireWindows() error {
	if runtime.GOOS != "windows" {
		return fmt.Errorf("this command can only run on Windows")
	}
	return nil
}
