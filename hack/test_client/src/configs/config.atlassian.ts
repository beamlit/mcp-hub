export const payload: ((previousResult: Record<string, any>) => {
  name: string;
  arguments: Record<string, any>;
})[] = [];

export const description = "Atlassian Cloud MCP Server";
export const name = "atlassian";
export const url = "http://localhost:8080";