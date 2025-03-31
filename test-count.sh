TYPESCRIPT_MCP_COUNT=$(grep -l "language: typescript" $(find ./hack/discovery/servers/catalog -name "*.yaml") | wc -l)
PYTHON_MCP_COUNT=$(grep -l "language: python" $(find ./hack/discovery/servers/catalog -name "*.yaml") | wc -l)

echo "TYPESCRIPT_MCP_COUNT: $TYPESCRIPT_MCP_COUNT"
echo "PYTHON_MCP_COUNT: $PYTHON_MCP_COUNT"

