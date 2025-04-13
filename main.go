package main

import (
	"log"

	"github.com/beamlit/mcp-hub/cmd"
	"github.com/joho/godotenv"
)

func LoadDotEnv() {
	err := godotenv.Load()
	if err != nil {
		log.Fatal("Error loading .env file")
	}
}

func main() {
	LoadDotEnv()
	cmd.Execute()
}
