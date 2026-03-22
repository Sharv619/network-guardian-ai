// Custom PromptFoo provider - calls the Network Guardian AI backend API
// Using CommonJS module format for compatibility

const fetch = globalThis.fetch;

function NetworkGuardianProvider() {
  this.apiUrl = 'http://localhost:8000/analyze';
}

NetworkGuardianProvider.prototype.id = function() {
  return 'network-guardian-api';
};

NetworkGuardianProvider.prototype.callApi = async function(prompt, context) {
  let domain = 
    context?.vars?.domain ||
    context?.vars?.Domain ||
    (typeof prompt === 'string' ? prompt : '');

  if (!domain || typeof domain !== 'string') {
    throw new Error('No domain provided');
  }

  domain = domain.trim().replace(/^https?:\/\//, '').split('/')[0].split('?')[0];

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
};

NetworkGuardianProvider.prototype.call = async function(prompt, context) {
  return this.callApi(prompt, context);
};

module.exports = NetworkGuardianProvider;
