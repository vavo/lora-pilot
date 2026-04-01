package launcher

import (
	"bytes"
	"context"
	"encoding/binary"
	"fmt"
	"os/exec"
	"strings"
	"unicode/utf16"
)

type Executor interface {
	Run(context.Context, CommandSpec) (string, error)
}

type OSExecutor struct{}

func (OSExecutor) Run(ctx context.Context, spec CommandSpec) (string, error) {
	cmd := exec.CommandContext(ctx, spec.Name, spec.Args...)
	output, err := cmd.CombinedOutput()
	trimmed := normalizeCommandOutput(output)
	if err != nil {
		if trimmed == "" {
			return "", fmt.Errorf("%s failed: %w", spec.Name, err)
		}
		return trimmed, fmt.Errorf("%s failed: %w", spec.Name, err)
	}
	return trimmed, nil
}

func normalizeCommandOutput(raw []byte) string {
	if len(raw) == 0 {
		return ""
	}
	if decoded, ok := decodeUTF16(raw); ok {
		return strings.TrimSpace(strings.TrimPrefix(decoded, "\ufeff"))
	}
	text := strings.ReplaceAll(string(raw), "\x00", "")
	text = strings.TrimPrefix(text, "\ufeff")
	return strings.TrimSpace(text)
}

func decodeUTF16(raw []byte) (string, bool) {
	if len(raw) < 2 || len(raw)%2 != 0 {
		return "", false
	}

	littleEndian := false
	switch {
	case bytes.HasPrefix(raw, []byte{0xff, 0xfe}):
		raw = raw[2:]
		littleEndian = true
	case bytes.HasPrefix(raw, []byte{0xfe, 0xff}):
		raw = raw[2:]
	default:
		zeroCount := 0
		for i := 1; i < len(raw); i += 2 {
			if raw[i] == 0 {
				zeroCount++
			}
		}
		if zeroCount < len(raw)/4 {
			return "", false
		}
		littleEndian = true
	}

	u16 := make([]uint16, 0, len(raw)/2)
	for i := 0; i+1 < len(raw); i += 2 {
		if littleEndian {
			u16 = append(u16, binary.LittleEndian.Uint16(raw[i:i+2]))
			continue
		}
		u16 = append(u16, binary.BigEndian.Uint16(raw[i:i+2]))
	}
	return string(utf16.Decode(u16)), true
}
