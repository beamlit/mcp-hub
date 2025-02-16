// @ts-ignore
import WebSocket from "ws";
// @ts-ignore
global.WebSocket = WebSocket;

import { logger, newClient } from "@beamlit/sdk";
import { LocalToolkit } from "@beamlit/sdk/functions/local.js";
import { description, name, payload, url } from "./config.js";

const main = async () => {
  const client = newClient();
  const toolkit = new LocalToolkit(client, name, url);
  await toolkit.initialize(name, description);
  const functions = await toolkit.getTools();
  for (const fn of functions) {
    let params: string[] = [];
    if (fn.schema && "shape" in fn.schema) {
      const schema = fn.schema.shape;
      params = Object.keys(schema);
    }
    logger.info(`${fn.name} (${params.join(", ")})`);
  }

  let previousResult: Record<string, any> = {};
  for (const fn of payload) {
    const params = fn(previousResult);
    const tool = functions.find((f) => f.name === params.name);
    if (!tool) {
      logger.error(`Tool with name ${params.name} not found`);
      return;
    }
    try {
      const result = await tool.invoke(params.arguments);
      const parsedResult = JSON.parse(result);
      if (parsedResult.length > 0 && parsedResult[0].text) {
        try {
          previousResult[params.name] = JSON.parse(parsedResult[0].text);
        } catch {
          previousResult[params.name] = parsedResult[0].text;
        }
        console.log(`Result: ${params.name}`, previousResult[params.name]);
      } else {
        console.log(`Result: ${params.name}`, parsedResult);
      }
    } catch (error) {
      console.log(`Error: ${params.name}`, error);
    }
  }
};

main();
