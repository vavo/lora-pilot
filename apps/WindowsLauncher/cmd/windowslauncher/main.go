package main

import (
	"context"
	"flag"
	"fmt"
	"os"

	"github.com/vavo/lora-pilot/apps/windowslauncher/internal/launcher"
)

func main() {
	if err := run(context.Background(), os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run(ctx context.Context, args []string) error {
	if len(args) == 0 {
		return usage()
	}

	switch args[0] {
	case "install":
		fs := flag.NewFlagSet("install", flag.ContinueOnError)
		resume := fs.Bool("resume", false, "resume an installation that previously required reboot")
		manifestURL := fs.String("manifest-url", "", "manifest URL or file path")
		distroName := fs.String("distro-name", "LoRAPilot", "managed WSL distro name")
		if err := fs.Parse(args[1:]); err != nil {
			return err
		}
		return launcher.New(launcher.Options{
			DistroName:  *distroName,
			ManifestURL: *manifestURL,
		}).Install(ctx, *resume)
	case "start":
		fs := flag.NewFlagSet("start", flag.ContinueOnError)
		distroName := fs.String("distro-name", "LoRAPilot", "managed WSL distro name")
		if err := fs.Parse(args[1:]); err != nil {
			return err
		}
		return launcher.New(launcher.Options{DistroName: *distroName}).Start(ctx)
	case "stop":
		fs := flag.NewFlagSet("stop", flag.ContinueOnError)
		distroName := fs.String("distro-name", "LoRAPilot", "managed WSL distro name")
		if err := fs.Parse(args[1:]); err != nil {
			return err
		}
		return launcher.New(launcher.Options{DistroName: *distroName}).Stop(ctx)
	case "status":
		fs := flag.NewFlagSet("status", flag.ContinueOnError)
		asJSON := fs.Bool("json", false, "emit JSON")
		distroName := fs.String("distro-name", "LoRAPilot", "managed WSL distro name")
		if err := fs.Parse(args[1:]); err != nil {
			return err
		}
		l := launcher.New(launcher.Options{DistroName: *distroName})
		status, err := l.Status(ctx)
		if err != nil {
			return err
		}
		return launcher.WriteStatus(os.Stdout, status, *asJSON)
	case "open":
		return launcher.New(launcher.Options{}).Open(ctx)
	case "uninstall":
		fs := flag.NewFlagSet("uninstall", flag.ContinueOnError)
		purge := fs.Bool("purge", false, "remove the managed distro and local state")
		if err := fs.Parse(args[1:]); err != nil {
			return err
		}
		return launcher.New(launcher.Options{}).Uninstall(ctx, *purge)
	default:
		return usage()
	}
}

func usage() error {
	fmt.Fprintln(os.Stderr, "usage: windowslauncher {install|start|stop|status|open|uninstall}")
	return fmt.Errorf("unknown or missing command")
}
