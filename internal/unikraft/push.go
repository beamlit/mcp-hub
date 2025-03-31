package unikraft

import (
	"context"
	"fmt"
)

func (r *UnikraftRuntime) Push(ctx context.Context, imageName string) error {
	fmt.Println("Pushing image", imageName, "do nothing for now in unikraft")
	return nil
	// cmd := exec.Command(
	// 	"docker", "push",
	// 	imageName,
	// )
	// cmd.Stdout = os.Stdout
	// cmd.Stderr = os.Stderr
	// err := cmd.Run()
	// if err != nil {
	// 	return err
	// }
	// return nil
}
