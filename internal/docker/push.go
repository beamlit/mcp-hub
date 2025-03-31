package docker

import (
	"context"
	"os"
	"os/exec"
)

func (r *DockerRuntime) Push(ctx context.Context, imageName string) error {
	cmd := exec.Command("docker", "push", imageName)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	err := cmd.Run()
	if err != nil {
		return err
	}
	return nil
}
