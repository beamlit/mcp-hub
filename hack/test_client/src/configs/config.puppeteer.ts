export const payload: ((previousResult: Record<string, any>) => {
  name: string;
  arguments: Record<string, any>;
})[] = [
  () => ({
    name: "puppeteer_navigate",
    arguments: {
      url: "https://fr.pairetfils.com",
    },
  }),
  () => ({
    name: "puppeteer_select",
    arguments: {},
  }),
];

export const description = "Puppeteer description";
export const name = "puppeteer";
export const url = "http://localhost:1400";
