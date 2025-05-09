package hub

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"

	"github.com/blaxel-ai/mcp-hub/internal/smithery"
	"gopkg.in/yaml.v2"
)

type Hub struct {
	Repositories map[string]*Repository `yaml:"repositories"`
}

type PackageManager string

const (
	PackageManagerAPK PackageManager = "apk"
	PackageManagerAPT PackageManager = "apt"
)

type Repository struct {
	Repository      string                   `yaml:"repository" mendatory:"false"`
	Path            string                   `yaml:"path" mendatory:"false"`
	SmitheryPath    string                   `yaml:"smitheryPath" mendatory:"false" default:"smithery.yaml"`
	Smithery        *smithery.SmitheryConfig `yaml:"smithery" mendatory:"false"`
	Dockerfile      string                   `yaml:"dockerfile" mendatory:"false" default:"Dockerfile"`
	PackageManager  PackageManager           `yaml:"packageManager" mendatory:"false" default:"apk"`
	DoNotShow       []string                 `yaml:"doNotShow" mendatory:"false"`
	HasNPM          bool                     `yaml:"hasNPM" mendatory:"false" default:"true"`
	Branch          string                   `yaml:"branch" mendatory:"false" default:"main"`
	URL             string                   `yaml:"url" mendatory:"false"`
	DisplayName     string                   `yaml:"displayName" mendatory:"true"`
	Icon            string                   `yaml:"icon" mendatory:"true"`
	Disabled        bool                     `yaml:"disabled" mendatory:"false" default:"false"`
	Description     string                   `yaml:"description" mendatory:"true"`
	LongDescription string                   `yaml:"longDescription" mendatory:"true"`
	Enterprise      bool                     `yaml:"enterprise" mendatory:"false" default:"false"`
	ComingSoon      bool                     `yaml:"comingSoon" mendatory:"false" default:"false"`
	Secrets         []string                 `yaml:"secrets" mendatory:"false"`
	HiddenSecrets   []string                 `yaml:"hiddenSecrets" mendatory:"false"`
	OAuth           *OAuth                   `yaml:"oauth" mendatory:"false"`
	Integration     string                   `yaml:"integration" mendatory:"false"`
	Tags            []string                 `yaml:"tags"`
	Categories      []string                 `yaml:"categories"`
}

type OAuth struct {
	Type   string   `yaml:"type"`
	Scopes []string `yaml:"scopes"`
}

func (h *Hub) Read(path string) error {
	h.Repositories = make(map[string]*Repository)
	files, err := os.ReadDir(path)
	if err != nil {
		return err
	}

	for _, file := range files {
		if file.IsDir() {
			continue
		}

		yamlFile, err := os.ReadFile(filepath.Join(path, file.Name()))
		if err != nil {
			return err
		}

		var repo Repository
		if err := yaml.Unmarshal(yamlFile, &repo); err != nil {
			return err
		}

		// Use filename without extension as repository name
		name := strings.TrimSuffix(file.Name(), filepath.Ext(file.Name()))
		h.Repositories[name] = &repo
	}
	return nil
}

// ValidateWithDefaultValues validates the hub and applies default values to empty fields
// This is useful to validate the hub before running the import command
func (h *Hub) ValidateWithDefaultValues() error {
	if h.Repositories == nil {
		return errors.New("repositories is required")
	}

	var errs []error

	for name, repository := range h.Repositories {
		// Use reflection to validate struct tags
		v := reflect.ValueOf(repository).Elem() // Get the element the pointer refers to
		t := v.Type()

		for i := 0; i < t.NumField(); i++ {
			field := t.Field(i)
			value := v.Field(i)

			// Check mandatory fields
			if mandatory, ok := field.Tag.Lookup("mendatory"); ok && mandatory == "true" {
				if value.IsZero() {
					errs = append(errs, fmt.Errorf("field %s is required in repository %s", field.Name, name))
				}
			}

			// Apply default values for empty fields
			if defaultVal, ok := field.Tag.Lookup("default"); ok && value.IsZero() {
				switch value.Kind() {
				case reflect.String:
					value.SetString(defaultVal)
				case reflect.Bool:
					value.SetBool(defaultVal == "true")
				}
			}
		}
	}

	return errors.Join(errs...)
}
