export const payload: ((previousResult: Record<string, any>) => {
  name: string;
  arguments: Record<string, any>;
})[] = [];

export const description = "Browser automation and web scraping capabilities using Puppeteer";
export const name = "puppeteer";
export const url = "http://localhost:8080";