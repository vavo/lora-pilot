package launcher

import (
	"bytes"
	"context"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestLoadManifest(t *testing.T) {
	t.Parallel()

	manifest, err := LoadManifest(strings.NewReader(`{
	  "app_version": "1.2.3",
	  "runtime_version": "1.2.3",
	  "published_at": "2026-03-27T00:00:00Z",
	  "min_windows_build": 19045,
	  "fresh_install": {"url": "https://example.invalid/rootfs.tar.zst", "sha256": "abc"},
	  "upgrade_overlay": {"url": "https://example.invalid/overlay.tar.zst", "sha256": "def"},
	  "ports": {"controlpilot": 7878}
	}`))
	if err != nil {
		t.Fatalf("LoadManifest returned error: %v", err)
	}
	if manifest.RuntimeVersion != "1.2.3" {
		t.Fatalf("unexpected runtime version: %s", manifest.RuntimeVersion)
	}
}

func TestLoadManifestStripsUTF8BOM(t *testing.T) {
	t.Parallel()

	input := append([]byte{0xef, 0xbb, 0xbf}, []byte(`{
	  "app_version": "1.2.3",
	  "runtime_version": "1.2.3",
	  "published_at": "2026-03-27T00:00:00Z",
	  "min_windows_build": 19045,
	  "fresh_install": {"url": "rootfs.tar.zst", "sha256": "abc"},
	  "upgrade_overlay": {"url": "overlay.tar.zst", "sha256": "def"},
	  "ports": {"controlpilot": 7878}
	}`)...)

	manifest, err := LoadManifest(bytes.NewReader(input))
	if err != nil {
		t.Fatalf("LoadManifest returned error: %v", err)
	}
	if manifest.AppVersion != "1.2.3" {
		t.Fatalf("unexpected app version: %s", manifest.AppVersion)
	}
}

func TestResolveRelativePaths(t *testing.T) {
	t.Parallel()

	baseDir := filepath.Join("C:", "Temp", "lora-pilot-runtime")
	manifest := Manifest{
		FreshInstall:   ArtifactRef{URL: "rootfs.tar.zst"},
		UpgradeOverlay: ArtifactRef{URL: "overlay.tar.zst"},
	}
	manifest.ResolveRelativePaths(baseDir)
	if manifest.FreshInstall.URL != filepath.Join(baseDir, "rootfs.tar.zst") {
		t.Fatalf("unexpected fresh install path: %s", manifest.FreshInstall.URL)
	}
	if manifest.UpgradeOverlay.URL != filepath.Join(baseDir, "overlay.tar.zst") {
		t.Fatalf("unexpected overlay path: %s", manifest.UpgradeOverlay.URL)
	}
}

func TestStateRoundTrip(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	path := filepath.Join(dir, "state.json")
	in := State{
		AppVersion:        "2.0.0",
		RuntimeVersion:    "2.0.0",
		DistroName:        "LoRAPilot",
		ManifestURL:       "https://downloads.example.com/windows-runtime-manifest.json",
		InstallPath:       `C:\Users\me\AppData\Local\LoRAPilot\wsl\LoRAPilot`,
		PendingResumeStep: "resume-install",
	}
	if err := SaveState(path, in); err != nil {
		t.Fatalf("SaveState returned error: %v", err)
	}
	out, err := LoadState(path)
	if err != nil {
		t.Fatalf("LoadState returned error: %v", err)
	}
	if out.PendingResumeStep != in.PendingResumeStep {
		t.Fatalf("unexpected pending step: %s", out.PendingResumeStep)
	}
	if out.ManifestURL != in.ManifestURL {
		t.Fatalf("unexpected manifest url: %s", out.ManifestURL)
	}
}

func TestVerifySHA256File(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	path := filepath.Join(dir, "artifact.txt")
	if err := os.WriteFile(path, []byte("lora-pilot"), 0o644); err != nil {
		t.Fatalf("WriteFile returned error: %v", err)
	}

	hash, err := SHA256File(path)
	if err != nil {
		t.Fatalf("SHA256File returned error: %v", err)
	}
	if err := VerifySHA256File(path, hash); err != nil {
		t.Fatalf("VerifySHA256File returned error: %v", err)
	}
}

func TestDownloadFileSetsBrowserLikeHeaders(t *testing.T) {
	t.Parallel()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if got := r.Header.Get("User-Agent"); !strings.Contains(got, "Mozilla/5.0") || !strings.Contains(got, "LoRAPilotInstaller/1.0") {
			t.Fatalf("unexpected user agent: %q", got)
		}
		if got := r.Header.Get("Accept"); got != "*/*" {
			t.Fatalf("unexpected accept header: %q", got)
		}
		_, _ = w.Write([]byte("runtime-bundle"))
	}))
	defer server.Close()

	path := filepath.Join(t.TempDir(), "artifact.bin")
	if err := DownloadFile(context.Background(), server.Client(), server.URL+"/artifact.bin", path); err != nil {
		t.Fatalf("DownloadFile returned error: %v", err)
	}

	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("ReadFile returned error: %v", err)
	}
	if string(raw) != "runtime-bundle" {
		t.Fatalf("unexpected downloaded content: %q", string(raw))
	}
}

func TestBuildCurlDownloadArgs(t *testing.T) {
	t.Parallel()

	args := buildCurlDownloadArgs("https://cdn.example.com/rootfs.tar.zst", `C:\Temp\rootfs.tar.zst`)
	joined := strings.Join(args, "\n")
	for _, needle := range []string{
		"--fail",
		"--location",
		"--retry",
		"--retry-all-errors",
		"--user-agent",
		defaultDownloadUserAgent,
		"--header",
		"Accept: */*",
		`C:\Temp\rootfs.tar.zst`,
		"https://cdn.example.com/rootfs.tar.zst",
	} {
		if !strings.Contains(joined, needle) {
			t.Fatalf("missing curl argument %q in %q", needle, joined)
		}
	}
}

func TestPrepareFreshImportPathRemovesStaleContents(t *testing.T) {
	t.Parallel()

	root := t.TempDir()
	installPath := filepath.Join(root, "wsl", "LoRAPilot")
	if err := os.MkdirAll(installPath, 0o755); err != nil {
		t.Fatalf("MkdirAll returned error: %v", err)
	}
	staleFile := filepath.Join(installPath, "ext4.vhdx")
	if err := os.WriteFile(staleFile, []byte("stale"), 0o644); err != nil {
		t.Fatalf("WriteFile returned error: %v", err)
	}

	if err := prepareFreshImportPath(installPath); err != nil {
		t.Fatalf("prepareFreshImportPath returned error: %v", err)
	}

	if _, err := os.Stat(staleFile); !os.IsNotExist(err) {
		t.Fatalf("stale file still exists, err=%v", err)
	}
	if _, err := os.Stat(filepath.Dir(installPath)); err != nil {
		t.Fatalf("parent dir missing after cleanup: %v", err)
	}
}

func TestToWSLPath(t *testing.T) {
	t.Parallel()

	got, err := ToWSLPath(`C:\Users\vavo\AppData\Local\LoRAPilot\downloads\rootfs.tar.zst`)
	if err != nil {
		t.Fatalf("ToWSLPath returned error: %v", err)
	}
	want := "/mnt/c/Users/vavo/AppData/Local/LoRAPilot/downloads/rootfs.tar.zst"
	if got != want {
		t.Fatalf("unexpected WSL path: got %q want %q", got, want)
	}
}

func TestFindConflictingPorts(t *testing.T) {
	t.Parallel()

	listener, err := netListen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("netListen returned error: %v", err)
	}
	defer listener.Close()

	port := listener.Addr().(*net.TCPAddr).Port
	conflicts, err := FindConflictingPorts([]int{port})
	if err != nil {
		t.Fatalf("FindConflictingPorts returned error: %v", err)
	}
	if len(conflicts) != 1 || conflicts[0] != port {
		t.Fatalf("unexpected conflicts: %#v", conflicts)
	}
}

func TestBuildWSLImportCommand(t *testing.T) {
	t.Parallel()

	cmd := BuildWSLImportCommand("LoRAPilot", `C:\Users\vavo\AppData\Local\LoRAPilot\wsl\LoRAPilot`, `C:\tmp\rootfs.tar`)
	if cmd.Name != "wsl.exe" {
		t.Fatalf("unexpected command name: %s", cmd.Name)
	}
	if len(cmd.Args) < 6 || cmd.Args[0] != "--import" {
		t.Fatalf("unexpected import args: %#v", cmd.Args)
	}
}

func TestBuildRunOnceAddCommand(t *testing.T) {
	t.Parallel()

	cmd := BuildRunOnceAddCommand("LoRAPilotSetupResume", `"C:\Tools\LoRAPilotLauncher.exe" setup --resume --launch`)
	if cmd.Name != "reg.exe" {
		t.Fatalf("unexpected command name: %s", cmd.Name)
	}
	if len(cmd.Args) < 9 || cmd.Args[0] != "ADD" {
		t.Fatalf("unexpected runonce args: %#v", cmd.Args)
	}
}

func TestBuildLauncherSetupCommand(t *testing.T) {
	t.Parallel()

	commandLine := BuildLauncherSetupCommand(`C:\Program Files\LoRAPilot\LoRAPilotLauncher.exe`, `https://downloads.example.com/windows-runtime-manifest.json`, true, true)
	if !strings.Contains(commandLine, `setup --resume --launch`) {
		t.Fatalf("unexpected setup command line: %s", commandLine)
	}
	if !strings.Contains(commandLine, `"https://downloads.example.com/windows-runtime-manifest.json"`) {
		t.Fatalf("manifest URL was not quoted: %s", commandLine)
	}
}

func TestNormalizeCommandOutputStripsUTF16Nulls(t *testing.T) {
	t.Parallel()

	raw := []byte{'L', 0, 'o', 0, 'R', 0, 'A', 0, 'P', 0, 'i', 0, 'l', 0, 'o', 0, 't', 0, '\r', 0, '\n', 0}
	if got := normalizeCommandOutput(raw); got != "LoRAPilot" {
		t.Fatalf("unexpected normalized output: %q", got)
	}
}

var netListen = func(network, address string) (net.Listener, error) {
	return net.Listen(network, address)
}
