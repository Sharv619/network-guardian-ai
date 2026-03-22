import { useState, useEffect } from 'react';
import { Check, Zap, Shield, Crown, CreditCard, ExternalLink, Loader2, AlertCircle } from 'lucide-react';
import { getPricing, getSubscription, PricingTier, createCheckout } from '../services/tenantService';

const tierIcons: Record<string, React.ReactNode> = {
  free: <Shield className="w-8 h-8" />,
  pro: <Zap className="w-8 h-8" />,
  enterprise: <Crown className="w-8 h-8" />,
};

const tierColors: Record<string, string> = {
  free: 'border-gray-500/30 bg-gray-500/5',
  pro: 'border-blue-500/30 bg-blue-500/5',
  enterprise: 'border-purple-500/30 bg-purple-500/5',
};

const PricingPage: React.FC = () => {
  const [pricing, setPricing] = useState<Record<string, PricingTier>>({});
  const [currentTier, setCurrentTier] = useState<string>('free');
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    loadPricing();
  }, []);

  const loadPricing = async () => {
    try {
      setLoading(true);
      const [pricingData, subscription] = await Promise.all([
        getPricing(),
        getSubscription().catch(() => null),
      ]);
      setPricing(pricingData.tiers);
      if (subscription) {
        setCurrentTier(subscription.tier || 'free');
      }
    } catch (error) {
      console.error('Failed to load pricing:', error);
      setError('Failed to load pricing information');
    } finally {
      setLoading(false);
    }
  };

  const handleUpgrade = async (tier: string) => {
    setError('');
    setUpgrading(tier);

    try {
      const result = await createCheckout(
        tier,
        `${window.location.origin}/success`,
        `${window.location.origin}/pricing`
      );
      
      if (result.url) {
        window.location.href = result.url;
      }
    } catch (error: any) {
      setError(error.message || 'Failed to create checkout session');
      setUpgrading(null);
    }
  };

  const tiers = ['free', 'pro', 'enterprise'];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-dark-100">Choose Your Plan</h2>
        <p className="text-dark-400 mt-2">
          Select the protection level that fits your needs
        </p>
      </div>

      {error && (
        <div className="max-w-4xl mx-auto p-4 bg-red-500/20 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          {error}
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto">
        {tiers.map((tier) => {
          const tierData = pricing[tier];
          if (!tierData) return null;

          const isCurrent = currentTier === tier;
          const isDowngrade = tiers.indexOf(currentTier) > tiers.indexOf(tier);
          const isUpgrade = tiers.indexOf(tier) > tiers.indexOf(currentTier);

          return (
            <div
              key={tier}
              className={`relative border rounded-xl p-6 ${tierColors[tier]} ${
                isCurrent ? 'ring-2 ring-accent' : ''
              }`}
            >
              {isCurrent && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-accent text-white text-xs font-medium rounded-full">
                  Current Plan
                </div>
              )}

              <div className="text-center mb-6">
                <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
                  tier === 'free' ? 'bg-gray-500/20 text-gray-400' :
                  tier === 'pro' ? 'bg-blue-500/20 text-blue-400' :
                  'bg-purple-500/20 text-purple-400'
                }`}>
                  {tierIcons[tier]}
                </div>
                <h3 className="text-xl font-bold text-dark-100">{tierData.name}</h3>
                <div className="mt-2">
                  <span className="text-3xl font-bold text-dark-100">
                    ${tierData.price_monthly}
                  </span>
                  <span className="text-dark-400">/month</span>
                </div>
                {tierData.price_yearly > 0 && (
                  <div className="text-sm text-green-400 mt-1">
                    Save ${(tierData.price_monthly * 12) - tierData.price_yearly}/year
                  </div>
                )}
              </div>

              <ul className="space-y-3 mb-6">
                <li className="flex items-start gap-2">
                  <Check className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
                  <span className="text-dark-200">
                    {tierData.requests_per_day === -1 ? 'Unlimited' : tierData.requests_per_day.toLocaleString()}{' '}
                    requests/day
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
                  <span className="text-dark-200">
                    {tierData.requests_per_minute === -1 ? 'Unlimited' : tierData.requests_per_minute}{' '}
                    requests/min
                  </span>
                </li>
                {tierData.features.map((feature, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <Check className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
                    <span className="text-dark-200">{feature.replace(/_/g, ' ')}</span>
                  </li>
                ))}
              </ul>

              {isCurrent ? (
                <button
                  disabled
                  className="w-full py-3 px-4 bg-dark-700 text-dark-400 font-medium rounded-lg cursor-not-allowed"
                >
                  Current Plan
                </button>
              ) : isDowngrade ? (
                <button
                  disabled
                  className="w-full py-3 px-4 bg-dark-800 border border-dark-700 text-dark-400 font-medium rounded-lg"
                >
                  Downgrade Available
                </button>
              ) : (
                <button
                  onClick={() => handleUpgrade(tier)}
                  disabled={upgrading !== null}
                  className={`w-full py-3 px-4 font-medium rounded-lg transition-colors flex items-center justify-center gap-2 ${
                    tier === 'pro' 
                      ? 'bg-blue-600 hover:bg-blue-500 text-white'
                      : tier === 'enterprise'
                      ? 'bg-purple-600 hover:bg-purple-500 text-white'
                      : 'bg-accent hover:bg-accent-hover text-white'
                  } disabled:opacity-50`}
                >
                  {upgrading === tier ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Redirecting...
                    </>
                  ) : (
                    <>
                      <CreditCard className="w-4 h-4" />
                      Upgrade to {tierData.name}
                    </>
                  )}
                </button>
              )}
            </div>
          );
        })}
      </div>

      <div className="text-center text-sm text-dark-500">
        All plans include a 14-day money-back guarantee.{' '}
        <a href="#" className="text-accent hover:underline">
          Compare all features
        </a>
      </div>
    </div>
  );
};

export default PricingPage;
