package launcher

import (
	"os"
	"path/filepath"
)

type Paths struct {
	BaseDir            string
	LogsDir            string
	DownloadsDir       string
	WSLDir             string
	StatePath          string
	CachedManifestPath string
}

func DefaultPaths() Paths {
	baseRoot := os.Getenv("LOCALAPPDATA")
	if baseRoot == "" {
		baseRoot = os.TempDir()
	}
	baseDir := filepath.Join(baseRoot, "LoRAPilot")
	return Paths{
		BaseDir:            baseDir,
		LogsDir:            filepath.Join(baseDir, "logs"),
		DownloadsDir:       filepath.Join(baseDir, "downloads"),
		WSLDir:             filepath.Join(baseDir, "wsl"),
		StatePath:          filepath.Join(baseDir, "state.json"),
		CachedManifestPath: filepath.Join(baseDir, "downloads", "windows-runtime-manifest.json"),
	}
}

func (p Paths) Ensure() error {
	for _, dir := range []string{p.BaseDir, p.LogsDir, p.DownloadsDir, p.WSLDir} {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return err
		}
	}
	return nil
}

func (p Paths) DistroPath(distroName string) string {
	return filepath.Join(p.WSLDir, distroName)
}
