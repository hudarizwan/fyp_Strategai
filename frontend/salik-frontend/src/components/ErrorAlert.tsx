import { AlertCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ErrorAlertProps {
  message: string;
  onClose?: () => void;
}

export default function ErrorAlert({ message, onClose }: ErrorAlertProps) {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-red-100 shadow-[0_16px_40px_rgba(127,29,29,0.2)]',
        onClose && 'pr-10'
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-full border border-red-400/20 bg-red-400/10">
          <AlertCircle className="h-5 w-5 text-red-300" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium leading-6">{message}</p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="absolute right-4 top-4 text-red-200 transition-colors hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

