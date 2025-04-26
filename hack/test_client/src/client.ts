import { BlaxelMcpClientTransport } from "@blaxel/sdk";
import { Client as ModelContextProtocolClient } from "@modelcontextprotocol/sdk/client/index.js";

export async function getClient(url: string, name: string): Promise<ModelContextProtocolClient> {
  const transport = new BlaxelMcpClientTransport(url);

  const client = new ModelContextProtocolClient(
    {
      name: name,
      version: "1.0.0",
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );
  await client.connect(transport);
  return client;
}