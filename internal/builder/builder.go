package builder

import "context"

type Build struct {
	tag     string
	debug   bool
	runtime Runtime
}

type Runtime interface {
	Inject(ctx context.Context, name string, path string, smitheryDir string, dockerfileDir string, cmd []string) (string, error)
	Build(ctx context.Context, imageName string, repoPath string, buildArgs map[string]string) error
	Push(ctx context.Context, imageName string) error
}

const (
	tmpDir       = "tmp"
	githubPrefix = "https://github.com/"
)

func NewBuild(tag string, debug bool, runtime Runtime) *Build {
	buildInstance := &Build{
		tag:     tag,
		debug:   debug,
		runtime: runtime,
	}
	buildInstance.Clean()
	return buildInstance
}
