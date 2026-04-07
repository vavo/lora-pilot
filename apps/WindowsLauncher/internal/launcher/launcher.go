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
var ErrSetupResumeScheduled = errors.New("setup will resume automatically after reboot")

const SetupResumeScheduledExitCode = 42
const resumeRunOnceValueName = "LoRAPilotSetupResume"

type Status struct {
	InstallPresent        bool   `json:"install_present"`
	DistroPresent         bool   `json:"distro_present"`
	ControlPilotReachable bool   `json:"controlpilot_reachable"`
	AppVersion            string `json:"app_version"`
	RuntimeVersion        string `json:"runtime_version"`
	InstallPath           string `json:"install_path"`
	LastStatus            string `json:"last_status"`
	PendingResumeStep     string `json:"pending_resume_step"`
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
	progress      *ProgressWriter
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
		progress:      NewProgressWriter(paths.InstallProgressPath, now),
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

	l.updateProgress("manifest", "Loading runtime manifest...", 5, true, "Resolving installer metadata.", 0, 0)
	manifest, err := l.loadManifest(ctx)
	if err != nil {
		return err
	}
	l.updateProgress("compatibility", "Checking Windows compatibility...", 8, true, "", 0, 0)
	if err := l.validateWindowsBuild(ctx, manifest.MinWindowsBuild); err != nil {
		return err
	}
	l.updateProgress("wsl", "Checking Windows Subsystem for Linux...", 12, true, "", 0, 0)
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
		l.updateProgress("update", "Updating the installed runtime...", 20, true, "Applying the latest overlay inside WSL.", 0, 0)
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
	l.updateProgress("installed", "Runtime installed.", 90, false, "LoRA Pilot is ready to start.", 0, 0)
	return nil
}

func (l *Launcher) Setup(ctx context.Context, resume, launch bool) (err error) {
	if err := l.requireWindows(); err != nil {
		return err
	}
	if err := l.paths.Ensure(); err != nil {
		return fmt.Errorf("prepare local directories: %w", err)
	}
	l.updateProgress("preparing", "Preparing LoRA Pilot setup...", 2, true, "First install can take several minutes.", 0, 0)
	defer func() {
		if err != nil && !errors.Is(err, ErrSetupResumeScheduled) {
			l.failProgress(err)
		}
	}()

	state, err := LoadState(l.paths.StatePath)
	if err != nil {
		return err
	}

	manifestSource := strings.TrimSpace(l.manifestURL)
	if manifestSource == "" {
		manifestSource = strings.TrimSpace(state.ManifestURL)
	}
	if manifestSource == "" {
		return fmt.Errorf("setup requires an embedded or explicit manifest URL")
	}

	if state.DistroName == "" {
		state.DistroName = l.distroName
	}
	state.ManifestURL = manifestSource
	if err := SaveState(l.paths.StatePath, state); err != nil {
		return err
	}

	setupLauncher := *l
	setupLauncher.manifestURL = manifestSource
	if err := setupLauncher.Install(ctx, resume); err != nil {
		if errors.Is(err, ErrRebootRequired) {
			if scheduleErr := setupLauncher.scheduleResumeAfterReboot(ctx, manifestSource, launch); scheduleErr != nil {
				return scheduleErr
			}
			return ErrSetupResumeScheduled
		}
		return err
	}

	_ = setupLauncher.clearResumeAfterReboot(ctx)
	if !launch {
		setupLauncher.completeProgress("LoRA Pilot is installed and ready to launch.")
		return nil
	}
	setupLauncher.updateProgress("starting", "Starting ControlPilot...", 92, true, "Launching services inside WSL.", 0, 0)
	return setupLauncher.Start(ctx)
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

	l.updateProgress("starting", "Starting ControlPilot...", 95, true, "Booting the runtime services.", 0, 0)
	if _, err := l.exec.Run(ctx, BuildWSLExecCommand(state.DistroName, "root", "/opt/pilot/wsl-start.sh")); err != nil {
		return err
	}
	l.updateProgress("healthcheck", "Waiting for ControlPilot to respond...", 98, true, "Almost there.", 0, 0)
	if err := l.waitForHealth(ctx, healthURL, l.healthTimeout); err != nil {
		return err
	}

	state.LastStatus = "running"
	state.LastStartOKAt = l.now().UTC().Format(time.RFC3339)
	if err := SaveState(l.paths.StatePath, state); err != nil {
		return err
	}
	if err := l.openBrowser(ctx, controlPilotURL); err != nil {
		return err
	}
	l.completeProgress("LoRA Pilot is ready. ControlPilot is open.")
	return nil
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
		InstallPresent:        state.DistroName != "",
		DistroPresent:         state.DistroName != "",
		ControlPilotReachable: l.isHealthy(ctx, fmt.Sprintf("http://127.0.0.1:%d/healthz", manifest.Ports.ControlPilot)),
		AppVersion:            state.AppVersion,
		RuntimeVersion:        state.RuntimeVersion,
		InstallPath:           state.InstallPath,
		LastStatus:            state.LastStatus,
		PendingResumeStep:     state.PendingResumeStep,
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
	state.ManifestURL = ""
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
	_, err := l.ensureCachedArtifact(ctx, manifest.FreshInstall, artifactPath, "download_rootfs", "Downloading Linux runtime...", "Reusing downloaded Linux runtime bundle.", 12, 58)
	if err != nil {
		return err
	}
	l.updateProgress("verify_rootfs", "Verifying runtime bundle...", 60, true, formatTransferDetail(manifest.FreshInstall.SizeBytes, manifest.FreshInstall.SizeBytes), manifest.FreshInstall.SizeBytes, manifest.FreshInstall.SizeBytes)
	if err := VerifySHA256File(artifactPath, manifest.FreshInstall.SHA256); err != nil {
		return err
	}

	importPath := artifactPath
	if strings.HasSuffix(strings.ToLower(artifactPath), ".zst") {
		importPath = strings.TrimSuffix(artifactPath, ".zst")
		l.updateProgress("decompress_rootfs", "Preparing Linux runtime archive...", 64, false, "", 0, manifest.FreshInstall.SizeBytes)
		if err := DecompressZstdFileWithProgress(artifactPath, importPath, func(progress TransferProgress) {
			l.updateProgress("decompress_rootfs", "Preparing Linux runtime archive...", scaleProgressRange(64, 82, progress, manifest.FreshInstall.SizeBytes), false, formatTransferDetail(progress.BytesDone, progress.BytesTotal), progress.BytesDone, progress.BytesTotal)
		}); err != nil {
			return err
		}
	}
	if err := prepareFreshImportPath(installPath); err != nil {
		return err
	}
	l.updateProgress("import_wsl", "Importing LoRA Pilot into WSL...", 85, true, "Windows is unpacking the runtime.", 0, 0)
	_, err = l.exec.Run(ctx, BuildWSLImportCommand(distroName, installPath, importPath))
	if err != nil {
		_, _ = l.exec.Run(ctx, BuildWSLUnregisterCommand(distroName))
		_ = os.RemoveAll(installPath)
		return err
	}
	return nil
}

func prepareFreshImportPath(installPath string) error {
	parentDir := filepath.Dir(installPath)
	if err := os.MkdirAll(parentDir, 0o755); err != nil {
		return fmt.Errorf("create distro parent dir: %w", err)
	}
	if err := os.RemoveAll(installPath); err != nil {
		return fmt.Errorf("clear distro install dir: %w", err)
	}
	return nil
}

func (l *Launcher) applyOverlay(ctx context.Context, distroName string, manifest Manifest) error {
	artifactPath := filepath.Join(l.paths.DownloadsDir, filepath.Base(manifest.UpgradeOverlay.URL))
	_, err := l.ensureCachedArtifact(ctx, manifest.UpgradeOverlay, artifactPath, "download_overlay", "Downloading runtime update...", "Reusing downloaded runtime update.", 20, 58)
	if err != nil {
		return err
	}
	l.updateProgress("verify_overlay", "Verifying runtime update...", 62, true, formatTransferDetail(manifest.UpgradeOverlay.SizeBytes, manifest.UpgradeOverlay.SizeBytes), manifest.UpgradeOverlay.SizeBytes, manifest.UpgradeOverlay.SizeBytes)
	if err := VerifySHA256File(artifactPath, manifest.UpgradeOverlay.SHA256); err != nil {
		return err
	}
	wslPath, err := ToWSLPath(artifactPath)
	if err != nil {
		return err
	}
	_, _ = l.exec.Run(ctx, BuildWSLExecCommand(distroName, "root", "/opt/pilot/wsl-stop.sh || true"))
	l.updateProgress("apply_overlay", "Applying runtime update in WSL...", 72, true, "Updating immutable runtime files.", 0, 0)
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
	if localPath, ok := resolveLocalPath(source); ok {
		manifest, err := l.loadManifestFromFile(localPath)
		if err != nil {
			return Manifest{}, err
		}
		if err := WriteManifest(l.paths.CachedManifestPath, manifest); err != nil {
			return Manifest{}, err
		}
		return manifest, nil
	}
	if err := DownloadFile(ctx, l.httpClient, source, l.paths.CachedManifestPath); err != nil {
		return Manifest{}, err
	}
	return l.loadCachedManifest()
}

func (l *Launcher) loadCachedManifest() (Manifest, error) {
	return l.loadManifestFromFile(l.paths.CachedManifestPath)
}

func (l *Launcher) loadManifestFromFile(path string) (Manifest, error) {
	file, err := os.Open(path)
	if err != nil {
		return Manifest{}, fmt.Errorf("open manifest: %w", err)
	}
	defer file.Close()
	manifest, err := LoadManifest(file)
	if err != nil {
		return Manifest{}, err
	}
	manifest.ResolveRelativePaths(filepath.Dir(path))
	return manifest, nil
}

func (l *Launcher) ensureWSL(ctx context.Context, state *State) error {
	if _, err := l.exec.Run(ctx, BuildWSLStatusCommand()); err == nil {
		state.PendingResumeStep = ""
		l.updateProgress("wsl_ready", "WSL is ready.", 15, false, "", 0, 0)
		return nil
	}
	if _, err := l.exec.Run(ctx, BuildWSLInstallCommand()); err != nil {
		return fmt.Errorf("WSL is not available and automatic setup failed: %w", err)
	}
	l.updateProgress("reboot_required", "Windows restart required to finish WSL setup.", 20, false, "Setup will resume automatically after sign-in.", 0, 0)
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

func (l *Launcher) scheduleResumeAfterReboot(ctx context.Context, manifestSource string, launch bool) error {
	executablePath, err := os.Executable()
	if err != nil {
		return fmt.Errorf("resolve launcher path: %w", err)
	}
	commandLine := BuildLauncherSetupCommand(executablePath, manifestSource, true, launch)
	if _, err := l.exec.Run(ctx, BuildRunOnceAddCommand(resumeRunOnceValueName, commandLine)); err != nil {
		return fmt.Errorf("register setup resume after reboot: %w", err)
	}
	return nil
}

func (l *Launcher) clearResumeAfterReboot(ctx context.Context) error {
	_, err := l.exec.Run(ctx, BuildRunOnceDeleteCommand(resumeRunOnceValueName))
	if err != nil && !strings.Contains(strings.ToLower(err.Error()), "unable to find") {
		return err
	}
	return nil
}

func (l *Launcher) ensureCachedArtifact(ctx context.Context, ref ArtifactRef, destination, phase, downloadMessage, reuseMessage string, startPercent, endPercent int) (bool, error) {
	if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
		return false, fmt.Errorf("create downloads dir: %w", err)
	}

	if info, err := os.Stat(destination); err == nil {
		if ref.SizeBytes > 0 && info.Size() != ref.SizeBytes {
			_ = os.Remove(destination)
		} else {
			l.updateProgress(phase, "Verifying downloaded runtime bundle...", startPercent, true, formatTransferDetail(info.Size(), maxInt64(ref.SizeBytes, info.Size())), info.Size(), maxInt64(ref.SizeBytes, info.Size()))
			if err := VerifySHA256File(destination, ref.SHA256); err == nil {
				total := maxInt64(ref.SizeBytes, info.Size())
				l.updateProgress(phase, reuseMessage, endPercent, false, formatTransferDetail(total, total), total, total)
				return true, nil
			}
			_ = os.Remove(destination)
		}
	} else if !os.IsNotExist(err) {
		return false, fmt.Errorf("inspect cached artifact: %w", err)
	}

	l.updateProgress(phase, downloadMessage, startPercent, false, formatTransferDetail(0, ref.SizeBytes), 0, ref.SizeBytes)
	if err := DownloadFileWithOptions(ctx, l.httpClient, ref.URL, destination, DownloadOptions{
		ExpectedSize: ref.SizeBytes,
		OnProgress: func(progress TransferProgress) {
			total := progress.BytesTotal
			if total <= 0 {
				total = ref.SizeBytes
			}
			l.updateProgress(
				phase,
				downloadMessage,
				scaleProgressRange(startPercent, endPercent, progress, ref.SizeBytes),
				false,
				formatTransferDetail(progress.BytesDone, total),
				progress.BytesDone,
				total,
			)
		},
	}); err != nil {
		return false, err
	}
	return false, nil
}

func (l *Launcher) updateProgress(phase, message string, percent int, indeterminate bool, detail string, bytesDone, bytesTotal int64) {
	if l.progress == nil {
		return
	}
	_ = l.progress.Update(phase, message, percent, indeterminate, detail, bytesDone, bytesTotal)
}

func (l *Launcher) completeProgress(message string) {
	if l.progress == nil {
		return
	}
	_ = l.progress.Complete(message)
}

func (l *Launcher) failProgress(err error) {
	if l.progress == nil {
		return
	}
	_ = l.progress.Fail(err)
}

func scaleProgressRange(start, end int, progress TransferProgress, fallbackTotal int64) int {
	if end <= start {
		return clampProgressPercent(end)
	}
	if progress.Percent > 0 {
		return clampProgressPercent(start + int(float64(end-start)*(progress.Percent/100)))
	}
	total := progress.BytesTotal
	if total <= 0 {
		total = fallbackTotal
	}
	if total <= 0 {
		return clampProgressPercent(start)
	}
	ratio := float64(progress.BytesDone) / float64(total)
	if ratio < 0 {
		ratio = 0
	}
	if ratio > 1 {
		ratio = 1
	}
	return clampProgressPercent(start + int(float64(end-start)*ratio))
}

func formatTransferDetail(bytesDone, bytesTotal int64) string {
	switch {
	case bytesTotal > 0:
		return fmt.Sprintf("%s / %s", formatByteSize(bytesDone), formatByteSize(bytesTotal))
	case bytesDone > 0:
		return fmt.Sprintf("%s transferred", formatByteSize(bytesDone))
	default:
		return ""
	}
}

func formatByteSize(value int64) string {
	if value <= 0 {
		return "0 B"
	}
	const unit = 1024
	if value < unit {
		return fmt.Sprintf("%d B", value)
	}
	div, exp := int64(unit), 0
	for n := value / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %ciB", float64(value)/float64(div), "KMGTPE"[exp])
}

func maxInt64(left, right int64) int64 {
	if left > right {
		return left
	}
	return right
}
