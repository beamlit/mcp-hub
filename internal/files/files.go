package files

import (
	"io"
	"os"
	"path/filepath"
)

func MoveFile(src, dst string) error {
	if err := CopyFile(src, dst); err != nil {
		return err
	}
	return os.Remove(src)
}

func CopyFile(src, dst string) error {
	sourceFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer sourceFile.Close()

	destFile, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer destFile.Close()

	_, err = io.Copy(destFile, sourceFile)
	if err != nil {
		return err
	}

	// Copy file permissions
	sourceInfo, err := os.Stat(src)
	if err != nil {
		return err
	}

	return os.Chmod(dst, sourceInfo.Mode())
}

func CopyMergeDir(src, dst string) error {
	files, err := os.ReadDir(src)
	if err != nil {
		return err
	}
	for _, file := range files {
		if file.IsDir() {
			err := CopyMergeDir(filepath.Join(src, file.Name()), filepath.Join(dst, file.Name()))
			if err != nil {
				return err
			}
		} else {
			err := CopyFile(filepath.Join(src, file.Name()), filepath.Join(dst, file.Name()))
			if err != nil {
				return err
			}
		}
	}
	return nil
}
