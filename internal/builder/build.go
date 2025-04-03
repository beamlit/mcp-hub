package builder

import (
	"context"
	"fmt"
	"path/filepath"
	"strings"

	"github.com/beamlit/mcp-hub/internal/files"
	"github.com/beamlit/mcp-hub/internal/hub"
)

func (b *Build) Build(name string, repository *hub.Repository) error {
	imageName := fmt.Sprintf("%s:%s", strings.ToLower(name), b.tag)
	language := strings.ToLower(repository.Build.Language)
	switch language {
	case "typescript", "javascript":
		err := b.prepareTypescript(repository)
		if err != nil {
			return fmt.Errorf("prepare typescript: %w", err)
		}
	case "python":
		fmt.Println("prepare python")
		err := b.preparePython(repository)
		if err != nil {
			return fmt.Errorf("prepare python: %w", err)
		}
	default:
		return fmt.Errorf("unsupported language: %s", language)
	}

	buildArgs := map[string]string{}
	if repository.Build.Command != "" {
		buildArgs["BUILD_COMMAND"] = repository.Build.Command
	}
	if repository.Build.Path != "" {
		buildArgs["BUILD_PATH"] = "/" + repository.Build.Path
	}
	if repository.Build.Output != "" {
		buildArgs["DIST_PATH"] = repository.Build.Output
	}
	smitheryDir := filepath.Join(repository.Source.Path, "smithery")
	dockerfileDir := filepath.Join(repository.Source.Path, "Dockerfile")
	var cmd []string
	switch language {
	case "typescript", "javascript":
		cmd = append(cmd, repository.Run.Entrypoint...)
	case "python":
		cmd = []string{"/usr/bin/python3", "-m", fmt.Sprintf("blaxel.%s", strings.ReplaceAll(repository.Build.Output, "/", "."))}
	}
	fmt.Println("Injecting command", cmd, "into Dockerfile", dockerfileDir, "in", repository.Source.LocalPath)
	_, err := b.runtime.Inject(context.Background(), name, fmt.Sprintf("%s/%s", repository.Source.LocalPath, repository.Source.Path), smitheryDir, dockerfileDir, cmd)
	if err != nil {
		return fmt.Errorf("inject: %w", err)
	}
	fmt.Println("buildArgs", buildArgs)
	err = b.runtime.Build(context.Background(), imageName, fmt.Sprintf("%s/%s", repository.Source.LocalPath, repository.Source.Path), buildArgs)
	if err != nil {
		return fmt.Errorf("build image: %w", err)
	}
	return nil
}

func (b *Build) preparePython(repository *hub.Repository) error {
	srcPath := repository.Source.LocalPath
	filesToCopy := map[string]string{
		"Dockerfile": "envs/python/Dockerfile",
		"Kraftfile":  "envs/python/Kraftfile",
		fmt.Sprintf("%s/transport.py", repository.Build.Output): "envs/python/transport.py",
	}
	for dst, src := range filesToCopy {
		err := files.CopyFile(src, filepath.Join(srcPath, dst))
		if err != nil {
			return fmt.Errorf("copy %s: %w", dst, err)
		}
	}
	err := files.AddLineToStartOfFile(
		filepath.Join(srcPath, "__init__.py"),
		"from .transport import websocket_server\nfrom .server import main\n",
	)
	if err != nil {
		return fmt.Errorf("add line to start of file: %w", err)
	}
	err = files.CreateFileIfNotExists(
		filepath.Join(srcPath, "__main__.py"),
		"from . import main\n\nif __name__ == '__main__':\n    main()",
	)
	if err != nil {
		return fmt.Errorf("create file: %w", err)
	}
	return nil
}

func (b *Build) prepareTypescript(repository *hub.Repository) error {
	basePath := repository.Source.LocalPath
	if repository.Build.Path != "" {
		basePath = filepath.Join(repository.Source.LocalPath, repository.Build.Path)
	}
	filesToCopy := map[string]string{
		"Dockerfile": "envs/typescript/Dockerfile",
		"Kraftfile":  "envs/typescript/Kraftfile",
	}
	for dst, src := range filesToCopy {
		err := files.CopyFile(src, filepath.Join(basePath, dst))
		if err != nil {
			return fmt.Errorf("copy %s: %w", dst, err)
		}
	}
	return nil
}
