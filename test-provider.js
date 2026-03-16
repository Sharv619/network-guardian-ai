// Custom PromptFoo provider - calls the Network Guardian AI backend API
async function callApi(domain) {
  const response = await fetch('http://localhost:8000/analyze', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ domain }),
  });
  
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }
  
  return response.json();
}

module.exports = {
  id: 'network-guardian-api',
  async callApi(prompt, context) {
    const domain = context.vars.domain;
    if (!domain) {
      throw new Error('No domain provided');
    }
    
    try {
      const result = await callApi(domain);
      return JSON.stringify(result);
    } catch (error) {
      throw new Error(`Failed to analyze ${domain}: ${error.message}`);
    }
  },
};
