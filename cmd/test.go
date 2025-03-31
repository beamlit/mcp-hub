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

var testCmd = &cobra.Command{
	Use:   "test",
	Short: "Test the MCP server",
	Long:  `test is a CLI tool to test the MCP server`,
	Run:   runTest,
}

func init() {
	testCmd.Flags().StringVarP(&configPath, "config", "c", "hub", "The path to the config files")
	testCmd.Flags().StringVarP(&registry, "registry", "r", "ghcr.io/beamlit/hub", "The registry to push the images to")
	testCmd.Flags().StringVarP(&mcp, "mcp", "m", "", "The MCP to import, if not provided")
	testCmd.Flags().StringVarP(&tag, "tag", "t", "latest", "The tag to use for the image")
	testCmd.Flags().BoolVarP(&debug, "debug", "d", false, "Enable debug mode, will not save the catalog")
	rootCmd.AddCommand(testCmd)
}

func runTest(cmd *cobra.Command, args []string) {
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

	_, err := buildInstance.CloneRepository(mcp, repository)
	if err != nil {
		log.Printf("Failed to process repository %s: %v", mcp, err)
		os.Exit(1)
	}
	err = buildInstance.Build(mcp, repository)
	if err != nil {
		log.Printf("Failed to build image for repository %s: %v", mcp, err)
		os.Exit(1)
	}

	err = buildInstance.Test(mcp, repository)
	if err != nil {
		log.Printf("Failed to test image for repository %s: %v", mcp, err)
		os.Exit(1)
	}
}
