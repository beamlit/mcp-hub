package cmd

import (
	"fmt"
	"log"
	"os"

	"github.com/beamlit/mcp-hub/internal/builder"
	"github.com/beamlit/mcp-hub/internal/docker"
	"github.com/beamlit/mcp-hub/internal/errors"
	"github.com/beamlit/mcp-hub/internal/hub"
	"github.com/beamlit/mcp-hub/internal/unikraft"
	"github.com/spf13/cobra"
)

var importCmd = &cobra.Command{
	Use:   "import",
	Short: "Import MCPs from a config file",
	Long:  `import is a CLI tool to import MCPs from a config file`,
	Run:   runImport,
}

func init() {
	importCmd.Flags().StringVarP(&configPath, "config", "c", "hub", "The path to the config files")
	importCmd.Flags().BoolVarP(&push, "push", "p", false, "Push the images to the registry")
	importCmd.Flags().StringVarP(&registry, "registry", "r", "ghcr.io/beamlit/hub", "The registry to push the images to")
	importCmd.Flags().StringVarP(&mcp, "mcp", "m", "", "The MCP to import, if not provided, all MCPs will be imported")
	importCmd.Flags().StringVarP(&tag, "tag", "t", "latest", "The tag to use for the image")
	importCmd.Flags().BoolVarP(&debug, "debug", "d", false, "Enable debug mode, will not save the catalog")
	importCmd.Flags().StringVar(&platform, "platform", "docker", "The platform to build the image for (docker, unikraft)")
	rootCmd.AddCommand(importCmd)
}

func runImport(cmd *cobra.Command, args []string) {
	hub := hub.Hub{}
	errors.HandleError("read config file", hub.Read(configPath))
	errors.HandleError("validate config file", hub.ValidateWithDefaultValues())

	var runtime builder.Runtime
	switch platform {
	case "docker":
		runtime = docker.NewRuntime()
	case "unikraft":
		runtime = unikraft.NewRuntime()
	default:
		log.Fatalf("Unsupported platform: %s", platform)
	}
	buildInstance := builder.NewBuild(tag, debug, runtime)
	// defer buildInstance.Clean()

	var errs []error

	for name, repository := range hub.Repositories {
		if mcp != "" && mcp != name {
			continue
		}
		_, err := buildInstance.CloneRepository(name, repository)
		if err != nil {
			errs = append(errs, fmt.Errorf("failed to process repository %s: %w", name, err))
			continue
		}
		err = buildInstance.Build(name, repository)
		if err != nil {
			errs = append(errs, fmt.Errorf("failed to build image for repository %s: %w", name, err))
			continue
		}
		if push {
			err = buildInstance.Push(name, repository)
			if err != nil {
				errs = append(errs, fmt.Errorf("failed to push image for repository %s: %w", name, err))
				continue
			}
		}
	}
	if len(errs) > 0 {
		for _, err := range errs {
			log.Printf("Error: %v", err)
		}
		os.Exit(1)
	}
}
