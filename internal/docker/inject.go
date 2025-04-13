package docker

import (
	"context"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

func (r *DockerRuntime) Inject(ctx context.Context, name string, path string, cmd []string) (string, error) {
	dockerFile, err := os.Open(filepath.Join(path, "Dockerfile"))
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
	return "", os.WriteFile(filepath.Join(path, "Dockerfile"), []byte(strings.Join(lines, "\n")), 0644)
}
