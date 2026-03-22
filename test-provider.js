// Custom PromptFoo provider - calls the Network Guardian AI backend API
// Works with promptfoo 0.120+

export class NetworkGuardianProvider {
  constructor() {
    this.apiUrl = 'http://localhost:8000/analyze';
  }

  id() {
    return 'network-guardian-api';
  }

  async callApi(prompt, context) {
    const domain = context?.vars?.domain;
    if (!domain) {
      throw new Error('No domain provided in vars');
    }

    try {
      const response = await fetch(this.apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain }),
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const result = await response.json();
      return JSON.stringify(result);
    } catch (error) {
      throw new Error(`Failed to analyze ${domain}: ${error.message}`);
    }
  }

  async call(prompt, context) {
    return this.callApi(prompt, context);
  }
}

export default NetworkGuardianProvider;
