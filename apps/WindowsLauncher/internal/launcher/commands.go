package launcher

import (
	"fmt"
	"net"
	"path/filepath"
	"strings"
	"unicode"
)

type CommandSpec struct {
	Name string
	Args []string
}

func BuildWSLStatusCommand() CommandSpec {
	return CommandSpec{Name: "wsl.exe", Args: []string{"--status"}}
}

func BuildWSLInstallCommand() CommandSpec {
	return CommandSpec{Name: "wsl.exe", Args: []string{"--install", "--no-distribution"}}
}

func BuildWSLListCommand() CommandSpec {
	return CommandSpec{Name: "wsl.exe", Args: []string{"--list", "--quiet"}}
}

func BuildWSLImportCommand(distroName, installPath, archivePath string) CommandSpec {
	return CommandSpec{
		Name: "wsl.exe",
		Args: []string{"--import", distroName, installPath, archivePath, "--version", "2"},
	}
}

func BuildWSLUnregisterCommand(distroName string) CommandSpec {
	return CommandSpec{Name: "wsl.exe", Args: []string{"--unregister", distroName}}
}

func BuildWSLExecCommand(distroName, user, command string) CommandSpec {
	args := []string{"-d", distroName}
	if user != "" {
		args = append(args, "--user", user)
	}
	args = append(args, "--", "bash", "-lc", command)
	return CommandSpec{Name: "wsl.exe", Args: args}
}

func BuildOpenBrowserCommand(targetURL string) CommandSpec {
	return CommandSpec{Name: "rundll32.exe", Args: []string{"url.dll,FileProtocolHandler", targetURL}}
}

func BuildWindowsBuildCommand() CommandSpec {
	return CommandSpec{
		Name: "powershell.exe",
		Args: []string{"-NoProfile", "-Command", "[System.Environment]::OSVersion.Version.Build"},
	}
}

func ToWSLPath(windowsPath string) (string, error) {
	cleaned := filepath.Clean(windowsPath)
	if len(cleaned) < 2 || cleaned[1] != ':' {
		return "", fmt.Errorf("path %q is not an absolute Windows path", windowsPath)
	}

	drive := unicode.ToLower(rune(cleaned[0]))
	rest := strings.ReplaceAll(cleaned[2:], `\`, "/")
	return fmt.Sprintf("/mnt/%c%s", drive, rest), nil
}

func FindConflictingPorts(ports []int) ([]int, error) {
	var conflicts []int
	for _, port := range ports {
		ln, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", port))
		if err != nil {
			conflicts = append(conflicts, port)
			continue
		}
		if closeErr := ln.Close(); closeErr != nil {
			return nil, fmt.Errorf("close listener for port %d: %w", port, closeErr)
		}
	}
	return conflicts, nil
}
