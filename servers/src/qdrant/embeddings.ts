export interface EmbeddingsConfig {
	model: string;
	modelType: string;
	clientCredentials: string;
	baseUrl: string;
	workspace: string;
}

export class Embeddings {
	constructor(private readonly config: EmbeddingsConfig) {
		this.config = config;
	}

	async embed(query: string): Promise<number[]> {
		switch (this.config.modelType) {
			case 'openai':
				return this.openAIEmbed(query);
			default:
				throw new Error(`Unsupported model type: ${this.config.modelType}`);
		}
	}

	async openAIEmbed(query: string): Promise<number[]> {
		const { model } = this.config;
		const clientCreds = this.config.clientCredentials;
		if (!clientCreds) {
			throw new Error('BL_CLIENT_CREDENTIALS is not set');
		}
		const token = await fetch(`${this.config.baseUrl}/oauth/token`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Basic ${clientCreds}`,
			},
			body: JSON.stringify({
				grant_type: 'client_credentials',
			}),
		});
		type TokenResponse = {
			access_token: string;
			token_type: string;
			expires_in: number;
		};
		const tokenBody = (await token.json()) as TokenResponse;
		const request = new Request(`${this.config.baseUrl}/${this.config.workspace}/models/${model}/v1/embeddings`, {
			method: 'POST',
			body: JSON.stringify({
				input: query,
			}),
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${tokenBody.access_token}`,
			},
		});
		const response = await fetch(request);
		if (response.status >= 400) {
			throw new Error(`Failed to embed query: ${response.statusText}`);
		}
		const body = (await response.json()) as { data: [{ embedding: number[] }] };
		return body.data[0].embedding;
	}
}
