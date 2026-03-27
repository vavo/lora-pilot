package launcher

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
)

type Executor interface {
	Run(context.Context, CommandSpec) (string, error)
}

type OSExecutor struct{}

func (OSExecutor) Run(ctx context.Context, spec CommandSpec) (string, error) {
	cmd := exec.CommandContext(ctx, spec.Name, spec.Args...)
	output, err := cmd.CombinedOutput()
	trimmed := strings.TrimSpace(string(output))
	if err != nil {
		if trimmed == "" {
			return "", fmt.Errorf("%s failed: %w", spec.Name, err)
		}
		return trimmed, fmt.Errorf("%s failed: %w", spec.Name, err)
	}
	return trimmed, nil
}
