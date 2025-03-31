package builder

import (
	"os"
)

func (b *Build) Clean() {
	os.RemoveAll(tmpDir)
}
