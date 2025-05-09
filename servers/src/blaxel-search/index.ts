import { call as braveCall, list as braveList } from '../brave-search';
import { ListToolsResponse, ToolResponse } from '../types';

export const infos = async () => {
	return {
		name: 'blaxel-search',
		displayName: 'Blaxel Search',
		categories: ['search'],
		integration: 'blaxel-search',
		description: 'Search the web for information',
		icon: 'https://app.blaxel.ai/logo_short.png',
		url: 'https://app.blaxel.ai',
		form: {
			config: {},
			secrets: {},
		},
	};
};

export async function list(): Promise<ListToolsResponse> {
	const tmp = await braveList();
	const tools = tmp.tools.map((tool) => {
		return {
			...tool,
			name: `blaxel_${tool.name.replace('brave_', '')}`,
		};
	});
	return { tools };
}

export async function call(request: Request, config: Record<string, string>, secrets: Record<string, string>): Promise<ToolResponse> {
	const body: { name: string; arguments: Record<string, string> } = (await request.json()) as {
		name: string;
		arguments: Record<string, string>;
	};
	body.name = body.name.replace('blaxel_', 'brave_');
	const rewriteSecrets = {
		apiKey: process.env.API_KEY || '',
	};
	const call = await braveCall(request, config, rewriteSecrets, body);
	return call;
}
