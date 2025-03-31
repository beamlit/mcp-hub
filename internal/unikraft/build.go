package unikraft

import (
	"context"
	"fmt"
)

func (r *UnikraftRuntime) Build(ctx context.Context, imageName string, repoPath string, buildArgs map[string]string) error {
	fmt.Println("Building image", imageName, "in directory", repoPath, "with args", buildArgs, "do nothing for now in unikraft")
	return nil
	// fmt.Println("Building image", imageName, "in directory", repoPath)
	// cmd := exec.Command(
	// 	"docker", "build",
	// 	"--platform", "linux/amd64",
	// 	"-t", imageName,
	// 	".",
	// )
	// for k, v := range buildArgs {
	// 	cmd.Args = append(cmd.Args, "--build-arg", fmt.Sprintf("%s=%s", k, v))
	// }
	// cmd.Stdout = os.Stdout
	// cmd.Stderr = os.Stderr
	// cmd.Dir = repoPath
	// err := cmd.Run()
	// if err != nil {
	// 	return err
	// }
	// return nil
}
