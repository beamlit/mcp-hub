package builder

import (
	"fmt"
	"strings"

	"github.com/beamlit/mcp-hub/internal/git"
	"github.com/beamlit/mcp-hub/internal/hub"
)

func (b *Build) CloneRepository(name string, repository *hub.Repository) (string, error) {
	var repoPath string
	//imageName := fmt.Sprintf("%s:%s", strings.ToLower(name), b.tag)
	if repository.Source.LocalPath != "" {
		repoPath = repository.Source.LocalPath
	} else {
		repoPath = fmt.Sprintf("%s/%s/%s", tmpDir, strings.TrimPrefix(repository.Source.Repository, githubPrefix), repository.Source.Branch)
	}

	if repository.Disabled {
		return "", nil
		// c := catalog.Catalog{}
		// errors.HandleError("load catalog", c.Load(name, repository, imageName))
		// if !b.debug {
		// 	errors.HandleError("save catalog", c.Save())
		// }
		// return &c, nil
	}

	if repository.Source.LocalPath == "" {
		if _, err := git.CloneRepository(repoPath, repository.Source.Branch, repository.Source.Repository); err != nil {
			return "", fmt.Errorf("clone repository: %w", err)
		}
		repository.Source.LocalPath = repoPath
	}

	// c := catalog.Catalog{}
	// errors.HandleError("load catalog", c.Load(name, repository, imageName))
	// if !b.debug {
	// 	errors.HandleError("save catalog", c.Save())
	// }
	return repoPath, nil
}
