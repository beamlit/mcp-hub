import * as fs from 'fs';
import * as yaml from 'js-yaml';
import * as path from 'path';
import { exit } from "process";
import { getClient } from "./client";
import { name, payload, url } from "./config"; // TODO: Update here like: /configs/config.exa

const main = async () => {
  const client = await getClient(url.replace("http://", "ws://"), name);
  const result = await client.listTools();

  // Write to YAML file
  // Read the repository's context7.yaml file to get additional fields
  try {
    const outputPath = path.join(process.cwd(), '..', '..', 'hub', `${name}.yaml`);
    const contextFilePath = path.join(process.cwd(), '..', '..', 'hub', `${name}.yaml`);
    if (fs.existsSync(contextFilePath)) {
      const contextYaml = yaml.load(fs.readFileSync(contextFilePath, 'utf8')) as Record<string, any>;

      // Add the field from ${name}.yaml to the output file
      const updatedYaml = {
        ...contextYaml,
        tools: result.tools
      };
      fs.writeFileSync(outputPath, yaml.dump(updatedYaml));
      console.info(`Updated ${outputPath} with fields from ${name}.yaml`);
    }
  } catch (error) {
    console.error(`Error adding fields from ${name}.yaml: ${error}`);
  }
  for (const fn of result.tools) {
    let params: string[] = [];
    if (fn.inputSchema) {
      params = Object.keys(fn.inputSchema.properties || {});
    }
    console.info(`${fn.name} (${params.join(", ")})`);
  }

  let previousResult: Record<string, any> = {};
  for (const fn of payload) {
    const params = fn(previousResult);
    const tool = result.tools.find((f: { name: string }) => f.name === params.name);
    if (!tool) {
      console.error(`Tool with name ${params.name} not found`);
      exit(1);
    }
    try {
      const result = await client.callTool({
        name: params.name,
        arguments: params.arguments,
      });
      const content = result.content as { text: string }[];
      if (content && content.length > 0 && content[0].text) {
        try {
          previousResult[params.name] = JSON.parse(content[0].text);
        } catch {
          previousResult[params.name] = content[0].text;
        }
        console.log(`Result: ${params.name}`, previousResult[params.name]);
      } else {
        console.log(`Result: ${params.name}`, result);
      }
    } catch (error) {
      console.log(`Error: ${params.name}`, error);
    }
  }
  exit(0);
};

main();
