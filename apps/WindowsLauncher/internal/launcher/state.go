package launcher

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
)

type State struct {
	AppVersion        string `json:"app_version"`
	RuntimeVersion    string `json:"runtime_version"`
	DistroName        string `json:"distro_name"`
	ManifestURL       string `json:"manifest_url"`
	InstallPath       string `json:"install_path"`
	InstalledAt       string `json:"installed_at"`
	LastStartOKAt     string `json:"last_start_ok_at"`
	LastStatus        string `json:"last_status"`
	PendingResumeStep string `json:"pending_resume_step"`
}

func LoadState(path string) (State, error) {
	raw, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		return State{}, nil
	}
	if err != nil {
		return State{}, fmt.Errorf("read state: %w", err)
	}

	var state State
	if err := json.Unmarshal(raw, &state); err != nil {
		return State{}, fmt.Errorf("decode state: %w", err)
	}
	return state, nil
}

func SaveState(path string, state State) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return fmt.Errorf("create state dir: %w", err)
	}

	raw, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return fmt.Errorf("encode state: %w", err)
	}
	raw = append(raw, '\n')

	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, raw, 0o644); err != nil {
		return fmt.Errorf("write state temp: %w", err)
	}
	if err := os.Rename(tmp, path); err != nil {
		return fmt.Errorf("rename state temp: %w", err)
	}
	return nil
}
