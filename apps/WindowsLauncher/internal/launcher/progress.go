package launcher

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type InstallProgress struct {
	Phase         string `json:"phase"`
	Message       string `json:"message"`
	Detail        string `json:"detail,omitempty"`
	Percent       int    `json:"percent"`
	BytesDone     int64  `json:"bytes_done,omitempty"`
	BytesTotal    int64  `json:"bytes_total,omitempty"`
	Indeterminate bool   `json:"indeterminate"`
	Complete      bool   `json:"complete"`
	Error         string `json:"error,omitempty"`
	UpdatedAt     string `json:"updated_at"`
}

type ProgressWriter struct {
	path string
	now  func() time.Time

	mu          sync.Mutex
	lastWritten InstallProgress
}

func NewProgressWriter(path string, now func() time.Time) *ProgressWriter {
	if now == nil {
		now = time.Now
	}
	return &ProgressWriter{path: path, now: now}
}

func (p *ProgressWriter) Update(phase, message string, percent int, indeterminate bool, detail string, bytesDone, bytesTotal int64) error {
	return p.write(InstallProgress{
		Phase:         phase,
		Message:       message,
		Detail:        detail,
		Percent:       clampProgressPercent(percent),
		BytesDone:     bytesDone,
		BytesTotal:    bytesTotal,
		Indeterminate: indeterminate,
		UpdatedAt:     p.now().UTC().Format(time.RFC3339),
	})
}

func (p *ProgressWriter) Complete(message string) error {
	return p.write(InstallProgress{
		Phase:     "complete",
		Message:   message,
		Percent:   100,
		Complete:  true,
		UpdatedAt: p.now().UTC().Format(time.RFC3339),
	})
}

func (p *ProgressWriter) Fail(err error) error {
	if err == nil {
		return nil
	}
	return p.write(InstallProgress{
		Phase:     "error",
		Message:   "LoRA Pilot setup failed.",
		Percent:   clampProgressPercent(p.lastWritten.Percent),
		Complete:  true,
		Error:     err.Error(),
		UpdatedAt: p.now().UTC().Format(time.RFC3339),
	})
}

func (p *ProgressWriter) write(progress InstallProgress) error {
	if p == nil || p.path == "" {
		return nil
	}

	p.mu.Lock()
	defer p.mu.Unlock()

	if progress.Percent == 0 && p.lastWritten.Percent > 0 && progress.Phase == p.lastWritten.Phase {
		progress.Percent = p.lastWritten.Percent
	}
	if progress.Message == "" {
		progress.Message = p.lastWritten.Message
	}
	if progress.Detail == "" && progress.Phase == p.lastWritten.Phase {
		progress.Detail = p.lastWritten.Detail
	}

	compare := progress
	compare.UpdatedAt = ""
	lastCompare := p.lastWritten
	lastCompare.UpdatedAt = ""
	if compare == lastCompare {
		return nil
	}
	p.lastWritten = progress

	if err := os.MkdirAll(filepath.Dir(p.path), 0o755); err != nil {
		return fmt.Errorf("create progress dir: %w", err)
	}
	raw, err := json.MarshalIndent(progress, "", "  ")
	if err != nil {
		return fmt.Errorf("encode progress: %w", err)
	}
	raw = append(raw, '\n')

	tmp := p.path + ".tmp"
	if err := os.WriteFile(tmp, raw, 0o644); err != nil {
		return fmt.Errorf("write progress temp: %w", err)
	}
	if err := os.Rename(tmp, p.path); err != nil {
		return fmt.Errorf("rename progress temp: %w", err)
	}
	return nil
}

func clampProgressPercent(percent int) int {
	if percent < 0 {
		return 0
	}
	if percent > 100 {
		return 100
	}
	return percent
}
