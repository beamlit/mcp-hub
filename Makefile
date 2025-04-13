# This Makefile serves as a helper to run the MCP hub and the GitHub MCP server.
ARGS:= $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
REGISTRY:= ghcr.io/beamlit/hub

import:
	go run main.go import -c hub -m $(ARGS) --debug

run:
	go run main.go start -m $(ARGS) --debug

catalog:
	go run main.go catalog -m $(ARGS) --debug --skip-build

test:
	cd hack/test_client \
	&& cp src/configs/config.$(ARGS).ts src/config.ts \
	&& pnpm run test

agent-count:
	cd hack/mcp-agent \
	&& uv run main.py --count $(ARGS)

agent-server-id:
	cd hack/mcp-agent \
	&& uv run main.py --server-id $(ARGS)

agent-server-name:
	cd hack/mcp-agent \
	&& uv run main.py --server-name $(ARGS)

agent-server-run:
	sh scripts/test-run-server.sh $(ARGS)

agent-run:
	sh scripts/test-run.sh

agent:
	cd hack/mcp-agent && uv run main.py
	sh scripts/test-run.sh

%:
	@:
