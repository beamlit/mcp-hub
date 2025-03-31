import { Transport } from "@modelcontextprotocol/sdk/shared/transport.js";
import {
  JSONRPCMessage,
  JSONRPCMessageSchema,
} from "@modelcontextprotocol/sdk/types.js";
import WebSocket from "ws";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { ListToolsResult } from "@modelcontextprotocol/sdk/types.js";

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 3000;

// Helper function to wait
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));


export class WebSocketClientTransport implements Transport {
    private _socket?: WebSocket;
    private _url: URL;
    private _headers: Record<string, string>;
  
    onclose?: () => void;
    onerror?: (error: Error) => void;
    onmessage?: (message: JSONRPCMessage) => void;
  
    constructor(url: URL, headers: Record<string, string>) {
      this._url = new URL(url.toString().replace("http", "ws"));
      this._headers = headers;
    }
  
    async start(): Promise<void> {
      if (this._socket) {
        throw new Error(
          "WebSocketClientTransport already started! If using Client class, note that connect() calls start() automatically."
        );
      }
  
      console.log("Starting WebSocket connection");
      let attempts = 0;
      while (attempts < MAX_RETRIES) {
        try {
          await this._connect();
          return;
        } catch (error) {
          attempts++;
          if (attempts === MAX_RETRIES) {
            throw error;
          }
          console.log(
            `WebSocket connection attempt ${attempts} failed, retrying in ${RETRY_DELAY_MS}ms...`
          );
          await delay(RETRY_DELAY_MS);
        }
      }
    }
  
    private _connect(): Promise<void> {
      console.log("Connecting to WebSocket");
      return new Promise((resolve, reject) => {
        this._socket = new WebSocket(this._url, {
          //protocols: SUBPROTOCOL,
          headers: this._headers,
        });
        console.log("WebSocket created");
        this._socket.onerror = (event) => {
          const error =
            "error" in event
              ? (event.error as Error)
              : new Error(`WebSocket error: ${JSON.stringify(event)}`);
          reject(error);
          this.onerror?.(error);
        };
        console.log("WebSocket onerror set");
        this._socket.onopen = () => {
          console.info("WebSocket opened");
          resolve();
        };
        console.log("WebSocket onopen set");
        this._socket.onclose = () => {
          console.info("WebSocket closed");
          this.onclose?.();
          this._socket = undefined;
        };
        console.log("WebSocket onclose set");
        this._socket.onmessage = (event: WebSocket.MessageEvent) => {
          console.info("WebSocket message received");
          let message: JSONRPCMessage;
          try {
            message = JSONRPCMessageSchema.parse(
              JSON.parse(event.data.toString())
            );
          } catch (error) {
            console.error(`Error parsing message: ${event.data}`);
            this.onerror?.(error as Error);
            return;
          }
          console.log("WebSocket message parsed");
          this.onmessage?.(message);
        };
      });
    }
  
    async close(): Promise<void> {
      this._socket?.close();
      this._socket = undefined;
      this.onclose?.();
    }
  
    async send(message: JSONRPCMessage): Promise<void> {
      let attempts = 0;
      console.log("Sending message");
      while (attempts < MAX_RETRIES) {
        try {
          if (!this._socket || this._socket.readyState !== WebSocket.OPEN) {
            if (!this._socket) {
              // Only try to start if socket doesn't exist
              console.log("Starting WebSocket connection");
              await this.start();
            } else {
              throw new Error("WebSocket is not in OPEN state");
            }
          }
          console.log("WebSocket socket is open");
          await new Promise<void>((resolve, reject) => {
            try {
              console.log("Sending message to WebSocket");
              console.log(message);
              this._socket?.send(JSON.stringify(message), (error) => {
                if (error) {
                  reject(error);
                } else {
                  resolve();
                }
              });
            } catch (error) {
              reject(error);
            }
          });
          return;
        } catch (error) {
          attempts++;
          if (attempts === MAX_RETRIES) {
            throw error;
          }
          console.log(
            `WebSocket send attempt ${attempts} failed, retrying in ${RETRY_DELAY_MS}ms...`
          );
          await delay(RETRY_DELAY_MS);
        }
      }
    }
  }

/**
 * Client for interacting with MCP (Model Context Protocol) services.
 */
export class MCPClient {
  private client: Client;
  private transport: Transport;

  constructor(client: Client, transport: Transport) {
    this.client = client;
    this.transport = transport;
  }

  /**
   * Retrieves a list of available tools from the MCP service.
   *
   * @returns {Promise<ListToolsResult>} The result containing the list of tools.
   * @throws Will throw an error if the request fails.
   */
  async listTools(): Promise<ListToolsResult> {
    if (this.client.transport === undefined) {
      try {
        await this.client.connect(this.transport);
      } catch (error) {
        throw new Error(`Failed to connect to MCP: ${error}`);
      }
    }
    return this.client.listTools();
  }
}

async function main() {
  const url = new URL("http://localhost:8080"); 
  const client = new Client(
      {
        name: "example-client",
        version: "1.0.0"
      },
      {
        capabilities: {
          prompts: {},
          resources: {},
          tools: {}
        }
      }
  );
  console.log("Creating transport");
  const transport = new WebSocketClientTransport(url, {});
  console.log("Connecting to MCP");
  await client.connect(transport);
  console.log("Connected to MCP");
  console.log("Listing tools");
  try {
      const tools = await client.listTools();
      console.log("Tools listed");
      console.log(JSON.stringify(tools, null, 2));
      await client.close();
      process.exit(0);
  } catch (error) {
      console.error("Error listing tools:", error);
      process.exit(1);
  }
}


main();
