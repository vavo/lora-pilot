package launcher

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

type ArtifactRef struct {
	URL    string `json:"url"`
	SHA256 string `json:"sha256"`
}

type Ports struct {
	ControlPilot   int `json:"controlpilot"`
	Jupyter        int `json:"jupyter"`
	CodeServer     int `json:"code_server"`
	ComfyUI        int `json:"comfyui"`
	Kohya          int `json:"kohya"`
	TensorBoard    int `json:"tensorboard"`
	InvokeAI       int `json:"invokeai"`
	AIToolkit      int `json:"ai_toolkit"`
	CopilotSidecar int `json:"copilot_sidecar"`
}

type Manifest struct {
	AppVersion      string      `json:"app_version"`
	RuntimeVersion  string      `json:"runtime_version"`
	PublishedAt     string      `json:"published_at"`
	MinWindowsBuild int         `json:"min_windows_build"`
	FreshInstall    ArtifactRef `json:"fresh_install"`
	UpgradeOverlay  ArtifactRef `json:"upgrade_overlay"`
	Ports           Ports       `json:"ports"`
}

func DefaultManifest() Manifest {
	return Manifest{
		Ports: Ports{
			ControlPilot:   7878,
			Jupyter:        8888,
			CodeServer:     8443,
			ComfyUI:        5555,
			Kohya:          6666,
			TensorBoard:    4444,
			InvokeAI:       9090,
			AIToolkit:      8675,
			CopilotSidecar: 7879,
		},
	}
}

func LoadManifest(r io.Reader) (Manifest, error) {
	raw, err := io.ReadAll(r)
	if err != nil {
		return Manifest{}, fmt.Errorf("read manifest: %w", err)
	}
	raw = bytes.TrimPrefix(raw, []byte{0xef, 0xbb, 0xbf})

	var manifest Manifest
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&manifest); err != nil {
		return Manifest{}, fmt.Errorf("decode manifest: %w", err)
	}
	if err := manifest.Validate(); err != nil {
		return Manifest{}, err
	}
	return manifest, nil
}

func (m *Manifest) ResolveRelativePaths(baseDir string) {
	m.FreshInstall.URL = resolveManifestPath(baseDir, m.FreshInstall.URL)
	m.UpgradeOverlay.URL = resolveManifestPath(baseDir, m.UpgradeOverlay.URL)
}

func WriteManifest(path string, manifest Manifest) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return fmt.Errorf("create manifest dir: %w", err)
	}
	raw, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		return fmt.Errorf("encode manifest: %w", err)
	}
	raw = append(raw, '\n')
	if err := os.WriteFile(path, raw, 0o644); err != nil {
		return fmt.Errorf("write manifest: %w", err)
	}
	return nil
}

func resolveManifestPath(baseDir, value string) string {
	if value == "" {
		return ""
	}
	if _, ok := resolveLocalPath(value); ok {
		return value
	}
	if strings.Contains(value, "://") {
		return value
	}
	return filepath.Join(baseDir, filepath.FromSlash(value))
}

func (m Manifest) Validate() error {
	if m.AppVersion == "" {
		return fmt.Errorf("manifest missing app_version")
	}
	if m.RuntimeVersion == "" {
		return fmt.Errorf("manifest missing runtime_version")
	}
	if m.FreshInstall.URL == "" || m.FreshInstall.SHA256 == "" {
		return fmt.Errorf("manifest missing fresh_install url or sha256")
	}
	if m.UpgradeOverlay.URL == "" || m.UpgradeOverlay.SHA256 == "" {
		return fmt.Errorf("manifest missing upgrade_overlay url or sha256")
	}
	if m.MinWindowsBuild <= 0 {
		return fmt.Errorf("manifest missing min_windows_build")
	}
	if m.Ports.ControlPilot == 0 {
		return fmt.Errorf("manifest missing controlpilot port")
	}
	return nil
}
