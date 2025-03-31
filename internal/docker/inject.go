package docker

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

func (r *DockerRuntime) Inject(ctx context.Context, name string, path string, smitheryDir string, dockerfileDir string, cmd []string) (string, error) {
	fmt.Println("Injecting command", cmd, "into Dockerfile", dockerfileDir)
	dockerFile, err := os.Open(filepath.Join(path, dockerfileDir))
	if err != nil {
		return "", err
	}
	defer dockerFile.Close()

	dockerFileBytes, err := io.ReadAll(dockerFile)
	if err != nil {
		return "", err
	}

	dockerFileString := string(dockerFileBytes)
	var lines []string

	for _, line := range strings.Split(dockerFileString, "\n") {
		if line == "" {
			continue
		}
		lines = append(lines, line)
	}
	lines[len(lines)-1] = ""
	var entrypoint string
	for i, args := range cmd {
		var cmdDockerFormat string
		if i == 0 {
			cmdDockerFormat = fmt.Sprintf("\"%s\"", args)
		} else {
			cmdDockerFormat = fmt.Sprintf(",\"%s\"", args)
		}
		entrypoint = fmt.Sprintf("%s %s", entrypoint, cmdDockerFormat)
	}
	lines[len(lines)-1] = fmt.Sprintf("ENTRYPOINT [%s]", entrypoint)
	return "", os.WriteFile(filepath.Join(path, dockerfileDir), []byte(strings.Join(lines, "\n")), 0644)
}
