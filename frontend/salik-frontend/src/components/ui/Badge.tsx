import { HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'outline' | 'cyan' | 'indigo' | 'purple' | 'emerald' | 'success' | 'warning' | 'destructive';
}

export default function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors backdrop-blur-sm',
        {
          'bg-white/10 border-white/20 text-white': variant === 'default',
          'bg-white/5 border-white/10 text-gray-300': variant === 'secondary',
          'bg-transparent border-white/20 text-white': variant === 'outline',
          'bg-cyan-500/20 border-cyan-500/30 text-cyan-300': variant === 'cyan',
          'bg-indigo-500/20 border-indigo-500/30 text-indigo-300': variant === 'indigo',
          'bg-purple-500/20 border-purple-500/30 text-purple-300': variant === 'purple',
          'bg-emerald-500/20 border-emerald-500/30 text-emerald-300': variant === 'emerald',
          'bg-emerald-500/10 border-emerald-500/20 text-emerald-300': variant === 'success',
          'bg-amber-500/10 border-amber-500/20 text-amber-300': variant === 'warning',
          'bg-red-500/10 border-red-500/20 text-red-300': variant === 'destructive',
        },
        className
      )}
      {...props}
    />
  );
}


