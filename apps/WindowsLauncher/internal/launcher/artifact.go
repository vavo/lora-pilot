package launcher

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strings"

	"github.com/klauspost/compress/zstd"
)

func DownloadFile(ctx context.Context, client *http.Client, sourceURL, destination string) error {
	if sourceURL == "" {
		return fmt.Errorf("download url is empty")
	}
	if client == nil {
		client = http.DefaultClient
	}
	if err := os.MkdirAll(filepath.Dir(destination), 0o755); err != nil {
		return fmt.Errorf("create download dir: %w", err)
	}

	if localPath, ok := resolveLocalPath(sourceURL); ok {
		return copyFile(localPath, destination)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, sourceURL, nil)
	if err != nil {
		return fmt.Errorf("build download request: %w", err)
	}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("download %s: %w", sourceURL, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("download %s: unexpected status %s", sourceURL, resp.Status)
	}

	out, err := os.Create(destination)
	if err != nil {
		return fmt.Errorf("create destination: %w", err)
	}
	defer out.Close()

	if _, err := io.Copy(out, resp.Body); err != nil {
		return fmt.Errorf("write destination: %w", err)
	}
	return nil
}

func VerifySHA256File(path, want string) error {
	hashValue, err := SHA256File(path)
	if err != nil {
		return err
	}
	if !strings.EqualFold(hashValue, want) {
		return fmt.Errorf("checksum mismatch for %s: expected %s, got %s", path, want, hashValue)
	}
	return nil
}

func SHA256File(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", fmt.Errorf("open %s: %w", path, err)
	}
	defer file.Close()

	hasher := sha256.New()
	if _, err := io.Copy(hasher, file); err != nil {
		return "", fmt.Errorf("hash %s: %w", path, err)
	}
	return hex.EncodeToString(hasher.Sum(nil)), nil
}

func DecompressZstdFile(sourcePath, destinationPath string) error {
	source, err := os.Open(sourcePath)
	if err != nil {
		return fmt.Errorf("open zstd source: %w", err)
	}
	defer source.Close()

	reader, err := zstd.NewReader(source)
	if err != nil {
		return fmt.Errorf("create zstd reader: %w", err)
	}
	defer reader.Close()

	if err := os.MkdirAll(filepath.Dir(destinationPath), 0o755); err != nil {
		return fmt.Errorf("create zstd destination dir: %w", err)
	}
	destination, err := os.Create(destinationPath)
	if err != nil {
		return fmt.Errorf("create zstd destination: %w", err)
	}
	defer destination.Close()

	if _, err := io.Copy(destination, reader); err != nil {
		return fmt.Errorf("decompress zstd: %w", err)
	}
	return nil
}

func resolveLocalPath(raw string) (string, bool) {
	if raw == "" {
		return "", false
	}
	if len(raw) > 1 && raw[1] == ':' {
		return raw, true
	}
	parsed, err := url.Parse(raw)
	if err == nil && parsed.Scheme == "file" {
		return parsed.Path, true
	}
	if err == nil && parsed.Scheme != "" {
		return "", false
	}
	if _, err := os.Stat(raw); err == nil {
		return raw, true
	}
	return "", false
}

func copyFile(sourcePath, destinationPath string) error {
	source, err := os.Open(sourcePath)
	if err != nil {
		return fmt.Errorf("open source file: %w", err)
	}
	defer source.Close()

	destination, err := os.Create(destinationPath)
	if err != nil {
		return fmt.Errorf("create destination file: %w", err)
	}
	defer destination.Close()

	if _, err := io.Copy(destination, source); err != nil {
		return fmt.Errorf("copy local file: %w", err)
	}
	return nil
}
