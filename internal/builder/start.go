package builder

import (
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"

	"github.com/beamlit/mcp-hub/internal/hub"
)

func (b *Build) Start(name string, repository *hub.Repository) error {

	envKeys := []string{}
	for _, property := range repository.Run.Config {
		if property.Env == "" {
			continue
		}
		envKeys = append(envKeys, property.Env)
		err := b.checkEnvironmentVariable(name, repository.Run.Config, property.Env)
		if err != nil {
			log.Printf("environment variable %s is not set and is required for the MCP %s", property.Env, name)
			os.Exit(1)
		}
	}
	log.Printf("Starting MCP %s", name)
	err := b.dockerRun(name, repository.Build.Language, envKeys, true)
	if err != nil {
		log.Printf("Failed to run docker command: %v", err)
		os.Exit(1)
	}

	return nil
}

func (b *Build) dockerRun(mcp string, language string, envKeys []string, attached bool) error {
	name := fmt.Sprintf("mcp-hub-%s", mcp)
	exec.Command("docker", "rm", "-f", name).Run()
	image := fmt.Sprintf("%s:%s", strings.ToLower(mcp), b.tag)
	dockerRunCmd := []string{}
	if attached {
		dockerRunCmd = []string{"run", "--rm", "-i", "-p", "8080:8080", "--platform", "linux/amd64", "--name", name}
		for _, key := range envKeys {
			dockerRunCmd = append(dockerRunCmd, "-e", fmt.Sprintf("%s=%s", key, os.Getenv(key)))
		}
		dockerRunCmd = append(dockerRunCmd, image)
	} else {
		dockerRunCmd = []string{"run", "--rm", "-d", "-p", "8080:8080", "--platform", "linux/amd64", "--name", name}
		for _, key := range envKeys {
			dockerRunCmd = append(dockerRunCmd, "-e", fmt.Sprintf("%s=%s", key, os.Getenv(key)))
		}
		dockerRunCmd = append(dockerRunCmd, image)
	}
	cmd := exec.Command("docker", dockerRunCmd...)
	// Connect command's stdout and stderr to our process stdout and stderr
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	// Run the command and wait for it to finish
	err := cmd.Run()
	if err != nil {
		return fmt.Errorf("failed to run docker command \"docker %s\": %v", strings.Join(dockerRunCmd, " "), err)
	}
	return nil
}

func (b *Build) checkEnvironmentVariable(mcp string, envs map[string]hub.Property, val string) error {
	trimedVal := strings.Trim(val, "$")
	required := false

	if _, ok := envs[trimedVal]; ok {
		required = envs[trimedVal].Required
	}

	if required && os.Getenv(trimedVal) == "" {
		return fmt.Errorf("environment variable %s is not set and is required for the MCP %s", trimedVal, mcp)
	}
	return nil
}
