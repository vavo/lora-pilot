package launcher

import (
	"net"
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

func TestStateRoundTrip(t *testing.T) {
	t.Parallel()

	dir := t.TempDir()
	path := filepath.Join(dir, "state.json")
	in := State{
		AppVersion:        "2.0.0",
		RuntimeVersion:    "2.0.0",
		DistroName:        "LoRAPilot",
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

var netListen = func(network, address string) (net.Listener, error) {
	return net.Listen(network, address)
}
