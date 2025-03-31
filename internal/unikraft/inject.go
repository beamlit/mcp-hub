package unikraft

import (
	"context"
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v2"
)

type Kraftfile struct {
	Spec    string            `yaml:"spec"`
	Runtime string            `yaml:"runtime"`
	Rootfs  string            `yaml:"rootfs"`
	Cmd     []string          `yaml:"cmd"`
	Labels  map[string]string `yaml:"labels"`
}

func (r *UnikraftRuntime) Inject(ctx context.Context, name string, path string, smitheryDir string, dockerfileDir string, cmd []string) (string, error) {
	kraftFilePath := filepath.Join(path, "Kraftfile")
	if smitheryDir == "@mcp-hub" {
		fmt.Println("Ignoring @mcp-hub Kraftfile")
		return "", nil
	}

	// First read the existing file
	kraftFileBytes, err := os.ReadFile(kraftFilePath)
	if err != nil {
		return "", err
	}

	var kraftFileData Kraftfile
	err = yaml.Unmarshal(kraftFileBytes, &kraftFileData)
	if err != nil {
		return "", err
	}

	kraftFileData.Cmd = cmd

	yamlBytes, err := yaml.Marshal(kraftFileData)
	if err != nil {
		return "", err
	}

	// Now write to the file with proper write permissions
	err = os.WriteFile(kraftFilePath, yamlBytes, 0644)
	if err != nil {
		return "", err
	}

	return kraftFilePath, nil
}
