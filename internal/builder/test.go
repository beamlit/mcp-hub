package builder

import (
	"log"
	"os"

	"github.com/beamlit/mcp-hub/internal/hub"
)

func (b *Build) Test(name string, repository *hub.Repository) error {
	envKeys := []string{}
	for _, property := range repository.Run.Config {
		if property.Env == "" {
			continue
		}
		envKeys = append(envKeys, property.Env)
		os.Setenv(property.Env, "TEST_VALUE")
	}
	log.Printf("Starting MCP %s", name)
	err := b.dockerRun(name, repository.Build.Language, envKeys, false)
	if err != nil {
		log.Printf("Failed to run docker command: %v", err)
		os.Exit(1)
	}
	return nil
}
