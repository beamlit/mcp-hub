package builder

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/beamlit/mcp-hub/internal/docker"
	"github.com/beamlit/mcp-hub/internal/files"
	"github.com/beamlit/mcp-hub/internal/hub"
)

func (b *Build) Build(name string, repository *hub.Repository) error {
	imageName := fmt.Sprintf("%s:%s", strings.ToLower(name), b.tag)
	switch repository.Language {
	case "typescript":
		err := b.prepareTypescript(name, repository)
		if err != nil {
			return fmt.Errorf("prepare typescript: %w", err)
		}
	default:
		return fmt.Errorf("unsupported language: %s", repository.Language)
	}

	buildArgs := map[string]string{}
	if repository.BasePath != "" {
		buildArgs["BUILD_PATH"] = "/" + repository.BasePath
	}
	if repository.DistPath != "" {
		buildArgs["DIST_PATH"] = repository.DistPath
	}
	fmt.Println("buildArgs", buildArgs)
	err := docker.BuildImage(context.Background(), imageName, repository.Path, buildArgs)
	if err != nil {
		return fmt.Errorf("build image: %w", err)
	}

	return nil
}

func (b *Build) prepareTypescript(name string, repository *hub.Repository) error {
	basePath := repository.Path
	if repository.BasePath != "" {
		basePath = filepath.Join(repository.Path, repository.BasePath)
	}

	srcPath := repository.Path
	if repository.SrcPath != "" {
		srcPath = filepath.Join(repository.Path, repository.SrcPath)
	}

	packageJson, err := os.ReadFile(filepath.Join(basePath, "package.json"))
	if err != nil {
		return fmt.Errorf("read package.json: %w", err)
	}
	type PackageJson struct {
		Type string `json:"type"`
	}
	var pj PackageJson
	err = json.Unmarshal(packageJson, &pj)
	if err != nil {
		return fmt.Errorf("unmarshal package.json: %w", err)
	}

	err = files.CopyFile("envs/typescript/Dockerfile", filepath.Join(repository.Path, "Dockerfile"))
	if err != nil {
		return fmt.Errorf("copy dockerfile: %w", err)
	}
	if pj.Type == "module" {
		err = files.CopyMergeDir("envs/typescript/esm", srcPath)
	} else {
		return fmt.Errorf("unsupported package.json type: %s, only module is supported", pj.Type)
	}
	if err != nil {
		return fmt.Errorf("copy overrides: %w", err)
	}
	return nil
}
