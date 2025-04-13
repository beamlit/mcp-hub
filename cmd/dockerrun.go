package cmd

import (
	"log"
	"os"

	"github.com/beamlit/mcp-hub/internal/builder"
	"github.com/beamlit/mcp-hub/internal/docker"
	"github.com/beamlit/mcp-hub/internal/errors"
	"github.com/beamlit/mcp-hub/internal/hub"
	"github.com/joho/godotenv"
	"github.com/spf13/cobra"
)

var dockerrunCmd = &cobra.Command{
	Use:   "dockerrun",
	Short: "Run the MCP server in a docker container",
	Long:  `dockerrun is a CLI tool to run the MCP server in a docker container`,
	Run:   runDockerrun,
}

func init() {
	dockerrunCmd.Flags().StringVarP(&configPath, "config", "c", "hub", "The path to the config files")
	dockerrunCmd.Flags().StringVarP(&registry, "registry", "r", "ghcr.io/beamlit/hub", "The registry to push the images to")
	dockerrunCmd.Flags().StringVarP(&mcp, "mcp", "m", "", "The MCP to import, if not provided")
	dockerrunCmd.Flags().StringVarP(&tag, "tag", "t", "latest", "The tag to use for the image")
	dockerrunCmd.Flags().BoolVarP(&debug, "debug", "d", false, "Enable debug mode, will not save the catalog")
	rootCmd.AddCommand(dockerrunCmd)
}

func runDockerrun(cmd *cobra.Command, args []string) {
	// Load .env file if it exists
	if err := godotenv.Load(); err != nil {
		log.Printf("Warning: No .env file found or error loading it: %v", err)
	}

	if mcp == "" {
		log.Printf("MCP is required")
		os.Exit(1)
	}

	// We set debug to true to avoid saving the catalog in control plane
	debug = true

	hub := hub.Hub{}
	errors.HandleError("read config file", hub.Read(configPath))
	errors.HandleError("validate config file", hub.ValidateWithDefaultValues())

	repository := hub.Repositories[mcp]
	if repository == nil {
		log.Printf("Repository %s not found", mcp)
		os.Exit(1)
	}

	runtime := docker.NewRuntime()
	buildInstance := builder.NewBuild(tag, debug, runtime)
	defer buildInstance.Clean()

	err := buildInstance.Test(mcp, repository, true)
	if err != nil {
		log.Printf("Failed to test image for repository %s: %v", mcp, err)
		os.Exit(1)
	}
}
