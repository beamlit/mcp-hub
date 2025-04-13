package builder

import (
	"log"
	"os"
	"strings"

	"github.com/beamlit/mcp-hub/internal/hub"
)

func (b *Build) Test(name string, repository *hub.Repository, attached bool) error {
	envKeys := []string{}
	defaultEnvs := map[string]string{}
	for _, property := range repository.Run.Config {
		if property.Env == "" {
			continue
		} else if os.Getenv(property.Env) != "" {
			envKeys = append(envKeys, property.Env)
		} else if _, ok := defaultEnvs[property.Env]; ok {
			envKeys = append(envKeys, property.Env)
			os.Setenv(property.Env, defaultEnvs[property.Env])
		} else if property.Type == "integer" {
			envKeys = append(envKeys, property.Env)
			os.Setenv(property.Env, "12345")
		} else if strings.Contains(strings.ToLower(property.Env), "url") {
			envKeys = append(envKeys, property.Env)
			os.Setenv(property.Env, "https://example.com")
		} else {
			envKeys = append(envKeys, property.Env)
			os.Setenv(property.Env, "TEST_VALUE")
		}
	}
	log.Printf("Starting MCP %s", name)
	err := b.dockerRun(name, repository.Build.Language, envKeys, attached)
	if err != nil {
		log.Printf("Failed to run docker command: %v", err)
		os.Exit(1)
	}
	return nil
}
