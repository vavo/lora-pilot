package launcher

import (
	"bufio"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"

	"github.com/klauspost/compress/zstd"
)

const defaultDownloadUserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 LoRAPilotInstaller/1.0"

var currentGOOS = runtime.GOOS
var execLookPath = exec.LookPath
var execCommandContext = exec.CommandContext

type TransferProgress struct {
	BytesDone  int64
	BytesTotal int64
	Percent    float64
}

type DownloadOptions struct {
	ExpectedSize int64
	OnProgress   func(TransferProgress)
}

func DownloadFile(ctx context.Context, client *http.Client, sourceURL, destination string) error {
	return DownloadFileWithOptions(ctx, client, sourceURL, destination, DownloadOptions{})
}

func DownloadFileWithOptions(ctx context.Context, client *http.Client, sourceURL, destination string, opts DownloadOptions) error {
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
		return copyFile(localPath, destination, opts)
	}

	if shouldUseCurlDownloader(sourceURL) {
		if err := downloadWithCurl(ctx, sourceURL, destination, opts); err == nil {
			return nil
		}
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, sourceURL, nil)
	if err != nil {
		return fmt.Errorf("build download request: %w", err)
	}
	req.Header.Set("User-Agent", defaultDownloadUserAgent)
	req.Header.Set("Accept", "*/*")

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

	total := resp.ContentLength
	if total <= 0 {
		total = opts.ExpectedSize
	}
	progress := newProgressWriter(total, opts.OnProgress)
	if _, err := io.Copy(out, io.TeeReader(resp.Body, progress)); err != nil {
		return fmt.Errorf("write destination: %w", err)
	}
	progress.complete()
	return nil
}

func shouldUseCurlDownloader(sourceURL string) bool {
	if currentGOOS != "windows" {
		return false
	}
	parsed, err := url.Parse(sourceURL)
	if err != nil {
		return false
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		return false
	}
	_, err = execLookPath("curl.exe")
	return err == nil
}

func buildCurlDownloadArgs(sourceURL, destination string) []string {
	return []string{
		"--progress-bar",
		"--show-error",
		"--fail",
		"--location",
		"--retry",
		"5",
		"--retry-delay",
		"2",
		"--retry-all-errors",
		"--user-agent",
		defaultDownloadUserAgent,
		"--header",
		"Accept: */*",
		"--output",
		destination,
		sourceURL,
	}
}

func downloadWithCurl(ctx context.Context, sourceURL, destination string, opts DownloadOptions) error {
	cmd := execCommandContext(ctx, "curl.exe", buildCurlDownloadArgs(sourceURL, destination)...)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return fmt.Errorf("curl stdout pipe %s: %w", sourceURL, err)
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return fmt.Errorf("curl stderr pipe %s: %w", sourceURL, err)
	}
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("start curl download %s: %w", sourceURL, err)
	}

	go func() {
		_, _ = io.Copy(io.Discard, stdout)
	}()

	var stderrBuffer strings.Builder
	progressDone := make(chan struct{})
	go func() {
		defer close(progressDone)
		parseCurlProgress(stderr, opts, &stderrBuffer)
	}()

	err = cmd.Wait()
	<-progressDone
	if err != nil {
		message := strings.TrimSpace(stderrBuffer.String())
		if message == "" {
			message = err.Error()
		}
		return fmt.Errorf("curl download %s: %s", sourceURL, message)
	}
	reportProgress(opts.OnProgress, TransferProgress{
		BytesDone:  opts.ExpectedSize,
		BytesTotal: opts.ExpectedSize,
		Percent:    100,
	})
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
	return DecompressZstdFileWithProgress(sourcePath, destinationPath, nil)
}

func DecompressZstdFileWithProgress(sourcePath, destinationPath string, onProgress func(TransferProgress)) error {
	source, err := os.Open(sourcePath)
	if err != nil {
		return fmt.Errorf("open zstd source: %w", err)
	}
	defer source.Close()

	info, err := source.Stat()
	if err != nil {
		return fmt.Errorf("stat zstd source: %w", err)
	}

	progressSource := &countingReader{
		reader:     source,
		total:      info.Size(),
		onProgress: onProgress,
	}

	reader, err := zstd.NewReader(progressSource)
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
	progressSource.complete()
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

func copyFile(sourcePath, destinationPath string, opts DownloadOptions) error {
	source, err := os.Open(sourcePath)
	if err != nil {
		return fmt.Errorf("open source file: %w", err)
	}
	defer source.Close()

	info, err := source.Stat()
	if err != nil {
		return fmt.Errorf("stat source file: %w", err)
	}

	destination, err := os.Create(destinationPath)
	if err != nil {
		return fmt.Errorf("create destination file: %w", err)
	}
	defer destination.Close()

	total := info.Size()
	if total <= 0 {
		total = opts.ExpectedSize
	}
	progress := newProgressWriter(total, opts.OnProgress)
	if _, err := io.Copy(destination, io.TeeReader(source, progress)); err != nil {
		return fmt.Errorf("copy local file: %w", err)
	}
	progress.complete()
	return nil
}

type progressWriter struct {
	total       int64
	written     int64
	lastPercent int
	onProgress  func(TransferProgress)
}

func newProgressWriter(total int64, onProgress func(TransferProgress)) *progressWriter {
	return &progressWriter{total: total, lastPercent: -1, onProgress: onProgress}
}

func (w *progressWriter) Write(p []byte) (int, error) {
	n := len(p)
	w.written += int64(n)
	reportTransferProgress(w.onProgress, w.written, w.total, &w.lastPercent)
	return n, nil
}

func (w *progressWriter) complete() {
	reportProgress(w.onProgress, TransferProgress{
		BytesDone:  w.total,
		BytesTotal: w.total,
		Percent:    100,
	})
}

type countingReader struct {
	reader      io.Reader
	total       int64
	read        int64
	lastPercent int
	onProgress  func(TransferProgress)
}

func (r *countingReader) Read(p []byte) (int, error) {
	n, err := r.reader.Read(p)
	if n > 0 {
		r.read += int64(n)
		reportTransferProgress(r.onProgress, r.read, r.total, &r.lastPercent)
	}
	return n, err
}

func (r *countingReader) complete() {
	reportProgress(r.onProgress, TransferProgress{
		BytesDone:  r.total,
		BytesTotal: r.total,
		Percent:    100,
	})
}

func reportTransferProgress(onProgress func(TransferProgress), bytesDone, bytesTotal int64, lastPercent *int) {
	if onProgress == nil || bytesTotal <= 0 {
		return
	}
	percent := int(float64(bytesDone) * 100 / float64(bytesTotal))
	if percent == *lastPercent {
		return
	}
	*lastPercent = percent
	reportProgress(onProgress, TransferProgress{
		BytesDone:  bytesDone,
		BytesTotal: bytesTotal,
		Percent:    float64(percent),
	})
}

func reportProgress(onProgress func(TransferProgress), progress TransferProgress) {
	if onProgress == nil {
		return
	}
	onProgress(progress)
}

func parseCurlProgress(stderr io.Reader, opts DownloadOptions, sink *strings.Builder) {
	scanner := bufio.NewScanner(stderr)
	scanner.Buffer(make([]byte, 0, 1024), 128*1024)
	scanner.Split(splitOnCRLF)
	lastPercent := -1.0
	for scanner.Scan() {
		line := scanner.Text()
		if sink != nil {
			if sink.Len() > 0 {
				sink.WriteByte('\n')
			}
			sink.WriteString(line)
		}
		percent, ok := extractCurlPercent(line)
		if !ok || percent == lastPercent {
			continue
		}
		lastPercent = percent
		bytesTotal := opts.ExpectedSize
		bytesDone := int64(0)
		if bytesTotal > 0 {
			bytesDone = int64(float64(bytesTotal) * (float64(percent) / 100))
		}
		reportProgress(opts.OnProgress, TransferProgress{
			BytesDone:  bytesDone,
			BytesTotal: bytesTotal,
			Percent:    percent,
		})
	}
}

func splitOnCRLF(data []byte, atEOF bool) (advance int, token []byte, err error) {
	for i, b := range data {
		if b == '\n' || b == '\r' {
			if i == 0 {
				return 1, nil, nil
			}
			return i + 1, data[:i], nil
		}
	}
	if atEOF && len(data) > 0 {
		return len(data), data, nil
	}
	return 0, nil, nil
}

func extractCurlPercent(line string) (float64, bool) {
	line = strings.TrimSpace(line)
	parts := strings.Fields(line)
	for i := len(parts) - 1; i >= 0; i-- {
		token := strings.TrimSuffix(parts[i], "%")
		if token == parts[i] {
			continue
		}
		value, err := strconv.ParseFloat(token, 64)
		if err != nil {
			continue
		}
		return value, true
	}
	return 0, false
}
