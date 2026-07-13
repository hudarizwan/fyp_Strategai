import { InputHTMLAttributes, forwardRef } from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

const Input = forwardRef<HTMLInputElement, InputProps>(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(
        'flex h-11 w-full rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-2 text-sm text-white shadow-sm backdrop-blur-xl placeholder:text-slate-500 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/30 disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      ref={ref}
      {...props}
    />
  );
});

Input.displayName = 'Input';

export default Input;
