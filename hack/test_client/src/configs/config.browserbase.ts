export const payload: ((previousResult: Record<string, any>) => {
  name: string;
  arguments: Record<string, any>;
})[] = [
  () => ({
    name: "browserbase_create_session",
    arguments: {},
  }),
  () => ({
    name: "browserbase_navigate",
    arguments: {
      url: "https://fr.pairetfils.com",
    },
  }),
  () => ({
    name: "browserbase_get_content",
    arguments: {},
  }),
  () => ({
    name: "browserbase_close_session",
    arguments: {
      sessionId: "",
    },
  }),
];

export const description = "Browserbase description";
export const name = "browserbase";
export const url = "http://localhost:1400";
