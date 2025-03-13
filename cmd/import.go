package cmd

import (
	"log"
	"os"

	"github.com/beamlit/mcp-hub/internal/build"
	"github.com/beamlit/mcp-hub/internal/errors"
	"github.com/beamlit/mcp-hub/internal/hub"
	"github.com/spf13/cobra"
)

var importCmd = &cobra.Command{
	Use:   "import",
	Short: "Import MCPs from a config file",
	Long:  `import is a CLI tool to import MCPs from a config file`,
	Run:   runImport,
}

func init() {
	importCmd.Flags().StringVarP(&configPath, "config", "c", "", "The path to the config files")
	importCmd.Flags().BoolVarP(&push, "push", "p", false, "Push the images to the registry")
	importCmd.Flags().StringVarP(&registry, "registry", "r", "ghcr.io/beamlit/hub", "The registry to push the images to")
	importCmd.Flags().StringVarP(&mcp, "mcp", "m", "", "The MCP to import, if not provided, all MCPs will be imported")
	importCmd.Flags().BoolVarP(&skipBuild, "skip-build", "s", false, "Skip building the image")
	importCmd.Flags().StringVarP(&tag, "tag", "t", "latest", "The tag to use for the image")
	importCmd.Flags().BoolVarP(&debug, "debug", "d", false, "Enable debug mode, will not save the catalog")
	rootCmd.AddCommand(importCmd)
}

func runImport(cmd *cobra.Command, args []string) {
	if configPath == "" {
		configPath = "hub"
	}

	hub := hub.Hub{}
	errors.HandleError("read config file", hub.Read(configPath))
	errors.HandleError("validate config file", hub.ValidateWithDefaultValues())

	buildInstance := build.NewBuild(tag, debug)
	// defer buildInstance.Clean()

	for name, repository := range hub.Repositories {
		if mcp != "" && mcp != name {
			continue
		}
		_, err := buildInstance.CloneRepository(name, repository)
		if err != nil {
			log.Printf("Failed to process repository %s: %v", name, err)
			os.Exit(1)
		}
		err = buildInstance.BuildAndPushImage(name, repository)
		if err != nil {
			log.Printf("Failed to build and push image for repository %s: %v", name, err)
			os.Exit(1)
		}
	}
}
