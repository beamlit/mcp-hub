PYTHON="aws_resources_mcp_server.yaml cite_mcp.yaml clickhouse_mcp_server.yaml duckduckgo_mcp_server.yaml elasticsearch_7.x_mcp_server.yaml emqx_mcp_server.yaml kagi_mcp_server.yaml mcp_dbutils.yaml mcp_development_framework.yaml mcp_email_server.yaml mcp_sentry.yaml mcp_server_for_opensearch.yaml mcp_server_memos.yaml mcp_server_redis.yaml mcp_server_template_for_cursor_ide.yaml mcp_stripe_server.yaml mysqldb_mcp_server.yaml openai_mcp_server.yaml scrapegraph_mcp_server.yaml world_bank_mcp_server.yaml xiyan_mcp_server.yaml"

mkdir -p hack/discovery/servers/catalog/python-run-failed
for server in $PYTHON; do
    mv hack/discovery/servers/catalog/$server hack/discovery/servers/catalog/python-run-failed/$server
done
