export const payload: ((previousResult: Record<string, any>) => {
  name: string;
  arguments: Record<string, any>;
})[] = [];

export const description = "Send emails using Resend's API";
export const name = "resend";
export const url = "http://localhost:8080";