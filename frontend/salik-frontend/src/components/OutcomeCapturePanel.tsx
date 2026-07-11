import { useState, type FormEvent } from 'react';
import { AlertTriangle, CheckCircle2, Clock3, Send, X } from 'lucide-react';
import { analyticsService } from '@/services/api';
import { AnalyticsRecommendation } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from './ui/Card';
import Button from './ui/Button';

interface OutcomeCapturePanelProps {
  productName: string;
  category?: string;
  analyticsRecommendation: AnalyticsRecommendation;
}

type FeedbackType = 'acted_on_recommendation' | 'skipped' | 'follow_up';

interface FormState {
  feedback_type: FeedbackType;
  actual_buy_price_pkr: string;
  actual_sell_price_pkr: string;
  quantity: string;
  notes: string;
}

const FEEDBACK_OPTIONS: Array<{
  value: FeedbackType;
  label: string;
  description: string;
}> = [
  {
    value: 'acted_on_recommendation',
    label: 'Acted on recommendation',
    description: 'I used this recommendation to buy or sell the product.',
  },
  {
    value: 'skipped',
    label: 'Skipped',
    description: 'I reviewed the recommendation but did not act on it.',
  },
  {
    value: 'follow_up',
    label: 'Later updated',
    description: 'I am adding the real-world outcome after the fact.',
  },
];

const initialState: FormState = {
  feedback_type: 'acted_on_recommendation',
  actual_buy_price_pkr: '',
  actual_sell_price_pkr: '',
  quantity: '',
  notes: '',
};

const parseOptionalNumber = (value: string): number | null => {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
};

export default function OutcomeCapturePanel({
  productName,
  category,
  analyticsRecommendation,
}: OutcomeCapturePanelProps) {
  const [state, setState] = useState<FormState>(initialState);
  const [submitting, setSubmitting] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (dismissed) {
    return null;
  }

  const handleChange = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setState((current) => ({ ...current, [key]: value }));
    setSuccessMessage(null);
    setError(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const payload = {
        pipeline_run_id: analyticsRecommendation.pipeline_run_id || undefined,
        analytics_result_id: analyticsRecommendation.analytics_result_id || undefined,
        marketing_strategy_id: analyticsRecommendation.marketing_strategy_id || undefined,
        product_name: productName,
        category: category || analyticsRecommendation.category || null,
        feedback_type: state.feedback_type,
        action_taken: state.feedback_type,
        actual_buy_price_pkr: parseOptionalNumber(state.actual_buy_price_pkr),
        actual_sell_price_pkr: parseOptionalNumber(state.actual_sell_price_pkr),
        quantity: parseOptionalNumber(state.quantity),
        notes: state.notes.trim() || null,
        source_page: 'results',
      };

      await analyticsService.submitFeedback(payload);
      setSuccessMessage('Feedback saved. Thanks for closing the loop.');
      setState(initialState);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to save feedback right now.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card className="border border-emerald-400/15 bg-gradient-to-br from-emerald-500/10 via-white/[0.04] to-cyan-500/10">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-300" />
            Outcome Feedback
          </CardTitle>
          <p className="mt-1 text-sm text-gray-400">
            Log what happened after you reviewed the recommendation so we can backtest future predictions.
          </p>
        </div>
        <Button variant="outline" onClick={() => setDismissed(true)} className="shrink-0">
          <X className="mr-2 h-4 w-4" />
          Dismiss
        </Button>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3 text-sm text-gray-300">
            <p className="text-xs uppercase tracking-[0.18em] text-gray-400">Product</p>
            <p className="mt-1 font-semibold text-white">{productName}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3 text-sm text-gray-300">
            <p className="text-xs uppercase tracking-[0.18em] text-gray-400">Analytics Result</p>
            <p className="mt-1 font-semibold text-white">{analyticsRecommendation.analytics_result_id || 'Pending'}</p>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-3 text-sm text-gray-300">
            <p className="text-xs uppercase tracking-[0.18em] text-gray-400">Tracking</p>
            <p className="mt-1 font-semibold text-white">Saved to outcome history</p>
          </div>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {FEEDBACK_OPTIONS.map((option) => {
              const active = state.feedback_type === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handleChange('feedback_type', option.value)}
                  className={`rounded-2xl border p-4 text-left transition-colors ${
                    active
                      ? 'border-emerald-400/40 bg-emerald-500/10'
                      : 'border-white/10 bg-white/[0.03] hover:bg-white/[0.05]'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Clock3 className={`h-4 w-4 ${active ? 'text-emerald-300' : 'text-gray-400'}`} />
                    <span className="font-semibold text-white">{option.label}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-gray-400">{option.description}</p>
                </button>
              );
            })}
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <label className="space-y-2 text-sm text-gray-300">
              <span className="text-xs uppercase tracking-[0.18em] text-gray-400">Actual Buy Price</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={state.actual_buy_price_pkr}
                onChange={(event) => handleChange('actual_buy_price_pkr', event.target.value)}
                placeholder="e.g. 1150"
                className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2 text-white outline-none transition-colors placeholder:text-gray-500 focus:border-emerald-400/40"
              />
            </label>
            <label className="space-y-2 text-sm text-gray-300">
              <span className="text-xs uppercase tracking-[0.18em] text-gray-400">Actual Sell Price</span>
              <input
                type="number"
                min="0"
                step="0.01"
                value={state.actual_sell_price_pkr}
                onChange={(event) => handleChange('actual_sell_price_pkr', event.target.value)}
                placeholder="e.g. 1499"
                className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2 text-white outline-none transition-colors placeholder:text-gray-500 focus:border-emerald-400/40"
              />
            </label>
            <label className="space-y-2 text-sm text-gray-300">
              <span className="text-xs uppercase tracking-[0.18em] text-gray-400">Quantity</span>
              <input
                type="number"
                min="0"
                step="1"
                value={state.quantity}
                onChange={(event) => handleChange('quantity', event.target.value)}
                placeholder="e.g. 50"
                className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-2 text-white outline-none transition-colors placeholder:text-gray-500 focus:border-emerald-400/40"
              />
            </label>
          </div>

          <label className="block space-y-2 text-sm text-gray-300">
            <span className="text-xs uppercase tracking-[0.18em] text-gray-400">Notes</span>
            <textarea
              rows={3}
              value={state.notes}
              onChange={(event) => handleChange('notes', event.target.value)}
              placeholder="Optional context, such as where you sold, special discounts, or why you skipped it."
              className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-3 py-2 text-white outline-none transition-colors placeholder:text-gray-500 focus:border-emerald-400/40"
            />
          </label>

          {(error || successMessage) && (
            <div
              className={`rounded-2xl border px-4 py-3 text-sm ${
                error
                  ? 'border-red-400/20 bg-red-500/10 text-red-100'
                  : 'border-emerald-400/20 bg-emerald-500/10 text-emerald-100'
              }`}
            >
              <div className="flex items-start gap-2">
                <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${error ? 'text-red-300' : 'text-emerald-300'}`} />
                <p>{error || successMessage}</p>
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" disabled={submitting}>
              {submitting ? (
                <>
                  <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Saving...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  Save Outcome
                </>
              )}
            </Button>
            <p className="text-xs text-gray-400">
              This stores one append-only feedback event tied to the original prediction.
            </p>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

