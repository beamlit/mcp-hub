package hub

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"

	"gopkg.in/yaml.v2"
)

type Hub struct {
	Repositories map[string]*Repository `yaml:"repositories"`
}

type Repository struct {
	Name               string   `yaml:"name" mandatory:"true"`
	DisplayName        string   `yaml:"displayName" mandatory:"true"`
	Description        string   `yaml:"description" mandatory:"true"`
	LongDescription    string   `yaml:"longDescription" mandatory:"true"`
	Documentation      string   `yaml:"documentation" mandatory:"false"`
	GetCredentialsLink string   `yaml:"getCredentialsLink" mandatory:"false"`
	Icon               string   `yaml:"icon" mandatory:"true"`
	Integration        string   `yaml:"integration" mandatory:"false"`
	Categories         []string `yaml:"categories" mandatory:"true"`
	Version            string   `yaml:"version" mandatory:"true"`
	//Tools              []Tool   `yaml:"tools" mandatory:"false"`
	Disabled   bool   `yaml:"disabled" mandatory:"false"`
	Enterprise bool   `yaml:"enterprise" mandatory:"false"`
	ComingSoon bool   `yaml:"comingSoon" mandatory:"false"`
	Source     Source `yaml:"source" mandatory:"true"`
	Build      Build  `yaml:"build" mandatory:"true"`
	Run        Run    `yaml:"run" mandatory:"true"`
}

type Tool struct {
	Name         string `yaml:"name" mandatory:"true"`
	Description  string `yaml:"description" mandatory:"true"`
	InputSchema  Schema `yaml:"inputSchema" mandatory:"true"`
	OutputSchema Schema `yaml:"outputSchema" mandatory:"true"`
}

type Schema struct {
	Type       string              `yaml:"type" mandatory:"true"`
	Properties map[string]Property `yaml:"properties" mandatory:"true"`
}

type Source struct {
	Repository string `yaml:"repository" mandatory:"true"`
	Branch     string `yaml:"branch" mandatory:"true"`
	Path       string `yaml:"path" mandatory:"false"`
	LocalPath  string `yaml:"localPath" mandatory:"false"`
}

type Build struct {
	Language     string   `yaml:"language" mandatory:"true"`
	Command      string   `yaml:"command" mandatory:"true"`
	Output       string   `yaml:"output" mandatory:"true"`
	Dependencies []string `yaml:"dependencies" mandatory:"false"`
}

type Run struct {
	Config     map[string]Property `yaml:"config" mandatory:"true"`
	Entrypoint []string            `yaml:"entrypoint" mandatory:"true"`
}

type Property struct {
	Type     string   `yaml:"type" mandatory:"true"`
	Required bool     `yaml:"required" mandatory:"true"`
	Default  string   `yaml:"default" mandatory:"false"`
	Enum     []string `yaml:"enum" mandatory:"false"`
	Env      string   `yaml:"env" mandatory:"false"`
	Arg      string   `yaml:"arg" mandatory:"false"`
	Hidden   bool     `yaml:"hidden" mandatory:"false"`
	Secret   bool     `yaml:"secret" mandatory:"false"`
	Label    string   `yaml:"label" mandatory:"false"`
	Min      int      `yaml:"min" mandatory:"false"`
	Max      int      `yaml:"max" mandatory:"false"`
	Pattern  string   `yaml:"pattern" mandatory:"false"`
	Format   string   `yaml:"format" mandatory:"false"`
	Example  string   `yaml:"example" mandatory:"false"`
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
			if mandatory, ok := field.Tag.Lookup("mandatory"); ok && mandatory == "true" {
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
